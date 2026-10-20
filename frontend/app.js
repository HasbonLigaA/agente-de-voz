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
let voiceTurnAbort = null;

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

function decodeHeaderUtf8(b64) {
  if (!b64) return "";
  try {
    const binary = atob(b64);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
    return new TextDecoder().decode(bytes);
  } catch {
    return "";
  }
}

function appendVoiceTurnToChat(userText, replyText) {
  const user = userText.trim();
  const reply = replyText.trim();
  if (user) appendBubble("user", user);
  if (reply) appendBubble("assistant", reply);
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

function isAssistantSpeaking() {
  return Boolean(lastAudio && !lastAudio.paused && !lastAudio.ended);
}

function interruptVoicePipeline() {
  speechGeneration += 1;
  if (voiceTurnAbort) {
    voiceTurnAbort.abort();
    voiceTurnAbort = null;
  }
  if (lastAudio) {
    lastAudio.pause();
    lastAudio.currentTime = 0;
    if (lastAudio.src?.startsWith("blob:")) URL.revokeObjectURL(lastAudio.src);
    lastAudio = null;
  }
  voiceBusy = false;
  setVoiceAvatarState(null);
}

function stopActiveSpeech() {
  interruptVoicePipeline();
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

function b64ToMp3Blob(b64) {
  const binary = atob(b64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  return new Blob([bytes], { type: "audio/mpeg" });
}

function playAudioBlobAwait(blob, gen = speechGeneration) {
  return new Promise((resolve) => {
    if (!blob?.size || gen !== speechGeneration) {
      resolve();
      return;
    }
    if (lastAudio) {
      lastAudio.pause();
      if (lastAudio.src?.startsWith("blob:")) URL.revokeObjectURL(lastAudio.src);
    }
    const audio = new Audio(URL.createObjectURL(blob));
    lastAudio = audio;
    const finish = () => {
      if (lastAudio === audio && lastAudio.src?.startsWith("blob:")) {
        URL.revokeObjectURL(lastAudio.src);
      }
      if (lastAudio === audio) lastAudio = null;
      resolve();
    };
    audio.addEventListener("ended", finish);
    audio.addEventListener("error", finish);
    setVoiceAvatarState("speaking");
    setVoiceModeStatus("Hablando… · pulsa el mic para cortar");
    audio.play().catch(finish);
  });
}

async function playAudioBlob(blob, gen = speechGeneration) {
  await playAudioBlobAwait(blob, gen);
  if (gen === speechGeneration) {
    setVoiceAvatarState(null);
    setVoiceModeStatus("Listo · pulsa para hablar");
    voiceBusy = false;
  }
}

async function consumeVoiceNdjsonStream(res, gen) {
  const reader = res.body?.getReader();
  if (!reader) throw new Error("Respuesta de voz inválida.");
  const decoder = new TextDecoder();
  let lineBuf = "";
  let assistantShown = false;
  let playChain = Promise.resolve();
  let streamDone = false;

  setVoiceModeStatus("Pensando…");
  setVoiceAvatarState("thinking");

  const finishIfIdle = () => {
    playChain.then(() => {
      if (!streamDone || gen !== speechGeneration) return;
      setVoiceAvatarState(null);
      setVoiceModeStatus("Listo · pulsa para hablar");
      voiceBusy = false;
    });
  };

  while (true) {
    const { done, value } = await reader.read();
    if (gen !== speechGeneration) {
      try {
        await reader.cancel();
      } catch {
        /* ignore */
      }
      return;
    }
    if (value?.length) lineBuf += decoder.decode(value, { stream: true });
    if (done) lineBuf += decoder.decode();
    let nl;
    while ((nl = lineBuf.indexOf("\n")) >= 0) {
      const line = lineBuf.slice(0, nl).trim();
      lineBuf = lineBuf.slice(nl + 1);
      if (!line) continue;
      let evt;
      try {
        evt = JSON.parse(line);
      } catch {
        continue;
      }
      if (evt.type === "reply" && !assistantShown) {
        const reply = String(evt.text || "").trim();
        if (reply) appendBubble("assistant", reply);
        assistantShown = true;
        setVoiceModeStatus("Generando voz…");
      }
      if (evt.type === "audio" && evt.data) {
        voiceBusy = false;
        const b64 = evt.data;
        playChain = playChain.then(async () => {
          if (gen !== speechGeneration) return;
          await playAudioBlobAwait(b64ToMp3Blob(b64), gen);
        });
      }
      if (evt.type === "error") {
        throw new Error(evt.detail || "Error en modo voz");
      }
      if (evt.type === "done") {
        streamDone = true;
        finishIfIdle();
      }
    }
    if (done) break;
  }
  if (!streamDone && gen === speechGeneration) {
    streamDone = true;
    finishIfIdle();
  }
}

async function consumeSpeechStream(res, gen) {
  const reader = res.body?.getReader();
  if (!reader) throw new Error("Respuesta de voz inválida.");
  const parts = [];
  setVoiceModeStatus("Generando voz…");
  setVoiceAvatarState("thinking");

  while (true) {
    const { done, value } = await reader.read();
    if (gen !== speechGeneration) {
      try {
        await reader.cancel();
      } catch {
        /* ignore */
      }
      return;
    }
    if (value?.length) parts.push(value);
    if (done) break;
  }

  if (gen !== speechGeneration || !parts.length) return;
  voiceBusy = false;
  const blob = new Blob(parts, { type: "audio/mpeg" });
  await playAudioBlob(blob, gen);
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
  if (micRecording) return;
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

function voiceTurnFilename(blob) {
  const t = blob.type || "";
  if (t.includes("mp4")) return "voz.m4a";
  if (t.includes("ogg")) return "voz.ogg";
  if (t.includes("wav")) return "voz.wav";
  return "voz.webm";
}

async function processVoiceTurn(blob) {
  interruptVoicePipeline();
  const gen = speechGeneration;
  voiceBusy = true;
  voiceTurnAbort = new AbortController();

  const formData = new FormData();
  formData.append("audio", blob, voiceTurnFilename(blob));
  if (sessionId) formData.append("session_id", sessionId);

  try {
    setVoiceModeStatus("Procesando tu mensaje…");
    setVoiceAvatarState("thinking");
    const res = await fetch("/api/voice/turn", {
      method: "POST",
      body: formData,
      signal: voiceTurnAbort.signal,
    });
    if (!res.ok) {
      let detail = "Error en modo voz";
      try {
        const errBody = await res.json();
        detail = errBody.detail || detail;
      } catch {
        /* ignore */
      }
      throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
    }
    const sid = res.headers.get("X-Session-Id");
    if (sid) sessionId = sid;
    const userFromVoice = decodeHeaderUtf8(res.headers.get("X-Voice-User-Text"));
    if (userFromVoice.trim()) appendBubble("user", userFromVoice.trim());

    const contentType = res.headers.get("content-type") || "";
    if (contentType.includes("ndjson")) {
      await consumeVoiceNdjsonStream(res, gen);
    } else {
      const replyFromHeader = decodeHeaderUtf8(res.headers.get("X-Voice-Reply-Text"));
      if (replyFromHeader.trim()) appendBubble("assistant", replyFromHeader.trim());
      await consumeSpeechStream(res, gen);
    }
  } catch (err) {
    if (err?.name === "AbortError" || gen !== speechGeneration) return;
    setVoiceModeStatus(String(err.message || err));
    setVoiceAvatarState(null);
    voiceBusy = false;
  } finally {
    voiceTurnAbort = null;
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
  interruptVoicePipeline();
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
  try {
    if (micRecording) {
      await stopMicRecording(true);
      return;
    }
    if (voiceBusy || isAssistantSpeaking()) {
      interruptVoicePipeline();
      setVoiceModeStatus("Grabando… pulsa otra vez para enviar");
    }
    await startMicRecording();
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
