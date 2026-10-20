let sessionId = null;
let lastAudio = null;
let chatBusy = false;
let sttBackendOk = false;

const ASSISTANT_NAME = "La Liga AmaSalvarVidas";
const LOGO_URL = "/static/logo-liga.png";

const logEl = document.getElementById("log");
const form = document.getElementById("chat-form");
const messageEl = document.getElementById("message");
const sendBtn = document.getElementById("send");
const newSessionBtn = document.getElementById("new-session");
const healthEl = document.getElementById("health");
const micBtn = document.getElementById("mic-btn");
const micStatusEl = document.getElementById("mic-status");
const presenceEl = document.getElementById("assistant-presence");
const avatarEl = document.getElementById("assistant-avatar");
const presenceLabelEl = document.getElementById("presence-label");
const emptyStateEl = document.getElementById("empty-state");

let appHttpsUrl = null;

let micStream = null;
let mediaRecorder = null;
let recordedChunks = [];
let micRecording = false;
let recordStartedAt = 0;
let presenceMode = null;

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

function setAssistantPresence(mode) {
  presenceMode = mode;
  if (!presenceEl || !avatarEl) return;
  if (!mode) {
    presenceEl.hidden = true;
    avatarEl.classList.remove("speaking", "thinking");
    return;
  }
  presenceEl.hidden = false;
  avatarEl.classList.toggle("speaking", mode === "speaking");
  avatarEl.classList.toggle("thinking", mode === "thinking");
  if (presenceLabelEl) {
    presenceLabelEl.textContent =
      mode === "speaking" ? "Hablando…" : "Preparando respuesta…";
  }
}

function bindAudioPresence(audio) {
  const clear = () => {
    if (lastAudio === audio) setAssistantPresence(null);
  };
  audio.addEventListener("ended", clear);
  audio.addEventListener("pause", clear);
  audio.addEventListener("error", clear);
}

function appendBubble(role, text) {
  const row = document.createElement("div");
  row.className = `msg-row ${role}`;

  if (role === "assistant") {
    const img = document.createElement("img");
    img.className = "msg-avatar";
    img.src = LOGO_URL;
    img.alt = "";
    row.appendChild(img);
  }

  const div = document.createElement("div");
  div.className = `bubble ${role}`;
  const label = role === "user" ? "Tú" : ASSISTANT_NAME;
  div.innerHTML = `<span class="role">${label}</span>${escapeHtml(text)}`;
  row.appendChild(div);
  logEl.appendChild(row);
  logEl.classList.add("has-messages");
  logEl.scrollTop = logEl.scrollHeight;
}

function syncEmptyState() {
  if (!logEl) return;
  logEl.classList.toggle("has-messages", logEl.children.length > 0);
}

function autoResizeMessageField() {
  if (!messageEl) return;
  messageEl.style.height = "auto";
  messageEl.style.height = `${Math.min(messageEl.scrollHeight, 120)}px`;
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

function normalizeOrigin(url) {
  return (url || "").replace(/\/$/, "");
}

async function ensureSecureContextForMic() {
  if (window.isSecureContext) return true;
  if (!appHttpsUrl) return false;
  const here = normalizeOrigin(window.location.origin);
  const target = normalizeOrigin(appHttpsUrl);
  if (here === target) return true;
  window.location.replace(appHttpsUrl);
  return false;
}

async function refreshHealth() {
  try {
    const res = await fetch("/api/health", { cache: "no-store" });
    const data = await res.json();
    sttBackendOk = Boolean(data.stt_available);
    if (data.app_https_url) {
      appHttpsUrl = data.app_https_url;
    }
    const engine = data.stt_engine || "auto";
    const sttLang = data.stt_language || "es-CO";
    const whLang = data.whisper_language || "es";
    const wh = data.whisper_model ? `/${data.whisper_model}` : "";
    const micHint = window.isSecureContext ? "micrófono disponible" : "micrófono vía HTTPS";
    healthEl.textContent = sttBackendOk ? "En línea" : "Parcial";
    healthEl.title = sttBackendOk
      ? `STT ${engine} · ${sttLang} · whisper=${whLang}${wh} · ${data.ollama_model || "LLM"} · ${micHint}`
      : "Instala faster-whisper e imageio-ffmpeg";
    healthEl.className = "status-pill ok";
    if (!window.isSecureContext && appHttpsUrl) {
      await ensureSecureContextForMic();
    }
  } catch {
    sttBackendOk = false;
    healthEl.textContent = "Sin conexión";
    healthEl.title = "Servicio no disponible. Inicia el servidor en este equipo.";
    healthEl.className = "status-pill err";
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
  const audio = new Audio(URL.createObjectURL(new Blob([bytes], { type: "audio/mpeg" })));
  lastAudio = audio;
  bindAudioPresence(audio);
  setAssistantPresence("speaking");
  try {
    await audio.play();
  } catch {
    setAssistantPresence(null);
  }
}

async function fetchSpeechAndPlay(replyText) {
  if (!replyText?.trim()) return;
  try {
    const res = await fetch("/api/speech", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: replyText }),
    });
    const data = await res.json();
    if (!res.ok) {
      setAssistantPresence(null);
      return;
    }
    if (data.audio_base64) await playAudioBase64(data.audio_base64);
    else setAssistantPresence(null);
  } catch {
    setAssistantPresence(null);
  }
}

function playReplyVoice(data) {
  if (data.audio_base64) void playAudioBase64(data.audio_base64);
  else void fetchSpeechAndPlay(data.reply_text);
}

async function sendChatMessage(
  text,
  { fromVoice = false, fastReturn = false, skipUserBubble = false } = {}
) {
  const trimmed = text.trim();
  if (!trimmed || chatBusy) return;
  if (isRepetitiveGarbage(trimmed)) {
    setMicStatus("Texto repetido o poco claro. Repite o escribe.");
    return;
  }

  if (!skipUserBubble) appendBubble("user", trimmed);
  messageEl.value = "";
  setComposerDisabled(true);
  setAssistantPresence("thinking");
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
    if (fastReturn) {
      playReplyVoice(data);
    } else if (data.audio_base64) {
      await playAudioBase64(data.audio_base64);
    } else {
      void fetchSpeechAndPlay(data.reply_text);
    }
  } catch (err) {
    setAssistantPresence(null);
    appendBubble("assistant", `Error: ${err.message}`);
  } finally {
    setComposerDisabled(false);
    messageEl.focus();
    if (fromVoice) setMicStatus("");
  }
}

async function transcribeBlob(blob, mime, filename) {
  let ext = "webm";
  if (filename && filename.includes(".")) {
    ext = filename.split(".").pop().toLowerCase();
  } else if (mime.includes("mp4") || mime.includes("m4a")) {
    ext = "m4a";
  } else if (mime.includes("ogg")) {
    ext = "ogg";
  } else if (mime.includes("wav")) {
    ext = "wav";
  } else if (mime.includes("mpeg") || mime.includes("mp3")) {
    ext = "mp3";
  }
  const formData = new FormData();
  formData.append("audio", blob, filename || `voz.${ext}`);
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
        }, 80);
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

async function sendTranscribedAudio(blob, filename) {
  const mime = blob.type || "application/octet-stream";
  setMicStatus("Transcribiendo audio…", true);
  setComposerDisabled(true);
  try {
    const { text } = await transcribeBlob(blob, mime, filename);
    if (!text?.trim()) {
      setMicStatus("No se entendió. Intenta de nuevo.");
      return;
    }
    messageEl.value = "";
    setMicStatus("");
    appendBubble("user", text);
    void sendChatMessage(text, { fromVoice: true, fastReturn: true, skipUserBubble: true });
  } catch (err) {
    setMicStatus(String(err.message || err));
    setComposerDisabled(false);
  }
}

async function startMicRecording() {
  if (micRecording || chatBusy) return;
  await refreshHealth();

  if (!window.isSecureContext) {
    if (!(await ensureSecureContextForMic())) {
      setMicStatus(
        appHttpsUrl
          ? `Redirigiendo a ${appHttpsUrl.replace(/^https:\/\//, "")} para activar el micrófono…`
          : "El micrófono requiere HTTPS. Configura APP_PUBLIC_HTTPS_URL en el servidor."
      );
    }
    return;
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
    setMicStatus("Error al grabar. Vuelve a pulsar el micrófono.");
    return;
  }

  recordStartedAt = Date.now();
  micRecording = true;
  micBtn?.classList.add("listening");
  setMicStatus("Grabando… habla con claridad y pulsa el micrófono otra vez para enviar.", true);
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
    if (send) setMicStatus("No se grabó. Pulsa el micrófono y habla.");
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
    setMicStatus("Muy breve. Mantén el micrófono al menos 2 segundos mientras hablas.");
    return;
  }

  if (blob.size < 800) {
    setMicStatus(`Audio muy bajo (${blob.size} bytes). Habla más fuerte o más cerca del micrófono.`);
    return;
  }

  await sendTranscribedAudio(blob);
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
  syncEmptyState();
  setAssistantPresence(null);
  messageEl.focus();
});

document.querySelectorAll(".chip[data-prompt]").forEach((btn) => {
  btn.addEventListener("click", () => {
    const prompt = btn.getAttribute("data-prompt");
    if (!prompt || chatBusy) return;
    void sendChatMessage(prompt);
  });
});

messageEl?.addEventListener("input", autoResizeMessageField);

refreshHealth();
