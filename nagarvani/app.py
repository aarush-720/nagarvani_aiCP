"""Flask application (server-rendered, no build step). Start it with `python run.py`."""
from __future__ import annotations

import json
import logging
import re
import uuid
from pathlib import Path

from flask import Flask, Response, abort, flash, jsonify, redirect, render_template, request, send_file, url_for

from . import config, data, service
from . import speech as asr
from . import triage as triage_mod
from .tickets import Store, parse, utcnow

log = logging.getLogger("nagarvani")
AUDIO_EXT = {"wav", "mp3", "m4a", "ogg", "oga", "opus", "webm", "mp4", "aac"}
MIME_EXT = {"audio/webm": "webm", "audio/ogg": "ogg", "audio/mp4": "mp4", "audio/mpeg": "mp3",
            "audio/wav": "wav", "audio/x-wav": "wav", "audio/aac": "aac", "video/webm": "webm"}


def _read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
    except (OSError, ValueError):
        return None


def create_app(db_path=None, *, load_asr: bool = True, upload_dir=None) -> Flask:
    app = Flask(__name__)
    app.config.update(SECRET_KEY="nagarvani-local-demo",       # local single-user demo; see limitations
                      MAX_CONTENT_LENGTH=25 * 1024 * 1024)
    app.json.ensure_ascii = False                          # readable Devanagari in JSON responses
    store = Store(db_path)
    uploads = Path(upload_dir or (config.INSTANCE / "uploads"))
    uploads.mkdir(parents=True, exist_ok=True)

    # Loaded once at start-up.
    state = {"classifier": False, "classifier_error": None, "asr": False, "asr_error": None}
    try:
        triage_mod.load_all()          # classifier artefact, gazetteer, duplicate detector
        state["classifier"] = True
    except Exception as e:  # noqa: BLE001
        state["classifier_error"] = f"{type(e).__name__}: {e}"
        log.error("classifier not loaded: %s", e)
    if load_asr:
        try:
            asr.load_backend()
            state["asr"] = True
        except asr.AsrUnavailable as e:
            state["asr_error"] = str(e)
            log.warning("ASR unavailable: %s", e)
    app.extensions["nagarvani"] = {"store": store, "state": state, "uploads": uploads}

    depts = data.dept_names()
    wards = data.ward_names()
    sla = data.sla_hours()
    bands = {b["band"]: dict(b, sla_hours=sla[b["band"]]) for b in data.taxonomy()["bands"]}

    @app.context_processor
    def globals_():
        return dict(DEPTS=depts, WARDS=wards, BANDS=bands, ist=service.to_ist, state=state,
                    asr_model=config.ASR_MODEL, cfg=config)

    # ---- citizen intake ---------------------------------------------------------------------
    @app.get("/")
    def intake():
        from .examples import EXAMPLES
        return render_template("intake.html", examples=EXAMPLES, submission_key=uuid.uuid4().hex)

    @app.post("/api/transcribe")
    def api_transcribe():
        f = request.files.get("audio")
        language = request.form.get("language", "mr")
        if language not in ("mr", "hi"):
            language = "mr"
        if not f or not f.filename and not f.mimetype:
            return jsonify(ok=False, code="no_file", message_mr="ऑडिओ फाईल मिळाली नाही.",
                           message_en="No audio file was received."), 400
        ext = (f.filename.rsplit(".", 1)[-1].lower() if f.filename and "." in f.filename else "")
        if ext not in AUDIO_EXT:
            ext = MIME_EXT.get((f.mimetype or "").split(";")[0], "")
        if ext not in AUDIO_EXT:
            return jsonify(ok=False, code="format", message_mr="ही फाईल ऑडिओ प्रकारची नाही.",
                           message_en="Unsupported file type. Use WAV, MP3, M4A, OGG/Opus, WebM or MP4."), 400
        upload_id = uuid.uuid4().hex
        path = uploads / f"{upload_id}.{ext}"
        f.save(path)                                        # persisted before any processing
        channel = "microphone" if request.form.get("source") == "microphone" else "upload"
        store_ = app.extensions["nagarvani"]["store"]
        try:
            r = asr.transcribe(path, language)
        except asr.AudioRejected as e:
            return jsonify(ok=False, code=e.code, message_mr=e.message_mr, message_en=e.message_en,
                           heuristic=True, upload_id=upload_id,
                           transcript=e.result.text if e.result else None)
        except Exception as e:  # noqa: BLE001 - ASR missing or crashed: keep the audio as a review ticket
            tid, _ = service.submit(store_, text="", channel=channel, language=language, audio_path=str(path),
                                    submission_key=f"audio-{upload_id}")
            service.record_failure(store_, tid, "speech recognition", e if not isinstance(e, asr.AsrUnavailable)
                                   else "speech recognition model not available on this computer")
            return jsonify(ok=False, code="asr_failed", ticket_id=tid, ticket_url=url_for("ticket", tid=tid),
                           message_mr=f"ऑडिओ जतन केला आहे (तक्रार क्रमांक {tid}). अधिकारी तो ऐकतील. तुम्ही तक्रार टाइपही करू शकता.",
                           message_en=f"The audio is saved as ticket #{tid} for an officer to listen to. "
                                      "You can also type the complaint.")
        return jsonify(ok=True, upload_id=upload_id, transcript=r.text, asr=r.to_dict(), channel=channel)

    @app.post("/submit")
    def submit():
        store_ = app.extensions["nagarvani"]["store"]
        text = (request.form.get("text") or "").strip()
        key = request.form.get("submission_key") or None
        if not re.search(r"[A-Za-zऀ-ॿ]", text):
            flash("कृपया तक्रार लिहा किंवा रेकॉर्ड करा. / Please type or record a complaint.")
            return redirect(url_for("intake"))
        upload_id = request.form.get("upload_id") or ""
        audio_path = None
        if re.fullmatch(r"[0-9a-f]{32}", upload_id):
            hits = list(uploads.glob(f"{upload_id}.*"))
            audio_path = str(hits[0]) if hits else None
        asr_info = None
        if request.form.get("asr_json"):
            try:
                asr_info = json.loads(request.form["asr_json"])
            except ValueError:
                asr_info = None
        ward_hint = request.form.get("ward_hint") or None
        if ward_hint not in wards:
            ward_hint = None
        channel = request.form.get("channel") or "typed"
        if channel not in ("typed", "upload", "microphone"):
            channel = "typed"
        tid, created = service.submit(store_, text=text[:2000], channel=channel,
                                      language=request.form.get("language", "mr"), ward_hint=ward_hint,
                                      raw_transcript=request.form.get("raw_transcript") or None,
                                      asr_info=asr_info, audio_path=audio_path, submission_key=key)
        if not created:
            flash(f"ही तक्रार आधीच नोंदवली आहे (#{tid}). / Already received as ticket #{tid}.")
        return redirect(url_for("ticket", tid=tid))

    # ---- trace -------------------------------------------------------------------------------
    @app.get("/ticket/<int:tid>")
    def ticket(tid):
        store_ = app.extensions["nagarvani"]["store"]
        t = store_.get(tid)
        if not t:
            abort(404)
        trace = json.loads(t["trace_json"]) if t["trace_json"] else None
        asr_info = json.loads(t["asr_json"]) if t["asr_json"] else None
        parent = store_.get(t["parent_id"]) if t["parent_id"] else None
        candidate = store_.get(t["dup_candidate_id"]) if t["dup_candidate_id"] else None
        overdue = bool(t["deadline_utc"] and t["status"] not in ("resolved", "merged")
                       and parse(t["deadline_utc"]) < utcnow())
        return render_template("ticket.html", t=t, trace=trace, asr_info=asr_info, parent=parent,
                               candidate=candidate, children=store_.children(tid), overdue=overdue)

    @app.get("/ticket/<int:tid>/audio")
    def ticket_audio(tid):
        t = app.extensions["nagarvani"]["store"].get(tid)
        if not t or not t["audio_path"] or not Path(t["audio_path"]).exists():
            abort(404)
        p = Path(t["audio_path"]).resolve()
        if uploads.resolve() not in p.parents:
            abort(404)
        return send_file(p)

    @app.post("/ticket/<int:tid>/action")
    def ticket_action(tid):
        store_ = app.extensions["nagarvani"]["store"]
        if not store_.get(tid):
            abort(404)
        action, note = request.form.get("action"), request.form.get("note", "")
        try:
            if action == "confirm":
                service.confirm(store_, tid, note)
                flash(f"#{tid} confirmed / पुष्टी केली.")
            elif action == "correct":
                ch = service.correct(store_, tid, department=request.form.get("department") or None,
                                     ward=request.form.get("ward") or None,
                                     priority=request.form.get("priority") or None, note=note)
                flash(f"#{tid}: " + (", ".join(f"{k} → {v}" for k, v in ch.items() if k != "deadline_utc")
                                     or "no change / बदल नाही"))
            elif action in ("dup_merge", "dup_keep"):
                service.decide_duplicate(store_, tid, merge=action == "dup_merge", note=note)
                flash(f"#{tid}: " + ("merged / एकत्र केले" if action == "dup_merge" else "kept separate / वेगळे ठेवले"))
            elif action == "resolve":
                service.resolve(store_, tid, note)
                flash(f"#{tid} resolved / निकाली काढली.")
            else:
                abort(400)
        except service.ActionError as e:
            flash(f"#{tid}: {e}")
        return redirect(request.form.get("next") or url_for("ticket", tid=tid))

    # ---- officer queue -------------------------------------------------------------------------
    @app.get("/queue")
    def queue():
        store_ = app.extensions["nagarvani"]["store"]
        f = {k: request.args.get(k) or None for k in ("ward", "department", "status")}
        rows = service.queue(store_, **f)
        review = [r for r in rows if r["status"] == "review"]
        other = [r for r in rows if r["status"] != "review"]
        n_corr = len(store_.corrections())
        return render_template("queue.html", review=review, other=other, f=f, n_corrections=n_corr)

    @app.get("/export/<ward>.csv")
    def export(ward):
        import csv
        import io
        if ward not in wards:
            abort(404)
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["ticket", "created_ist", "status", "department", "priority", "deadline_ist", "overdue",
                    "reports", "transcript_uncertain", "text", "review_reason"])
        for r in service.export_rows(app.extensions["nagarvani"]["store"], ward):
            w.writerow([r["id"], service.to_ist(r["created_utc"]), r["status"], r["department"], r["priority"],
                        service.to_ist(r["deadline_utc"]), "yes" if r["overdue"] else "no", r["report_count"],
                        "yes" if r["transcript_uncertain"] else "no", r["text"], r["review_reason"] or ""])
        body = "﻿" + buf.getvalue()                     # BOM so Excel on Windows reads UTF-8
        return Response(body.encode("utf-8"), mimetype="text/csv; charset=utf-8",
                        headers={"Content-Disposition": f"attachment; filename=nagarvani_{ward}.csv"})

    @app.get("/corrections.jsonl")
    def corrections():
        body = service.corrections_jsonl(app.extensions["nagarvani"]["store"])
        return Response(body.encode("utf-8"), mimetype="application/x-ndjson; charset=utf-8",
                        headers={"Content-Disposition": "attachment; filename=nagarvani_corrections.jsonl"})

    # ---- about / health ------------------------------------------------------------------------
    @app.get("/about")
    def about():
        from . import results_view
        R = results_view.load()
        return render_template("about.html", s=results_view.summary(R) if R else None,
                               ae=_read_json(config.RESULTS / "asr_eval.json"),
                               bench=_read_json(config.RESULTS / "asr_benchmark.json"))

    @app.get("/health")
    def health():
        st = app.extensions["nagarvani"]["state"]
        db_ok = app.extensions["nagarvani"]["store"].ok()
        body = {"classifier_loaded": st["classifier"], "database_ok": db_ok, "asr_model_loaded": st["asr"],
                "asr_model": config.ASR_MODEL, "asr_error": st["asr_error"], "classifier_error": st["classifier_error"]}
        return jsonify(body), 200 if st["classifier"] and db_ok else 503

    # ---- errors: never show a stack trace ------------------------------------------------------
    @app.errorhandler(404)
    def not_found(_e):
        return render_template("error.html", code=404, msg_mr="हे पान सापडले नाही.", msg_en="Page not found."), 404

    @app.errorhandler(413)
    def too_big(_e):
        return render_template("error.html", code=413, msg_mr="फाईल खूप मोठी आहे.",
                               msg_en="The file is too large (limit 25 MB)."), 413

    @app.errorhandler(Exception)
    def crashed(e):
        from werkzeug.exceptions import HTTPException
        if isinstance(e, HTTPException):
            return render_template("error.html", code=e.code, msg_mr="विनंती पूर्ण करता आली नाही.",
                                   msg_en=e.description), e.code
        log.exception("unhandled error")
        return render_template("error.html", code=500, msg_mr="काहीतरी चुकले. तुमची तक्रार जतन झाली असल्यास ती अधिकाऱ्यांकडे आहे.",
                               msg_en="Something went wrong. If your complaint was saved, it is with an officer."), 500

    return app
