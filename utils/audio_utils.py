import soundfile as sf
import io

def bytes_to_file(audio_bytes: bytes, filename: str):
    with open(filename, "wb") as f:
        f.write(audio_bytes)

def file_to_bytes(filename: str) -> bytes:
    with open(filename, "rb") as f:
        return f.read()
