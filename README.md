# Saraswati

Saraswati uses a local Ollama model as its primary action planner. The model
receives the request on localhost and returns a structured plan; the backend
validates each action against the built-in tool allowlist. If Ollama is stopped
or its model is missing, the app reports and uses the existing intent planner as
a limited fallback. The React/Tauri client includes English browser speech
recognition for input and receives Kokoro WAV audio from the backend for output;
it does not use browser or operating-system speech synthesis.

Supported plan tools include disk, process, file, date, uptime, operating-system
queries; allowlisted desktop app launches; and visible browser navigation.
Email drafts are prepared by the local model and must be reviewed in the UI.
Sending requires an explicit **Send Email** click and runs in a visible
Playwright browser.

## Backend setup

Use Python 3.10 or newer. On Debian/Ubuntu, install the native audio libraries:

```sh
sudo apt install espeak-ng libsndfile1 portaudio19-dev
```

Install the Python dependencies:

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
```

Install Ollama and download a local model once while online:

```sh
ollama pull qwen2.5:3b
```

Start the Ollama service before starting Saraswati (for example, `ollama serve`
in a separate terminal if it is not managed by your system). Inference runs against
`http://127.0.0.1:11434` and does not send prompts to a hosted API. To use another
model, set `OLLAMA_MODEL` to its installed Ollama model tag. The default is
`qwen2.5:3b`. `OLLAMA_HOST` can change the local port but is restricted to
localhost; `OLLAMA_TIMEOUT_SECONDS` defaults to 90.

The backend searches standard Linux locations and the system library registry for
eSpeak NG and its data directory. Kokoro downloads its model and voice assets on
the first run and reuses the local Hugging Face cache afterward.
For visible Gmail automation, install Playwright's Chromium browser if Google
Chrome is not already installed:

```sh
python -m playwright install chromium
```

Email drafts are shown in the UI for editing. The explicit **Send Email** action
opens a visible browser using Saraswati's persistent browser profile and sends
the reviewed draft; sign in to Gmail in that browser when prompted.

Start the backend from the project root:

```sh
python -m uvicorn api:app --app-dir saraswati_engine --host 127.0.0.1 --port 8000
```

The API exposes `POST /api/query` (JSON `{ "query": "..." }`) and
`POST /api/speak` (JSON `{ "text": "..." }`). Both responses include
`audio_base64`, containing a WAV payload encoded as base64. Responses and speech
are English-only.

## React/Tauri client

```sh
cd saraswati-ui
npm install
npm run dev
```

The Vite development server uses port 1420 and the client connects to
`http://127.0.0.1:8000`. Build the desktop UI with `npm run build`; run Tauri
development mode with `npm run tauri dev`.

The repository contains the shared React/Tauri client but no separate Android
application or Android-specific backend binding.
