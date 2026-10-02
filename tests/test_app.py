"""Flask routes through the test client: text path, upload path (mocked ASR), failure paths,
officer actions, corrections export, CSV encoding, and live duplicate escalation."""
import csv
import io
import json
import re
from datetime import timedelta
from types import SimpleNamespace

import pytest

from nagarvani import asr, pipeline, service
from nagarvani.app import create_app
from nagarvani.store import iso, utcnow
from tests import audio_fixtures as af

POTHOLE = "हडपसर येथे रस्त्यावर खूप मोठे खड्डे पडले आहेत"


class FakeBackend:
    def __init__(self, text=POTHOLE, logprob=-0.3, crash=False):
        self.text, self.logprob, self.crash = text, logprob, crash

    def transcribe(self, audio, **kw):
        if self.crash:
            raise RuntimeError("decoder exploded")
        return iter([SimpleNamespace(text=self.text, avg_logprob=self.logprob, no_speech_prob=0.02)]), None


@pytest.fixture
def app(tmp_path):
    a = create_app(tmp_path / "t.sqlite3", load_asr=False, upload_dir=tmp_path / "uploads")
    a.config["TESTING"] = False          # exercise the real error handlers
    yield a
    asr.set_backend(None, None)


@pytest.fixture
def client(app):
    return app.test_client()


def store(app):
    return app.extensions["nagarvani"]["store"]


def submit(client, text, key, **extra):
    return client.post("/submit", data={"text": text, "submission_key": key, "language": "mr", **extra})


def tid_from(resp):
    return int(re.search(r"/ticket/(\d+)", resp.headers["Location"]).group(1))


# ---- pages -----------------------------------------------------------------------------
@pytest.mark.parametrize("url", ["/", "/queue", "/about", "/health", "/corrections.jsonl"])
def test_pages_render(client, url):
    assert client.get(url).status_code == 200


def test_intake_has_no_name_or_phone_fields(client):
    html = client.get("/").get_data(as_text=True)
    assert 'name="name"' not in html and 'name="phone"' not in html
    assert "speech recognition is not available" in html.lower()     # model not loaded in tests


def test_no_external_resources(client):
    for url in ["/", "/queue", "/about"]:
        html = client.get(url).get_data(as_text=True)
        assert not re.search(r'(src|href)="https?://', html), url


def test_health_reports_components(client):
    h = client.get("/health").get_json()
    assert h["classifier_loaded"] and h["database_ok"] and h["asr_model_loaded"] is False


def test_about_numbers_come_from_results(client):
    ev = json.loads((pipeline.config.RESULTS / "eval.json").read_text(encoding="utf-8"))
    html = client.get("/about").get_data(as_text=True)
    acc = ev["department"]["accuracy"]
    assert f"{100 * acc['rate']:.1f}% ({acc['count']}/{acc['total']})" in html
    assert "Real-audio evaluation has not been run" in html          # no results/asr_eval.json
    assert "Simulation, not ASR" in html


def test_404_is_friendly(client):
    r = client.get("/ticket/999")
    assert r.status_code == 404 and "Traceback" not in r.get_data(as_text=True)


# ---- text path -----------------------------------------------------------------------------
def test_typed_complaint_to_trace(client, app):
    r = submit(client, "कोथरूडमध्ये रस्त्यावर मोठा खड्डा आहे", "k1")
    assert r.status_code == 302
    html = client.get(r.headers["Location"]).get_data(as_text=True)
    for must in ("Department", "Location", "Severity", "Duplicates", "Routing gate", "तक्रार क्रमांक", "R00",
                 "proposed values, not official PMC"):
        assert must in html
    t = store(app).get(tid_from(r))
    assert t["status"] in ("auto_routed", "review") and t["ward"] == "W08" and t["created_utc"].endswith("+00:00")
    assert "IST" in html


def test_double_submission_is_refused(client, app):
    a = submit(client, "कोथरूडमध्ये रस्त्यावर मोठा खड्डा आहे", "same")
    b = submit(client, "कोथरूडमध्ये रस्त्यावर मोठा खड्डा आहे", "same")
    assert tid_from(a) == tid_from(b) and len(store(app).tickets()) == 1


def test_empty_text_is_not_a_ticket(client, app):
    r = submit(client, "  !!! ", "k2")
    assert r.status_code == 302 and r.headers["Location"].endswith("/") and not store(app).tickets()


def test_ward_hint_used_when_text_has_no_place(client, app):
    r = submit(client, "रस्त्यावर खूप मोठे खड्डे पडले आहेत", "k3", ward_hint="W05")
    t = store(app).get(tid_from(r))
    assert t["ward"] == "W05" and json.loads(t["trace_json"])["ward"]["method"] == "hint"


def test_unknown_place_goes_to_review(client, app):
    t = store(app).get(tid_from(submit(client, "रस्त्यावर खूप मोठे खड्डे पडले आहेत", "k4")))
    assert t["status"] == "review" and "not resolved" in t["review_reason"]


# ---- failure paths ---------------------------------------------------------------------------
def test_triage_crash_still_creates_review_ticket(client, app, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("model file corrupted")
    monkeypatch.setattr(service, "triage", boom)
    r = submit(client, "कोथरूडमध्ये रस्त्यावर मोठा खड्डा आहे", "k5")
    t = store(app).get(tid_from(r))
    assert t["status"] == "review" and "model file corrupted" in t["failure"]
    page = client.get(r.headers["Location"]).get_data(as_text=True)
    assert "Automatic processing failed" in page and "Traceback" not in page


def test_saving_failure_still_leaves_review_ticket(client, app, monkeypatch):
    monkeypatch.setattr(service, "apply_result", lambda *a, **k: (_ for _ in ()).throw(OSError("disk full")))
    t = store(app).get(tid_from(submit(client, "कोथरूडमध्ये रस्त्यावर मोठा खड्डा आहे", "k6")))
    assert t["status"] == "review" and "disk full" in t["failure"]


# ---- upload path (mocked ASR) ----------------------------------------------------------------
def upload(client, path, name, language="mr"):
    with open(path, "rb") as f:
        return client.post("/api/transcribe", data={"audio": (f, name), "language": language, "source": "upload"},
                           content_type="multipart/form-data")


@pytest.mark.parametrize("ext", ["ogg", "webm", "mp4", "m4a", "mp3", "wav"])
def test_upload_transcribe_then_submit(client, app, tmp_path, ext):
    asr.set_backend(FakeBackend(), "mock")
    p = af.write(tmp_path / f"voice.{ext}", af.tone(3))
    j = upload(client, p, f"voice.{ext}").get_json()
    assert j["ok"] and j["transcript"] == POTHOLE and j["asr"]["language"] == "mr"
    edited = POTHOLE + " कृपया लवकर दुरुस्ती करा"
    r = client.post("/submit", data={"text": edited, "raw_transcript": j["transcript"], "upload_id": j["upload_id"],
                                     "asr_json": json.dumps(j["asr"]), "channel": "upload",
                                     "submission_key": f"u-{ext}", "language": "mr"})
    t = store(app).get(tid_from(r))
    assert t["raw_transcript"] == POTHOLE and t["text"] == edited and t["audio_path"].endswith(f".{ext}")
    html = client.get(r.headers["Location"]).get_data(as_text=True)
    assert "Raw transcript" in html and "edited text" in html and "<audio" in html
    assert client.get(f"/ticket/{t['id']}/audio").status_code == 200


def test_uncertain_transcript_is_flagged(client, app, tmp_path):
    asr.set_backend(FakeBackend(logprob=-1.6), "mock")
    j = upload(client, af.write(tmp_path / "v.wav", af.tone(3)), "v.wav").get_json()
    assert j["asr"]["uncertain"] is True
    r = client.post("/submit", data={"text": j["transcript"], "raw_transcript": j["transcript"],
                                     "upload_id": j["upload_id"], "asr_json": json.dumps(j["asr"]),
                                     "channel": "upload", "submission_key": "unc"})
    assert store(app).get(tid_from(r))["transcript_uncertain"] == 1


@pytest.mark.parametrize("samples,code", [(af.silence(3), "silence"), (af.tone(0.4), "too_short")])
def test_upload_guard_rejections(client, app, tmp_path, samples, code):
    asr.set_backend(FakeBackend(), "mock")
    j = upload(client, af.write(tmp_path / "s.wav", samples), "s.wav").get_json()
    assert j["ok"] is False and j["code"] == code and j["heuristic"] and j["message_mr"]
    assert not store(app).tickets()


def test_repeated_transcript_rejected(client, app, tmp_path):
    asr.set_backend(FakeBackend(text="धन्यवाद धन्यवाद धन्यवाद धन्यवाद धन्यवाद"), "mock")
    j = upload(client, af.write(tmp_path / "r.wav", af.tone(3)), "r.wav").get_json()
    assert j["code"] == "repetition"


def test_asr_crash_keeps_audio_as_review_ticket(client, app, tmp_path):
    asr.set_backend(FakeBackend(crash=True), "mock")
    j = upload(client, af.write(tmp_path / "c.ogg", af.tone(3)), "c.ogg").get_json()
    assert j["ok"] is False and j["code"] == "asr_failed"
    t = store(app).get(j["ticket_id"])
    assert t["status"] == "review" and "speech recognition" in t["failure"] and t["audio_path"]


def test_asr_model_missing_keeps_audio(client, app, tmp_path, monkeypatch):
    asr.set_backend(None, None)
    monkeypatch.setattr(pipeline.config, "MODELS", tmp_path / "nomodels")
    j = upload(client, af.write(tmp_path / "m.wav", af.tone(3)), "m.wav").get_json()
    assert j["code"] == "asr_failed" and store(app).get(j["ticket_id"])["status"] == "review"


def test_non_audio_upload_rejected(client, tmp_path):
    p = tmp_path / "x.txt"
    p.write_text("hello", encoding="utf-8")
    assert upload(client, p, "x.txt").status_code == 400


# ---- live duplicates and R32 -----------------------------------------------------------------
def test_triple_duplicate_merges_and_escalates(client, app):
    ids = [tid_from(submit(client, POTHOLE, f"dup{i}")) for i in range(3)]
    s = store(app)
    first, second, third = (s.get(i) for i in ids)
    assert first["status"] == "auto_routed"
    assert second["status"] == "merged" and second["parent_id"] == ids[0]
    assert third["status"] == "merged"
    parent = s.get(ids[0])
    assert parent["report_count"] == 3 and parent["priority"] == "P2" and "R32" in parent["escalation"]
    html = client.get(f"/ticket/{ids[2]}").get_data(as_text=True)
    assert "R32" in html and "MERGED" in html
    assert "Escalated" in client.get(f"/ticket/{ids[0]}").get_data(as_text=True)


# ---- officer queue and actions ---------------------------------------------------------------
def test_queue_sort_filter_overdue(client, app):
    s = store(app)
    old = utcnow() - timedelta(days=30)
    a = s.create(now=old, channel="seed", text="जुनी तक्रार", status="review", department="ROAD", ward="W08",
                 priority="P3", deadline_utc=iso(old + timedelta(hours=168)))
    b = s.create(channel="seed", text="तातडीची", status="auto_routed", department="DRAIN", ward="W08",
                 priority="P1", deadline_utc=iso(utcnow() + timedelta(hours=24)))
    c = s.create(channel="seed", text="दुसरा वॉर्ड", status="auto_routed", department="ROAD", ward="W01",
                 priority="P2", deadline_utc=iso(utcnow() + timedelta(hours=72)))
    rows = service.queue(s)
    assert [r["id"] for r in rows] == [b, c, a] and rows[-1]["overdue"]
    assert [r["id"] for r in service.queue(s, ward="W08")] == [b, a]
    assert [r["id"] for r in service.queue(s, department="ROAD", status="review")] == [a]
    html = client.get("/queue?ward=W08").get_data(as_text=True)
    assert "OVERDUE" in html and "दुसरा वॉर्ड" not in html


def test_corrections_logged_and_exported(client, app):
    s = store(app)
    tid = tid_from(submit(client, "रस्त्यावर खूप मोठे खड्डे पडले आहेत", "c1"))     # review: no ward
    client.post(f"/ticket/{tid}/action", data={"action": "confirm"})               # refused: no ward yet
    assert s.get(tid)["status"] == "review"
    client.post(f"/ticket/{tid}/action", data={"action": "correct", "department": "ROAD", "ward": "W12",
                                               "priority": "P2", "note": "officer knows the street"})
    client.post(f"/ticket/{tid}/action", data={"action": "confirm"})
    t = s.get(tid)
    assert (t["ward"], t["priority"], t["status"], t["confirmed"]) == ("W12", "P2", "routed", 1)
    lines = client.get("/corrections.jsonl").get_data(as_text=True).strip().splitlines()
    fields = [json.loads(x)["field"] for x in lines]
    assert "ward" in fields and "priority" in fields and "confirm" in fields
    client.post(f"/ticket/{tid}/action", data={"action": "resolve"})
    assert s.get(tid)["status"] == "resolved"


def test_pending_duplicate_decision(client, app):
    s = store(app)
    a = tid_from(submit(client, POTHOLE, "p1"))
    b = s.create(channel="seed", text="हडपसर येथे रस्ता खराब", status="review", department="ROAD", ward="W05",
                 priority="P3", dup_candidate_id=a, dup_score=0.38, dup_pending=1, masked_text="x")
    assert "Possible duplicate" in client.get(f"/ticket/{b}").get_data(as_text=True)
    client.post(f"/ticket/{b}/action", data={"action": "dup_merge"})
    assert s.get(b)["status"] == "merged" and s.get(a)["report_count"] == 2
    c = s.create(channel="seed", text="हडपसर येथे फुटपाथ", status="review", department="ROAD", ward="W05",
                 priority="P3", dup_candidate_id=a, dup_score=0.33, dup_pending=1, masked_text="y")
    client.post(f"/ticket/{c}/action", data={"action": "dup_keep"})
    assert s.get(c)["dup_pending"] == 0 and s.get(c)["status"] == "review"
    assert {"duplicate"} <= {r["field"] for r in s.corrections()}


# ---- CSV export --------------------------------------------------------------------------------
def test_ward_csv_has_bom_and_devanagari(client):
    submit(client, "कोथरूडमध्ये रस्त्यावर मोठा खड्डा आहे", "csv1")
    r = client.get("/export/W08.csv")
    assert r.status_code == 200 and r.data.startswith(b"\xef\xbb\xbf")
    assert "text/csv" in r.headers["Content-Type"] and "charset=utf-8" in r.headers["Content-Type"]
    rows = list(csv.reader(io.StringIO(r.data.decode("utf-8-sig"))))
    assert rows[0][0] == "ticket" and "कोथरूड" in rows[1][9]
    assert client.get("/export/W99.csv").status_code == 404
