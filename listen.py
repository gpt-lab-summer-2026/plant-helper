import whisper
import sounddevice as sd
import numpy
# listen to user

ALLOWED_LANGUAGES = ["fi", "en"]
DEFAULT_LANGUAGE = "fi"

# load whisper model, only once 
model = whisper.load_model("small")

# listen function
def listen():
    fs = 16000
    # record audio
    # TO DO: stop recording when no one is speaking, esim. webrtcvad
    duration = 5  # seconds
    print("speak now")
    myrecording = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype="float32")
    sd.wait()
    myrecording=numpy.squeeze(myrecording)

    # Pad audio to 30 seconds as Whisper expects
    myrecording = whisper.pad_or_trim(myrecording)
    
    mel = whisper.log_mel_spectrogram(myrecording, n_mels=model.dims.n_mels).to(model.device)
    _, probs = model.detect_language(mel)
    detected = max(probs, key=probs.get)

    # Use detected language if allowed, otherwise fall back to default
    language = detected if detected in ALLOWED_LANGUAGES else DEFAULT_LANGUAGE
    print(f"Detected language: {detected}, using: {language}")

    transcription = model.transcribe(myrecording, language=language)

    print(transcription["text"])
    return (transcription["text"], language)

# test print
# print(listen())