import json
import re
import subprocess
import wave
from pathlib import Path

from vosk import Model, KaldiRecognizer


BASE_DIR = Path(__file__).resolve().parent
VOSK_MODEL_PATH = BASE_DIR / "model" / "vosk-ru"


vosk_model = Model(str(VOSK_MODEL_PATH))


FILLER_WORDS = [
    "ээ", "эм", "мм", "ну", "короче", "типа", "как бы",
    "блин", "алло", "слушай", "это", "значит"
]


def convert_audio_to_wav(source_path: str) -> str:
    source = Path(source_path)
    wav_path = source.with_suffix(".wav")

    command = [
        "ffmpeg",
        "-y",
        "-i", str(source),
        "-ac", "1",
        "-ar", "16000",
        str(wav_path)
    ]

    subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

    return str(wav_path)


def transcribe_audio(audio_path: str) -> str:
    wav_path = convert_audio_to_wav(audio_path)

    result_text = []

    with wave.open(wav_path, "rb") as wf:
        recognizer = KaldiRecognizer(vosk_model, wf.getframerate())

        while True:
            data = wf.readframes(4000)
            if len(data) == 0:
                break

            if recognizer.AcceptWaveform(data):
                result = json.loads(recognizer.Result())
                result_text.append(result.get("text", ""))

        final_result = json.loads(recognizer.FinalResult())
        result_text.append(final_result.get("text", ""))

    return " ".join(result_text).strip()


def clean_transcript(text: str) -> str:
    text = text.lower()

    for word in FILLER_WORDS:
        pattern = rf"\b{re.escape(word)}\b"
        text = re.sub(pattern, " ", text)

    text = re.sub(r"\s+", " ", text)
    return text.strip()