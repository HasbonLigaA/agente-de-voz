"""Modo voz: LLM en streaming + TTS por segmentos (primer audio antes de que termine Ollama)."""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import re
import threading
from collections.abc import AsyncIterator

from backend.brand import sanitize_institution_name
from backend.grounded_llm import stream_answer_from_catalog
from backend.tts import synthesize_speech
from backend.tts_prepare import compress_reply_for_voice

logger = logging.getLogger(__name__)

_MIN_SEGMENT = 28
_MAX_SEGMENT = 220


def _ndjson(obj: dict) -> bytes:
    return (json.dumps(obj, ensure_ascii=False) + "\n").encode("utf-8")


def _pop_segment(buffer: str) -> tuple[str | None, str]:
    if not buffer.strip():
        return None, buffer

    nl = buffer.find("\n")
    if nl >= 0 and nl >= _MIN_SEGMENT - 1:
        line = buffer[:nl].strip()
        rest = buffer[nl + 1 :]
        if line:
            return line, rest

    if len(buffer) >= _MAX_SEGMENT:
        cut = buffer[:_MAX_SEGMENT].rsplit(" ", 1)[0].strip()
        if len(cut) >= _MIN_SEGMENT:
            return cut, buffer[len(cut) :].lstrip()

    m = re.search(r"(?<=[.!?…])\s+", buffer)
    if m and m.start() >= _MIN_SEGMENT - 1:
        seg = buffer[: m.end()].strip()
        return seg, buffer[m.end() :]

    return None, buffer


async def _llm_token_queue(history: list[dict[str, str]], *, for_voice: bool) -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue()

    def worker() -> None:
        try:
            for token in stream_answer_from_catalog(history, for_voice=for_voice):
                q.put_nowait(("token", token))
            q.put_nowait(("done", None))
        except Exception as exc:
            q.put_nowait(("error", exc))

    threading.Thread(target=worker, daemon=True).start()
    return q


class _AudioScheduler:
    def __init__(self, tts_max_chars: int) -> None:
        self._tts_max_chars = tts_max_chars
        self._sem = asyncio.Semaphore(2)
        self._seq = 0
        self._tasks: dict[int, asyncio.Task[bytes]] = {}
        self._next_emit = 0
        self._spoken_chars = 0

    async def _synth(self, text: str) -> bytes:
        if self._tts_max_chars > 0:
            remaining = self._tts_max_chars - self._spoken_chars
            if remaining <= 0:
                return b""
            if len(text) > remaining:
                text = text[: max(0, remaining - 1)].rsplit(" ", 1)[0]
        if not text.strip():
            return b""
        async with self._sem:
            return await synthesize_speech(text)

    def push(self, segment: str) -> None:
        seg = compress_reply_for_voice(segment, max_chars=0)
        if not seg.strip():
            return
        seq = self._seq
        self._seq += 1
        self._spoken_chars += len(seg)
        self._tasks[seq] = asyncio.create_task(self._synth(seg))

    async def flush_ready(self) -> list[bytes]:
        out: list[bytes] = []
        while self._next_emit in self._tasks:
            task = self._tasks[self._next_emit]
            if not task.done():
                break
            try:
                audio = task.result()
                if audio:
                    out.append(audio)
            except Exception as exc:
                logger.warning("TTS segment %s failed: %s", self._next_emit, exc)
            del self._tasks[self._next_emit]
            self._next_emit += 1
        return out

    async def finish(self) -> list[bytes]:
        if self._tasks:
            await asyncio.gather(*self._tasks.values(), return_exceptions=True)
        out: list[bytes] = []
        while self._next_emit < self._seq:
            emitted = await self.flush_ready()
            if emitted:
                out.extend(emitted)
            elif self._next_emit in self._tasks:
                await asyncio.sleep(0.02)
            else:
                break
        return out


async def voice_turn_ndjson_stream(
    history: list[dict[str, str]],
    *,
    for_voice: bool,
    tts_max_chars: int,
) -> AsyncIterator[bytes]:
    q = await _llm_token_queue(history, for_voice=for_voice)
    buffer = ""
    parts: list[str] = []
    audio = _AudioScheduler(tts_max_chars)

    while True:
        kind, data = await q.get()
        if kind == "error":
            yield _ndjson({"type": "error", "detail": str(data)})
            return
        if kind == "done":
            break
        parts.append(str(data))
        buffer += str(data)
        while True:
            seg, buffer = _pop_segment(buffer)
            if not seg:
                break
            audio.push(seg)
        for chunk in await audio.flush_ready():
            yield _ndjson(
                {"type": "audio", "data": base64.b64encode(chunk).decode("ascii")}
            )

    tail = buffer.strip()
    if tail:
        audio.push(tail)

    full = sanitize_institution_name("".join(parts).strip())
    if not full:
        yield _ndjson({"type": "error", "detail": "Respuesta vacía del modelo"})
        return

    yield _ndjson({"type": "reply", "text": full})

    for chunk in await audio.finish():
        yield _ndjson({"type": "audio", "data": base64.b64encode(chunk).decode("ascii")})

    yield _ndjson({"type": "done"})
