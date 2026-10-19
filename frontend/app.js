let sessionId = null;
let lastAudio = null;
let chatBusy = false;
let sttBackendOk = false;

const logEl = document.getElementById("log");
const form = document.getElementById("chat-form");
const messageEl = document.getElementById("message");
const sendBtn = document.getElementById("send");
const newSessionBtn = document.getElementById("new-session");
const healthEl = document.getElementById("health");
const micBtn = document.getElementById("mic-btn");
const micStatusEl = document.getElementById("mic-status");

let micStream = null;
let mediaRecorder = null;
let recordedChunks = [];
let micRecording = false;
let recordStartedAt = 0;

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

async function refreshHealth() {
  try {
    const res = await fetch("/api/health", { cache: "no-store" });
    const data = await res.json();
    sttBackendOk = Boolean(data.stt_available);
    const engine = data.stt_engine || "whisper";
    const wh = data.whisper_model ? `/${data.whisper_model}` : "";
    healthEl.textContent = sttBackendOk
      ? `Backend · ${data.ollama_model} · mic→${engine}${wh}`
      : `Backend · pip install faster-whisper imageio-ffmpeg`;
    healthEl.className = "health ok";
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
  await lastAudio.play();
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
  for (const t of ["audio/webm;codecs=opus", "audio/webm", "audio/ogg;codecs=opus", "audio/mp4"]) {
    if (MediaRecorder.isTypeSupported(t)) return t;
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
    const mime = recorder.mimeType || "audio/webm";
    recorder.addEventListener(
      "stop",
      () => {
        setTimeout(() => {
          resolve(new Blob(recordedChunks, { type: mime }));
        }, 200);
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
  if (!sttBackendOk) {
    setMicStatus("Instala: pip install faster-whisper imageio-ffmpeg python-multipart");
    return;
  }
  if (!navigator.mediaDevices?.getUserMedia) {
    setMicStatus("Micrófono no soportado aquí. Usa Chrome en localhost.");
    return;
  }

  try {
    micStream = await navigator.mediaDevices.getUserMedia({
      audio: {
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
        channelCount: 1,
        sampleRate: { ideal: 48000 },
      },
    });
  } catch {
    setMicStatus("Permiso de micrófono denegado (candado en la barra de direcciones).");
    return;
  }

  recordedChunks = [];
  const mime = pickRecorderMime();
  try {
    mediaRecorder = mime ? new MediaRecorder(micStream, { mimeType: mime }) : new MediaRecorder(micStream);
  } catch {
    mediaRecorder = new MediaRecorder(micStream);
  }

  mediaRecorder.ondataavailable = (e) => {
    if (e.data && e.data.size > 0) recordedChunks.push(e.data);
  };

  mediaRecorder.start(250);
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

refreshHealth();
