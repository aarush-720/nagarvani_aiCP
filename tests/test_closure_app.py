"""Closure verification through the web app: officer resolve with photo, citizen page, and
that no HTTP route other than the citizen's 'yes' closes a ticket."""
import io

import pytest

from nagarvani import config
from nagarvani.app import create_app
from nagarvani.tickets import iso, utcnow

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
TEXT = "कोथरूडमध्ये रस्त्यावर मोठे खड्डे पडले आहेत"


@pytest.fixture
def app(tmp_path):
    return create_app(tmp_path / "t.sqlite3", load_asr=False, upload_dir=tmp_path / "uploads")


@pytest.fixture
def client(app):
    return app.test_client()


def store(app):
    return app.extensions["nagarvani"]["store"]


def open_ticket(app, priority="P3"):
    return store(app).create(channel="seed", text=TEXT, status="auto_routed", department="ROAD", ward="KOB",
                             priority=priority, deadline_utc=iso(utcnow()))


def resolve(client, tid, note="खड्डा बुजवला / pothole filled", photo=None, name="after.png"):
    data = {"action": "resolve", "note": note}
    if photo is not None:
        data["photo"] = (io.BytesIO(photo), name)
    return client.post(f"/ticket/{tid}/action", data=data, content_type="multipart/form-data")


def test_resolve_with_photo_then_citizen_yes_closes(client, app):
    tid = open_ticket(app)
    resolve(client, tid, photo=PNG)
    t = store(app).get(tid)
    assert t["status"] == "pending_confirmation" and t["resolution_photo"].endswith(".png")
    assert client.get(f"/ticket/{tid}/photo").data == PNG
    page = client.get(f"/status/{tid}").get_data(as_text=True)
    assert "हे काम झाले का?" in page and "Was this fixed?" in page and "pothole filled" in page
    client.post(f"/status/{tid}/answer", data={"answer": "yes"})
    assert store(app).get(tid)["status"] == "closed"
    assert "Closed after you confirmed" in client.get(f"/status/{tid}").get_data(as_text=True)


def test_citizen_no_reopens_with_higher_priority(client, app):
    tid = open_ticket(app, "P3")
    resolve(client, tid)
    client.post(f"/status/{tid}/answer", data={"answer": "no", "comment": "अजून खड्डा आहे"})
    t = store(app).get(tid)
    assert (t["status"], t["priority"], t["citizen_comment"]) == ("reopened", "P2", "अजून खड्डा आहे")
    assert parse_after_now(t["deadline_utc"])
    assert "citizen" in client.get(f"/ticket/{tid}").get_data(as_text=True)          # timeline shows the actor


def parse_after_now(s):
    from nagarvani.tickets import parse
    return parse(s) > utcnow()


@pytest.mark.parametrize("photo,name", [
    (b"just some text, not an image", "after.jpg"),                  # renamed file: checked by content
    (b"\xff\xd8\xff" + b"\x00" * (config.RESOLUTION_PHOTO_MAX_BYTES + 1), "big.jpg"),
])
def test_bad_photo_is_refused_and_nothing_changes(client, app, tmp_path, photo, name):
    tid = open_ticket(app)
    resolve(client, tid, photo=photo, name=name)
    assert store(app).get(tid)["status"] == "auto_routed"
    assert not list((tmp_path / "uploads").glob("resolution/*"))


def test_resolve_without_note_is_refused(client, app):
    tid = open_ticket(app)
    resolve(client, tid, note="  ", photo=PNG)
    assert store(app).get(tid)["status"] == "auto_routed"


@pytest.mark.parametrize("action", ["close", "closed", "confirm_fixed", "report_not_fixed", "resolve_and_close"])
def test_officer_route_cannot_close(client, app, action):
    tid = open_ticket(app)
    resolve(client, tid)
    r = client.post(f"/ticket/{tid}/action", data={"action": action, "note": "x"})
    assert r.status_code == 400 and store(app).get(tid)["status"] == "pending_confirmation"


def test_no_route_closes_without_the_citizen(client, app):
    tid = open_ticket(app)
    for action in ("confirm", "correct", "dup_merge", "dup_keep"):
        client.post(f"/ticket/{tid}/action", data={"action": action, "note": "x"})
    resolve(client, tid)
    resolve(client, tid)                                                   # second resolve: refused
    for action in ("confirm", "correct", "dup_merge", "dup_keep"):
        client.post(f"/ticket/{tid}/action", data={"action": action, "note": "x"})
    client.post(f"/status/{tid}/answer", data={"answer": "maybe"})
    assert store(app).get(tid)["status"] == "pending_confirmation"
    assert not any(e["to_status"] == "closed" for e in store(app).events(tid))


def test_citizen_cannot_answer_an_open_ticket(client, app):
    tid = open_ticket(app)
    client.post(f"/status/{tid}/answer", data={"answer": "yes"})
    assert store(app).get(tid)["status"] == "auto_routed"


def test_status_lookup(client, app):
    tid = open_ticket(app)
    assert client.get(f"/status?id=%23{tid}").headers["Location"].endswith(f"/status/{tid}")
    assert client.get("/status/99999").status_code == 404
    assert client.get("/status").status_code == 200


def test_submission_page_links_to_the_citizen_page(client, app):
    r = client.post("/submit", data={"text": TEXT, "submission_key": "k1"})
    page = client.get(r.headers["Location"]).get_data(as_text=True)
    assert "/status/" in page
