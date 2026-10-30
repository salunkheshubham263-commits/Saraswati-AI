import json
import os
import re
import subprocess
import sys
import tempfile
import threading
import unicodedata
from ctypes.util import find_library
from pathlib import Path
from typing import Tuple
import numpy as np
import torch
import torch.nn as nn
import soundfile as sf
from misaki.espeak import EspeakWrapper

espeak_library = next(
    (
        path
        for path in (
            "/usr/lib64/libespeak-ng.so.1",
            "/usr/lib/x86_64-linux-gnu/libespeak-ng.so.1",
            "/lib64/libespeak-ng.so.1",
            "/lib/x86_64-linux-gnu/libespeak-ng.so.1",
        )
        if os.path.exists(path)
    ),
    None,
) or find_library("espeak-ng")
if espeak_library:
    EspeakWrapper.set_library(espeak_library)

espeak_data_path = next(
    (
        path
        for path in (
            "/usr/share/espeak-ng-data",
            "/usr/local/share/espeak-ng-data",
            "/usr/lib/espeak-ng-data",
            "/usr/lib64/espeak-ng-data",
            "/usr/lib/x86_64-linux-gnu/espeak-ng-data",
        )
        if os.path.isdir(path)
    ),
    None,
)
if espeak_data_path:
    EspeakWrapper.set_data_path(espeak_data_path)

from kokoro import KPipeline

# Keep the import path compatible with your current project layout.
ENGINE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ENGINE_DIR))
from tools.terminal_tool import SafeTerminalRunner
from tools.app_launcher import SafeAppLauncher


class IntentClassifierNN(nn.Module):
    """Must match the architecture used by train_intent.py."""

    def __init__(self, input_size: int, hidden_size: int, output_size: int):
        super().__init__()
        self.layer1 = nn.Linear(input_size, hidden_size)
        self.relu = nn.ReLU()
        self.layer2 = nn.Linear(hidden_size, output_size)

    def forward(self, x):
        x = self.layer1(x)
        x = self.relu(x)
        return self.layer2(x)


class SaraswatiEngine:
    def __init__(self, model_dir: str | Path):
        model_dir = Path(model_dir).expanduser()
        self.model_path = model_dir / "saraswati_intent_model.pth"
        self.vocab_path = model_dir / "vocab.json"

        self.terminal_tool = SafeTerminalRunner()
        self.app_launcher = SafeAppLauncher()

        print("Initializing Kokoro English voice engine...")
        self.tts_pipeline = KPipeline(
            lang_code="a",
            repo_id="hexgrad/Kokoro-82M",
        )
        self.voice_name = "af_heart"
        self._tts_lock = threading.Lock()

        self.stt_model = None
        self.recorder = None

        self._load_model_and_vocab()
        self.conversation_history = []
        self.max_history = 10

    @staticmethod
    def normalize_text(text: str) -> str:
        text = unicodedata.normalize("NFKC", text).lower().strip()
        text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
        return re.sub(r"\s+", " ", text)

    def _load_model_and_vocab(self):
        if not self.model_path.is_file():
            raise FileNotFoundError(f"Model not found: {self.model_path}")
        if not self.vocab_path.is_file():
            raise FileNotFoundError(f"Vocabulary not found: {self.vocab_path}")

        with self.vocab_path.open("r", encoding="utf-8") as file:
            self.vocab = json.load(file)

        try:
            checkpoint = torch.load(
                self.model_path, map_location="cpu", weights_only=False
            )
        except TypeError:
            checkpoint = torch.load(self.model_path, map_location="cpu")

        self.intent_map = {
            int(index): intent
            for index, intent in checkpoint["intent_map"].items()
        }

        self.model = IntentClassifierNN(
            input_size=checkpoint["input_size"],
            hidden_size=checkpoint["hidden_size"],
            output_size=checkpoint["output_size"],
        )
        self.model.load_state_dict(checkpoint["model_state"])
        self.model.eval()

    def _text_to_vector(self, text: str) -> torch.Tensor:
        normalized = self.normalize_text(text)
        vector = torch.zeros(len(self.vocab), dtype=torch.float32)

        for token in normalized.split():
            index = self.vocab.get(token)
            if index is not None:
                vector[index] = 1.0

        return vector

    def predict_intent(self, text: str) -> Tuple[str, float]:
        normalized = self.normalize_text(text)
        if not normalized:
            return "unknown", 0.0

        vector = self._text_to_vector(text)
        if not torch.any(vector):
            return "unknown", 0.0

        with torch.no_grad():
            logits = self.model(vector.unsqueeze(0))
            probabilities = torch.softmax(logits, dim=1)
            confidence_tensor, class_tensor = torch.max(probabilities, dim=1)

        confidence = float(confidence_tensor.item())
        intent = self.intent_map.get(int(class_tensor.item()), "unknown")

        if confidence < 0.70:
            return "unknown", confidence

        return intent, confidence

    def generate_audio(self, text: str) -> Tuple[np.ndarray, int]:
        if not text or not text.strip():
            raise ValueError("Speech text must not be empty.")

        audio_chunks = []
        with self._tts_lock:
            for _, _, audio in self.tts_pipeline(
                text.strip(), voice=self.voice_name, speed=1.0
            ):
                if isinstance(audio, torch.Tensor):
                    audio = audio.detach().cpu().numpy()
                audio_chunks.append(np.asarray(audio, dtype=np.float32).reshape(-1))

        if not audio_chunks:
            raise RuntimeError("Kokoro produced no audio for the supplied text.")

        return np.concatenate(audio_chunks), 24000

    def speak(self, text: str):
        if not text or not text.strip():
            return

        print(f'Saraswati speaking: "{text}"')
        audio_path = None
        try:
            audio, sample_rate = self.generate_audio(text)
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as audio_file:
                audio_path = audio_file.name
            sf.write(audio_path, audio, sample_rate)
            subprocess.run(
                ["aplay", audio_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=30,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired, RuntimeError, ValueError) as error:
            print(f"TTS error: {error}")
        finally:
            if audio_path:
                Path(audio_path).unlink(missing_ok=True)

    def process_query(self, user_query: str):
        if not user_query.strip():
            return

        # Handle explicit request to view recent conversation history
        if user_query.lower() in {"history", "show history", "chat history"}:
            print("\n--- Recent Conversation History ---")
            if not self.conversation_history:
                print("No conversation history recorded yet.")
            for i, turn in enumerate(self.conversation_history, 1):
                print(f"[{i}] User: {turn['user']}")
                print(f"    Saraswati: {turn['assistant']}")
            print("-----------------------------------")
            return

        print(f"\nUser query: {user_query}")
        intent, confidence = self.predict_intent(user_query)
        print(f"Detected intent: {intent} (confidence: {confidence:.2f})")

        actions = {
            "list_files": ("ls -la", "Here are your directory files"),
            "show_user": ("whoami", "You are currently logged in as"),
            "show_date": ("date", "Today's date and time is"),
            "system_uptime": ("uptime", "Here is the system uptime"),
            "os_info": ("uname -a", "Here is your operating system kernel information"),
            "disk_space": ("df -h", "Here is the disk space usage"),
            "process_management": ("ps aux --sort=-%cpu", "Here are the running system processes"),
        }

        if intent == "unknown" or (intent not in actions and intent != "launch_app"):
            response = "I could not understand that request"
            print("Unsupported request.")
            self.speak(response)
            return

        # Handle application launcher intent separately
        if intent == "launch_app":
            query_lower = user_query.lower()
            target_app = None
            if "firefox" in query_lower:
                target_app = "firefox"
            elif "vlc" in query_lower:
                target_app = "vlc"
            elif "browser" in query_lower or "chrome" in query_lower:
                target_app = "chrome"
            elif "terminal" in query_lower:
                target_app = "terminal"

            if target_app is None:
                response = "Please specify an application to launch."
            else:
                result = self.app_launcher.launch_application(target_app)
                response = (
                    f"Launching {target_app}."
                    if result.get("success", False)
                    else f"Unable to launch {target_app}: {result.get('error', 'unknown error')}"
                )

            # Log turn to conversation history
            self.conversation_history.append({
                "user": user_query,
                "assistant": response
            })
            if len(self.conversation_history) > self.max_history:
                self.conversation_history.pop(0)

            self.speak(response)
            return

        command, base_response = actions[intent]
        result = self.terminal_tool.execute_command(command)

        if not result.get("success", False):
            response = f"Unable to execute that action: {result.get('error', 'unknown error')}"
            self.speak(response)
            return

        output = str(result.get("output", "")).strip()
        if intent == "process_management" and output:
            output = "\n".join(output.splitlines()[:10])
        response = base_response

        if output:
            print(f"\n[Terminal Output]:\n{output}\n")

        if intent in {"show_user", "show_date"} and output:
            response = f"{response} {output}"
        elif intent in {"system_uptime", "disk_space", "os_info"} and output:
            response = f"{response}. {output}"
        elif intent == "list_files" and output:
            response = f"{response}."
        elif intent == "process_management" and output:
            response = f"{response}."

        # Append this turn to conversation history
        self.conversation_history.append({
            "user": user_query,
            "assistant": response
        })
        
        # Trim history if it exceeds the maximum window size
        if len(self.conversation_history) > self.max_history:
            self.conversation_history.pop(0)

        self.speak(response)

    def transcribe_audio(self, audio_path: str) -> str:
        if self.stt_model is None:
            from faster_whisper import WhisperModel

            print("Initializing Faster-Whisper STT Engine...")
            self.stt_model = WhisperModel(
                "small",
                device="cpu",
                compute_type="int8",
                cpu_threads=4,
            )

        segments, info = self.stt_model.transcribe(
            audio_path,
            beam_size=1,             # Optimized greedy decoding for speed on long text
            without_timestamps=True, # Avoids overhead from calculating word timestamps
            vad_filter=True,
        )

        segments = list(segments)
        transcript = " ".join(
            segment.text.strip()
            for segment in segments
            if segment.text.strip()
        ).strip()

        print(f"Detected language: {info.language} (probability: {info.language_probability:.2f})")
        print(f"Transcribed Text: {transcript!r}")

        return transcript

    def run(self):
        print("=" * 54)
        print("       SARASWATI AI DESKTOP ASSISTANT ONLINE")
        print("       Type 'exit' or 'quit' to shut down")
        print("=" * 54)

        self.speak("Saraswati assistant is online and ready.")

        while True:
            try:
                mode = input("\nSaraswati [t = type, v = voice, exit = quit] ❯ ").strip().lower()
                if mode in {"exit", "quit"}:
                    print("Shutting down Saraswati...")
                    self.speak("Goodbye.")
                    break
                elif mode == "v":
                    if self.recorder is None:
                        from tools.audio_recorder import AudioRecorder

                        self.recorder = AudioRecorder()
                    try:
                        audio_file = self.recorder.record_to_file()
                        user_input = self.transcribe_audio(audio_file)
                    except (OSError, RuntimeError) as error:
                        print(f"Voice input failed: {error}")
                        continue
                else:
                    user_input = input("Saraswati (Type) ❯ ").strip()

                if user_input:
                    self.process_query(user_input)

            except KeyboardInterrupt:
                print("\nShutting down...")
                break
            except EOFError:
                print("\nInput ended. Shutting down...")
                break


if __name__ == "__main__":
    model_directory = ENGINE_DIR / "models"
    assistant = SaraswatiEngine(model_directory)
    assistant.run()