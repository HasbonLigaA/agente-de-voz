# Agente de voz (MVP)

Conversación por **texto**; respuestas del modelo con **voz** vía Ollama + Edge TTS.

## Requisitos

- Python 3.11+
- Acceso de red al host Ollama (`OLLAMA_HOST`)
- Salida a internet para Edge TTS (Microsoft)

## Configuración

Toda la configuración (Ollama, TTS, STT, prompts, puerto) va en **`.env`**. El código lee solo `backend/config.py`.

Copia `.env.example` a `.env` y ajusta si hace falta:

```powershell
copy .env.example .env
```

## Ejecución

### Docker (recomendado en servidor)

```bash
cp .env.example .env   # y ajusta OLLAMA_HOST, etc.
docker compose up -d --build
```

La app queda en el puerto definido en `PORT` (por defecto **8767**), escuchando en todas las interfaces.

### Desarrollo local (Python)

```powershell
cd "c:\Dev\HASBON\Procesos\Agente de voz"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8767
```

Abre [http://127.0.0.1:8767](http://127.0.0.1:8767).

## Probar desde el celular

1. **Misma Wi‑Fi (rápido):** en una terminal del proyecto:
   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts\serve_mobile.ps1
   ```
   Abre en el celular la URL `http://TU_IP:8767` que imprime el script. Si no carga, permite Python en el firewall de Windows (red privada).

2. **Micrófono en el celular:** los navegadores exigen **HTTPS** para activar el micrófono. Abre `APP_PUBLIC_HTTPS_URL` (por defecto `https://seguimiento.laliga.org.co:8768`). Si entras por `http://160.2.1.22:8767`, la app te redirige sola al HTTPS. El certificado debe estar vigente (`*.laliga.org.co`).

El celular solo habla con tu PC; Ollama sigue en `OLLAMA_HOST` (no expongas el puerto 11434 a internet).

## Estructura

- `backend/` — API FastAPI, Ollama, TTS, sesiones en memoria
- `frontend/` — mini UI de prueba

## Próximos pasos (fase 2)

- Entrada por micrófono (STT)
- Persistencia de conversaciones
- Streaming de respuesta / voz
