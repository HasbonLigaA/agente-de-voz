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
const micStatusEl = document.getElementById("mic-status");
const voiceModeOpenBtn = document.getElementById("voice-mode-open");
const voiceModeEl = document.getElementById("voice-mode");
const voiceModeCloseBtn = document.getElementById("voice-mode-close");
const voiceModeMicBtn = document.getElementById("voice-mode-mic");
const voiceModeStatusEl = document.getElementById("voice-mode-status");
const voiceModeAvatarEl = document.getElementById("voice-mode-avatar");

let appHttpsUrl = null;
let micStream = null;
let mediaRecorder = null;
let recordedChunks = [];
let micRecording = false;
let recordStartedAt = 0;
let voiceModeOpen = false;
let voiceBusy = false;
let speechGeneration = 0;
let speechFetchAbort = null;

function isIOS() {
  return (
    /iPad|iPhone|iPod/.test(navigator.userAgent) ||
    (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1)
  );
}

function ensureMediaDevices() {
  if (!navigator.mediaDevices) navigator.mediaDevices = {};
  if (navigator.mediaDevices.getUserMedia) return true;
  const legacy =
    navigator.getUserMedia ||
    navigator.webkitGetUserMedia ||
    navigator.mozGetUserMedia;
  if (!legacy) return false;
  navigator.mediaDevices.getUserMedia = (constraints) =>
    new Promise((resolve, reject) => {
      legacy.call(navigator, constraints, resolve, reject);
    });
  return true;
}

function isRepetitiveGarbage(text) {
  const m = text.toLowerCase().match(/[a-záéíóúüñ]+/gi) || [];
  if (m.length < 2) return false;
  const counts = {};
  for (const w of m) counts[w] = (counts[w] || 0) + 1;
  const max = Math.max(...Object.values(counts));
  if (max >= 2 && m.length <= 4) return true;
  return max >= 3 && max / m.length >= 0.45;
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

function escapeHtml(s) {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
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
  if (voiceModeOpenBtn) voiceModeOpenBtn.disabled = disabled;
}

function unlockComposerFully() {
  setComposerDisabled(false);
}

function setVoiceModeStatus(text) {
  if (voiceModeStatusEl) voiceModeStatusEl.textContent = text;
}

function setVoiceAvatarState(state) {
  if (!voiceModeAvatarEl) return;
  voiceModeAvatarEl.classList.toggle("speaking", state === "speaking");
  voiceModeAvatarEl.classList.toggle("thinking", state === "thinking");
}

function stopActiveSpeech() {
  speechGeneration += 1;
  if (speechFetchAbort) {
    speechFetchAbort.abort();
    speechFetchAbort = null;
  }
  if (lastAudio) {
    lastAudio.pause();
    lastAudio.currentTime = 0;
    URL.revokeObjectURL(lastAudio.src);
    lastAudio = null;
  }
  setVoiceAvatarState(null);
}

async function refreshHealth() {
  try {
    const res = await fetch("/api/health", { cache: "no-store" });
    const data = await res.json();
    sttBackendOk = Boolean(data.stt_available);
    if (data.app_https_url) appHttpsUrl = data.app_https_url;
    healthEl.textContent = sttBackendOk ? "En línea" : "Parcial";
    healthEl.className = "status-pill ok";
    if (!window.isSecureContext && appHttpsUrl) {
      await ensureSecureContextForMic();
    }
  } catch {
    sttBackendOk = false;
    healthEl.textContent = "Sin conexión";
    healthEl.className = "status-pill err";
  }
}

async function ensureSecureContextForMic() {
  if (window.isSecureContext) return true;
  if (!appHttpsUrl) return false;
  const here = (window.location.origin || "").replace(/\/$/, "");
  const target = appHttpsUrl.replace(/\/$/, "");
  if (here === target) return true;
  window.location.replace(appHttpsUrl);
  return false;
}

async function playAudioBase64(b64, gen = speechGeneration) {
  if (!b64 || gen !== speechGeneration) return;
  if (lastAudio) {
    lastAudio.pause();
    URL.revokeObjectURL(lastAudio.src);
  }
  const binary = atob(b64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  const audio = new Audio(URL.createObjectURL(new Blob([bytes], { type: "audio/mpeg" })));
  lastAudio = audio;
  audio.addEventListener("ended", () => {
    if (lastAudio === audio && gen === speechGeneration) {
      setVoiceAvatarState(null);
      setVoiceModeStatus("Listo · pulsa para hablar");
      voiceBusy = false;
      if (voiceModeMicBtn) voiceModeMicBtn.disabled = false;
    }
  });
  setVoiceAvatarState("speaking");
  setVoiceModeStatus("Hablando…");
  try {
    await audio.play();
  } catch {
    if (gen === speechGeneration) {
      setVoiceAvatarState(null);
      voiceBusy = false;
      if (voiceModeMicBtn) voiceModeMicBtn.disabled = false;
    }
  }
}

async function fetchSpeechAndPlay(replyText, gen = speechGeneration) {
  if (!replyText?.trim() || gen !== speechGeneration) return;
  speechFetchAbort = new AbortController();
  try {
    const res = await fetch("/api/speech", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: replyText }),
      signal: speechFetchAbort.signal,
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Error al generar voz");
    await playAudioBase64(data.audio_base64, gen);
  } catch (err) {
    if (err?.name === "AbortError") return;
    setVoiceModeStatus(String(err.message || err));
    setVoiceAvatarState(null);
    voiceBusy = false;
    if (voiceModeMicBtn) voiceModeMicBtn.disabled = false;
  } finally {
    speechFetchAbort = null;
  }
}

async function sendChatMessage(text) {
  const trimmed = text.trim();
  if (!trimmed || chatBusy) return;
  if (isRepetitiveGarbage(trimmed)) {
    setMicStatus("Texto repetido o poco claro. Reformula tu pregunta.");
    return;
  }

  appendBubble("user", trimmed);
  messageEl.value = "";
  autoResizeMessageField();
  setComposerDisabled(true);

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
  } catch (err) {
    appendBubble("assistant", `Error: ${err.message}`);
  } finally {
    unlockComposerFully();
    messageEl.focus();
  }
}

async function transcribeBlob(blob, mime, filename) {
  let ext = "webm";
  if (filename?.includes(".")) ext = filename.split(".").pop().toLowerCase();
  else if (mime.includes("mp4")) ext = "m4a";
  else if (mime.includes("ogg")) ext = "ogg";
  else if (mime.includes("wav")) ext = "wav";
  const formData = new FormData();
  formData.append("audio", blob, filename || `voz.${ext}`);
  const res = await fetch("/api/transcribe", { method: "POST", body: formData });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Error al transcribir");
  return data.text;
}

function pickRecorderMime() {
  const types = isIOS()
    ? ["audio/webm;codecs=opus", "audio/webm", "audio/mp4", "audio/ogg;codecs=opus"]
    : ["audio/webm;codecs=opus", "audio/webm", "audio/ogg;codecs=opus", "audio/mp4"];
  for (const t of types) {
    if (typeof MediaRecorder !== "undefined" && MediaRecorder.isTypeSupported(t)) return t;
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
      () => setTimeout(() => resolve(new Blob(recordedChunks, { type: mime })), 80),
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

async function ensureMicReady() {
  if (!window.isSecureContext) {
    if (!(await ensureSecureContextForMic())) {
      throw new Error("El micrófono requiere HTTPS en este dispositivo.");
    }
  }
  if (!sttBackendOk) {
    throw new Error("Transcripción no disponible en el servidor.");
  }
  if (typeof MediaRecorder === "undefined" || !ensureMediaDevices()) {
    throw new Error("Micrófono no disponible en este navegador.");
  }
}

async function startMicRecording() {
  if (micRecording || voiceBusy) return;
  await refreshHealth();
  await ensureMicReady();

  micStream = await navigator.mediaDevices.getUserMedia({
    audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
    video: false,
  });

  recordedChunks = [];
  const mime = pickRecorderMime();
  try {
    mediaRecorder = mime
      ? new MediaRecorder(micStream, { mimeType: mime })
      : new MediaRecorder(micStream);
  } catch {
    mediaRecorder = new MediaRecorder(micStream);
  }

  mediaRecorder.ondataavailable = (e) => {
    if (e.data?.size > 0) recordedChunks.push(e.data);
  };
  mediaRecorder.start(isIOS() ? 1000 : 250);
  recordStartedAt = Date.now();
  micRecording = true;
  voiceModeMicBtn?.classList.add("listening");
  setVoiceModeStatus("Grabando… pulsa otra vez para enviar");
}

async function stopMicRecording(send) {
  if (!micRecording && !mediaRecorder) return;
  const recorder = mediaRecorder;
  const elapsed = Date.now() - recordStartedAt;
  micRecording = false;
  voiceModeMicBtn?.classList.remove("listening");
  mediaRecorder = null;

  if (!recorder || recorder.state === "inactive") {
    releaseMicStream();
    if (send) setVoiceModeStatus("No se grabó. Intenta otra vez.");
    return;
  }

  const blob = await stopRecorderAndGetBlob(recorder);
  releaseMicStream();
  recordedChunks = [];

  if (!send) {
    setVoiceModeStatus("Listo · pulsa para hablar");
    return;
  }
  if (elapsed < 900 || blob.size < 500) {
    setVoiceModeStatus("Muy breve. Habla al menos 1 segundo.");
    return;
  }
  await processVoiceTurn(blob);
}

async function processVoiceTurn(blob) {
  voiceBusy = true;
  if (voiceModeMicBtn) voiceModeMicBtn.disabled = true;
  stopActiveSpeech();
  const gen = speechGeneration;

  try {
    setVoiceModeStatus("Transcribiendo…");
    setVoiceAvatarState("thinking");
    const text = (await transcribeBlob(blob, blob.type)).trim();
    if (!text) throw new Error("No se entendió el audio.");

    setVoiceModeStatus("Pensando…");
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text, session_id: sessionId }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Error en el chat");
    sessionId = data.session_id;

    setVoiceModeStatus("Generando voz…");
    await fetchSpeechAndPlay(data.reply_text, gen);
  } catch (err) {
    if (gen === speechGeneration) {
      setVoiceModeStatus(String(err.message || err));
      setVoiceAvatarState(null);
      voiceBusy = false;
      if (voiceModeMicBtn) voiceModeMicBtn.disabled = false;
    }
  }
}

function openVoiceMode() {
  voiceModeOpen = true;
  if (voiceModeEl) {
    voiceModeEl.hidden = false;
    voiceModeEl.setAttribute("aria-hidden", "false");
  }
  setVoiceModeStatus("Listo · pulsa para hablar");
  void refreshHealth();
}

function closeVoiceMode() {
  if (micRecording) void stopMicRecording(false);
  stopActiveSpeech();
  voiceBusy = false;
  voiceModeOpen = false;
  if (voiceModeEl) {
    voiceModeEl.hidden = true;
    voiceModeEl.setAttribute("aria-hidden", "true");
  }
  if (voiceModeMicBtn) {
    voiceModeMicBtn.disabled = false;
    voiceModeMicBtn.classList.remove("listening");
  }
}

function autoResizeMessageField() {
  if (!messageEl) return;
  messageEl.style.height = "auto";
  messageEl.style.height = `${Math.min(messageEl.scrollHeight, 120)}px`;
}

voiceModeOpenBtn?.addEventListener("click", () => {
  if (chatBusy) return;
  openVoiceMode();
});

voiceModeCloseBtn?.addEventListener("click", closeVoiceMode);
voiceModeEl?.querySelector("[data-voice-close]")?.addEventListener("click", closeVoiceMode);

voiceModeMicBtn?.addEventListener("click", async () => {
  if (voiceBusy) return;
  try {
    if (micRecording) await stopMicRecording(true);
    else await startMicRecording();
  } catch (err) {
    setVoiceModeStatus(String(err.message || err));
  }
});

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  if (micRecording) await stopMicRecording(false);
  await sendChatMessage(messageEl.value);
});

messageEl?.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    form.requestSubmit();
  }
});

newSessionBtn.addEventListener("click", () => {
  closeVoiceMode();
  sessionId = null;
  logEl.innerHTML = "";
  syncEmptyState();
  setMicStatus("");
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

unlockComposerFully();
refreshHealth();
