import sounddevice as sd
import soundfile as sf
import numpy as np

class AudioRecorder:
    def __init__(self, sample_rate: int = 16000):  # Fixed type hint colon
        self.sample_rate = sample_rate

    def record_to_file(self, output_path: str = "/tmp/saraswati_input.wav"):
        print("\n🎤 Listening... Speak now (Press Enter to stop recording).")

        audio_data = []

        def callback(indata, frames, time, status):
            if status:
                print(status, flush=True)
            audio_data.append(indata.copy())

        try:
            with sd.InputStream(samplerate=self.sample_rate, channels=1, callback=callback):
                input()
        except sd.PortAudioError as error:
            raise RuntimeError(f"Unable to open the audio input device: {error}") from error

        if not audio_data:
            raise RuntimeError("No audio was captured from the input device.")

        audio_array = np.concatenate(audio_data, axis=0)
        sf.write(output_path, audio_array, self.sample_rate)
        print("🛑 Recording finished. Transcribing...")
        return output_path