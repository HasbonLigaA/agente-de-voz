let sessionId = null;
let lastAudio = null;
let chatBusy = false;
let sttBackendOk = false;
let publicMicUrl = null;

const logEl = document.getElementById("log");
const form = document.getElementById("chat-form");
const messageEl = document.getElementById("message");
const sendBtn = document.getElementById("send");
const newSessionBtn = document.getElementById("new-session");
const healthEl = document.getElementById("health");
const micBtn = document.getElementById("mic-btn");
const micStatusEl = document.getElementById("mic-status");
const httpsBannerEl = document.getElementById("https-banner");
const httpsBannerLinkEl = document.getElementById("https-banner-link");

let micStream = null;
let mediaRecorder = null;
let recordedChunks = [];
let micRecording = false;
let recordStartedAt = 0;

function isIOS() {
  return (
    /iPad|iPhone|iPod/.test(navigator.userAgent) ||
    (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1)
  );
}

function micAllowedHere() {
  return Boolean(window.isSecureContext);
}

function ensureMediaDevices() {
  if (!navigator.mediaDevices) {
    navigator.mediaDevices = {};
  }
  if (navigator.mediaDevices.getUserMedia) {
    return true;
  }
  const legacy =
    navigator.getUserMedia ||
    navigator.webkitGetUserMedia ||
    navigator.mozGetUserMedia;
  if (!legacy) {
    return false;
  }
  navigator.mediaDevices.getUserMedia = (constraints) =>
    new Promise((resolve, reject) => {
      legacy.call(navigator, constraints, resolve, reject);
    });
  return true;
}

function normalizeWords(text) {
  const m = text.toLowerCase().match(/[a-záéíóúüñ]+/gi);
  return m || [];
}

function isRepetitiveGarbage(text) {
  const words = normalizeWords(text);
  if (words.length < 2) return false;
  const counts = {};
  for (const w of words) counts[w] = (counts[w] || 0) + 1;
  const max = Math.max(...Object.values(counts));
  if (max >= 2 && words.length <= 4) return true;
  return max >= 3 && max / words.length >= 0.45;
}

function appendBubble(role, text) {
  const div = document.createElement("div");
  div.className = `bubble ${role}`;
  const label = role === "user" ? "Tú" : "Agente";
  div.innerHTML = `<span class="role">${label}</span>${escapeHtml(text)}`;
  logEl.appendChild(div);
  logEl.scrollTop = logEl.scrollHeight;
}

function escapeHtml(s) {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function waitForPaint() {
  return new Promise((resolve) => {
    requestAnimationFrame(() => requestAnimationFrame(resolve));
  });
}

function setMicStatus(text, active = false) {
  if (!micStatusEl) return;
  micStatusEl.textContent = text;
  micStatusEl.classList.toggle("active", active);
}

function setComposerDisabled(disabled) {
  chatBusy = disabled;
  sendBtn.disabled = disabled;
  messageEl.disabled = disabled;
  if (micBtn) micBtn.disabled = disabled;
}

function updateHttpsBanner() {
  if (!httpsBannerEl || !httpsBannerLinkEl) return;
  if (micAllowedHere()) {
    httpsBannerEl.classList.add("hidden");
    return;
  }
  const url = publicMicUrl || "";
  if (!url || url.startsWith("http://")) {
    httpsBannerEl.classList.remove("hidden");
    httpsBannerLinkEl.textContent = "Esperando URL HTTPS del servidor…";
    httpsBannerLinkEl.removeAttribute("href");
    return;
  }
  httpsBannerEl.classList.remove("hidden");
  httpsBannerLinkEl.href = url;
  httpsBannerLinkEl.textContent = url.replace(/^https:\/\//, "");
}

function redirectToMicHttpsUrl() {
  if (!publicMicUrl || !publicMicUrl.startsWith("https://")) {
    setMicStatus(
      "Micrófono requiere HTTPS. Abre el enlace amarillo arriba o pide la URL segura al administrador."
    );
    return false;
  }
  if (publicMicUrl.replace(/\/$/, "") === window.location.origin.replace(/\/$/, "")) {
    return true;
  }
  window.location.href = publicMicUrl;
  return false;
}

async function refreshHealth() {
  try {
    const res = await fetch("/api/health", { cache: "no-store" });
    const data = await res.json();
    sttBackendOk = Boolean(data.stt_available);
    if (data.public_https_url) {
      publicMicUrl = data.public_https_url;
    }
    const engine = data.stt_engine || "whisper";
    const wh = data.whisper_model ? `/${data.whisper_model}` : "";
    const micHint = micAllowedHere() ? "mic OK" : "mic→HTTPS";
    healthEl.textContent = sttBackendOk
      ? `Backend · ${data.ollama_model} · ${engine}${wh} · ${micHint}`
      : `Backend · pip install faster-whisper imageio-ffmpeg`;
    healthEl.className = "health ok";
    updateHttpsBanner();
  } catch {
    sttBackendOk = false;
    healthEl.textContent = "Backend apagado (inicia uvicorn en este equipo).";
    healthEl.className = "health err";
  }
}

async function playAudioBase64(b64) {
  if (!b64) return;
  if (lastAudio) {
    lastAudio.pause();
    URL.revokeObjectURL(lastAudio.src);
  }
  const binary = atob(b64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  lastAudio = new Audio(URL.createObjectURL(new Blob([bytes], { type: "audio/mpeg" })));
  try {
    await lastAudio.play();
  } catch {
    /* autoplay puede pedir gesto del usuario en móvil */
  }
}

async function sendChatMessage(text) {
  const trimmed = text.trim();
  if (!trimmed || chatBusy) return;
  if (isRepetitiveGarbage(trimmed)) {
    setMicStatus("Texto repetido/confuso. Repite o escribe.");
    return;
  }

  appendBubble("user", trimmed);
  messageEl.value = "";
  setComposerDisabled(true);
  await waitForPaint();

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: trimmed, session_id: sessionId }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Error en el chat");
    sessionId = data.session_id;
    appendBubble("assistant", data.reply_text);
    await playAudioBase64(data.audio_base64);
  } catch (err) {
    appendBubble("assistant", `Error: ${err.message}`);
  } finally {
    setComposerDisabled(false);
    messageEl.focus();
  }
}

async function transcribeBlob(blob, mime) {
  const ext = mime.includes("mp4") ? "m4a" : mime.includes("ogg") ? "ogg" : "webm";
  const formData = new FormData();
  formData.append("audio", blob, `voz.${ext}`);
  const res = await fetch("/api/transcribe", { method: "POST", body: formData });
  let data = {};
  try {
    data = await res.json();
  } catch {
    throw new Error(`Transcripción falló (HTTP ${res.status})`);
  }
  if (!res.ok) throw new Error(data.detail || "Error al transcribir");
  return { text: data.text, raw: data.raw_text || null };
}

function pickRecorderMime() {
  const types = isIOS()
    ? ["audio/mp4", "audio/aac", "audio/webm;codecs=opus", "audio/webm", "audio/ogg;codecs=opus"]
    : ["audio/webm;codecs=opus", "audio/webm", "audio/ogg;codecs=opus", "audio/mp4"];
  for (const t of types) {
    if (typeof MediaRecorder !== "undefined" && MediaRecorder.isTypeSupported(t)) {
      return t;
    }
  }
  return "";
}

function releaseMicStream() {
  if (micStream) {
    micStream.getTracks().forEach((t) => t.stop());
    micStream = null;
  }
}

async function stopRecorderAndGetBlob(recorder) {
  return new Promise((resolve) => {
    const mime = recorder.mimeType || pickRecorderMime() || "audio/webm";
    recorder.addEventListener(
      "stop",
      () => {
        setTimeout(() => {
          resolve(new Blob(recordedChunks, { type: mime }));
        }, 250);
      },
      { once: true }
    );
    try {
      if (recorder.state === "recording") recorder.requestData();
    } catch {
      /* ignore */
    }
    recorder.stop();
  });
}

async function startMicRecording() {
  if (micRecording || chatBusy) return;
  await refreshHealth();

  if (!micAllowedHere()) {
    if (!redirectToMicHttpsUrl()) return;
  }

  if (!sttBackendOk) {
    setMicStatus("Instala: pip install faster-whisper imageio-ffmpeg python-multipart");
    return;
  }

  if (typeof MediaRecorder === "undefined") {
    setMicStatus("Este navegador no puede grabar audio. Prueba Chrome o Safari actualizado.");
    return;
  }

  if (!ensureMediaDevices()) {
    setMicStatus("Micrófono no disponible en este navegador.");
    return;
  }

  try {
    micStream = await navigator.mediaDevices.getUserMedia({
      audio: {
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      },
      video: false,
    });
  } catch (err) {
    const name = err?.name || "";
    if (name === "NotAllowedError" || name === "PermissionDeniedError") {
      setMicStatus("Permiso de micrófono denegado. Actívalo en ajustes del navegador.");
    } else if (name === "NotFoundError") {
      setMicStatus("No se encontró micrófono en este dispositivo.");
    } else {
      setMicStatus(`No se pudo usar el micrófono (${name || "error"}).`);
    }
    return;
  }

  recordedChunks = [];
  const mime = pickRecorderMime();
  try {
    mediaRecorder = mime ? new MediaRecorder(micStream, { mimeType: mime }) : new MediaRecorder(micStream);
  } catch {
    try {
      mediaRecorder = new MediaRecorder(micStream);
    } catch {
      releaseMicStream();
      setMicStatus("No se pudo iniciar la grabación en este dispositivo.");
      return;
    }
  }

  mediaRecorder.ondataavailable = (e) => {
    if (e.data && e.data.size > 0) recordedChunks.push(e.data);
  };

  try {
    mediaRecorder.start(isIOS() ? 1000 : 250);
  } catch {
    releaseMicStream();
    mediaRecorder = null;
    setMicStatus("Error al grabar. Vuelve a pulsar 🎤.");
    return;
  }

  recordStartedAt = Date.now();
  micRecording = true;
  micBtn?.classList.add("listening");
  setMicStatus("● GRABANDO… habla 4–6 s claro y pulsa 🎤 otra vez.", true);
}

async function stopMicRecording(send) {
  if (!micRecording && !mediaRecorder) return;

  const recorder = mediaRecorder;
  const elapsed = Date.now() - recordStartedAt;
  micRecording = false;
  micBtn?.classList.remove("listening");
  mediaRecorder = null;

  if (!recorder || recorder.state === "inactive") {
    releaseMicStream();
    if (send) setMicStatus("No se grabó. Pulsa 🎤 y habla.");
    return;
  }

  const blob = await stopRecorderAndGetBlob(recorder);
  releaseMicStream();
  recordedChunks = [];

  if (!send) {
    setMicStatus("Grabación cancelada.");
    return;
  }

  if (elapsed < 1200) {
    setMicStatus("Muy rápido. Mantén 🎤 al menos 2 s hablando.");
    return;
  }

  if (blob.size < 800) {
    setMicStatus(`Audio muy bajo (${blob.size} bytes). Habla más fuerte/cerca del mic.`);
    return;
  }

  setMicStatus(`Enviando audio (${Math.round(blob.size / 1024)} KB) a transcribir…`, true);
  setComposerDisabled(true);

  try {
    const { text, raw } = await transcribeBlob(blob, blob.type);
    if (!text?.trim()) {
      setMicStatus("No se entendió. Intenta otra vez.");
      return;
    }
    if (isRepetitiveGarbage(text)) {
      setMicStatus("Transcripción confusa. Repite más despacio o escribe.");
      messageEl.value = text;
      return;
    }
    messageEl.value = text;
    if (raw) {
      setMicStatus(`Corregido por IA · antes: «${raw.slice(0, 50)}…»`);
    } else {
      setMicStatus(`OK: «${text.slice(0, 70)}${text.length > 70 ? "…" : ""}»`);
    }
    await sendChatMessage(text);
    setMicStatus("");
  } catch (err) {
    setMicStatus(String(err.message || err));
  } finally {
    setComposerDisabled(false);
  }
}

micBtn?.addEventListener("click", () => {
  if (micRecording) void stopMicRecording(true);
  else void startMicRecording();
});

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  if (micRecording) await stopMicRecording(false);
  await sendChatMessage(messageEl.value);
});

newSessionBtn.addEventListener("click", () => {
  if (micRecording) void stopMicRecording(false);
  sessionId = null;
  logEl.innerHTML = "";
  messageEl.focus();
});

httpsBannerLinkEl?.addEventListener("click", (e) => {
  if (!publicMicUrl || !publicMicUrl.startsWith("https://")) {
    e.preventDefault();
    void refreshHealth();
  }
});

refreshHealth();
setInterval(() => {
  if (!micAllowedHere() && (!publicMicUrl || !publicMicUrl.startsWith("https://"))) {
    void refreshHealth();
  }
}, 8000);
