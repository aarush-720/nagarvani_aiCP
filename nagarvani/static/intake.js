// Citizen intake: record or upload audio, show the transcript for checking, guard double submission.
(function () {
  const $ = (id) => document.getElementById(id);
  const form = $("intake"), text = $("text"), submitBtn = $("submit");
  let fromAudio = false;

  function lang() { return document.querySelector("input[name=language]:checked").value; }

  function setFromAudio(on) {
    fromAudio = on;
    $("check-label").classList.toggle("hidden", !on);
    $("checked").checked = false;
    updateSubmit();
  }
  function updateSubmit() { submitBtn.disabled = fromAudio && !$("checked").checked; }
  $("checked").addEventListener("change", updateSubmit);

  function showError(msg) {
    const box = $("asr-error");
    box.innerHTML = msg;
    box.classList.remove("hidden");
  }

  async function sendAudio(blob, filename, source, statusEl) {
    $("asr-error").classList.add("hidden");
    statusEl.textContent = "ऐकत आहे… / Transcribing…";
    const fd = new FormData();
    fd.append("audio", blob, filename);
    fd.append("language", lang());
    fd.append("source", source);
    let data;
    try {
      const resp = await fetch("/api/transcribe", { method: "POST", body: fd });
      data = await resp.json();
    } catch (e) {
      statusEl.textContent = "";
      showError("सर्व्हरशी संपर्क झाला नाही. कृपया तक्रार टाइप करा.<span class='en'>Could not reach the server. Please type the complaint.</span>");
      return;
    }
    statusEl.textContent = "";
    if (!data.ok) {
      let msg = (data.message_mr || "") + "<span class='en'>" + (data.message_en || "") + "</span>";
      if (data.heuristic) msg += "<span class='en'>(automatic check — a heuristic; it can be wrong)</span>";
      if (data.ticket_url) msg += "<p><a class='button small' href='" + data.ticket_url + "'>तक्रार पहा / View ticket</a></p>";
      else msg += "<p>कृपया पुन्हा रेकॉर्ड करा किंवा टाइप करा.<span class='en'>Please record again or type the complaint.</span></p>";
      showError(msg);
      return;
    }
    text.value = data.transcript;
    $("raw_transcript").value = data.transcript;
    $("upload_id").value = data.upload_id;
    $("asr_json").value = JSON.stringify(data.asr);
    $("channel").value = data.channel;
    const a = data.asr;
    let meta = "model " + a.model + " · " + a.duration + " s audio · " + a.seconds + " s to transcribe · language " + a.language;
    if (a.uncertain) meta += " · ⚠ अनिश्चित मजकूर / transcript uncertain";
    $("asr-meta").textContent = meta;
    $("asr-box").classList.remove("hidden");
    setFromAudio(true);
    text.focus();
  }

  // ---- microphone ----
  const recBtn = $("rec");
  if (recBtn) {
    let recorder = null, chunks = [], timer = null;
    recBtn.addEventListener("click", async () => {
      if (recorder && recorder.state === "recording") { recorder.stop(); return; }
      if (!navigator.mediaDevices || !window.MediaRecorder) {
        showError("हा ब्राउझर रेकॉर्डिंग करू शकत नाही.<span class='en'>This browser cannot record. Upload a file or type instead.</span>");
        return;
      }
      let stream;
      try { stream = await navigator.mediaDevices.getUserMedia({ audio: true }); }
      catch (e) {
        showError("मायक्रोफोन वापरण्याची परवानगी मिळाली नाही.<span class='en'>Microphone permission was denied. Use an example, upload a file or type.</span>");
        return;
      }
      const type = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4", "audio/ogg;codecs=opus"]
        .find((t) => MediaRecorder.isTypeSupported(t)) || "";
      recorder = new MediaRecorder(stream, type ? { mimeType: type } : undefined);
      chunks = [];
      recorder.ondataavailable = (e) => { if (e.data.size) chunks.push(e.data); };
      recorder.onstop = () => {
        clearInterval(timer);
        stream.getTracks().forEach((t) => t.stop());
        recBtn.textContent = "🎙 रेकॉर्ड सुरू करा / Start recording";
        recBtn.classList.remove("rec");
        const mime = recorder.mimeType || "audio/webm";
        const ext = mime.includes("mp4") ? "mp4" : mime.includes("ogg") ? "ogg" : "webm";
        sendAudio(new Blob(chunks, { type: mime }), "recording." + ext, "microphone", $("rec-status"));
      };
      recorder.start();
      let secs = 0;
      $("rec-status").textContent = "0 s";
      timer = setInterval(() => {
        secs += 1;
        $("rec-status").textContent = secs + " s (कमाल ६० / max 60)";
        if (secs >= 60) recorder.stop();
      }, 1000);
      recBtn.textContent = "⏹ थांबवा / Stop";
      recBtn.classList.add("rec");
    });
  }

  // ---- upload ----
  const upBtn = $("upload");
  if (upBtn) upBtn.addEventListener("click", () => {
    const f = $("file").files[0];
    if (!f) { showError("आधी फाईल निवडा.<span class='en'>Choose a file first.</span>"); return; }
    sendAudio(f, f.name, "upload", $("upload-status"));
  });

  // ---- examples ----
  document.querySelectorAll(".examples button[data-text]").forEach((b) =>
    b.addEventListener("click", () => {
      text.value = b.dataset.text;
      $("channel").value = "typed";
      $("upload_id").value = ""; $("raw_transcript").value = ""; $("asr_json").value = "";
      $("asr-box").classList.add("hidden");
      setFromAudio(false);
      window.scrollTo({ top: text.offsetTop - 100, behavior: "smooth" });
    }));

  // ---- typing by hand clears nothing, but a typed complaint needs no check box ----
  text.addEventListener("input", () => { if (!$("upload_id").value) setFromAudio(false); });

  // ---- double submission guard (the server also refuses a reused submission key) ----
  form.addEventListener("submit", (e) => {
    if (submitBtn.dataset.sent) { e.preventDefault(); return; }
    submitBtn.dataset.sent = "1";
    submitBtn.disabled = true;
    submitBtn.textContent = "पाठवत आहे… / Submitting…";
  });
})();
