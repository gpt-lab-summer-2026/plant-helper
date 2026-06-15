import wave
import numpy
import webrtcvad
import whisper
import sounddevice as sd

ALLOWED_LANGUAGES = ["fi", "en"]
DEFAULT_LANGUAGE = "fi"

model = whisper.load_model("small")
vad = webrtcvad.Vad()
vad.set_mode(2)

def listen():
    fs = 16000
    chunk_size = 480  # 30ms at 16kHz, required by webrtcvad
    silence_limit = 30
    pre_buffer_size = 5

    silence_count = 0
    speech_detected = False
    recorded_chunks = []
    pre_buffer = []

    print("speak now")
    with sd.InputStream(samplerate=fs, channels=1, dtype="int16") as stream:
        while True:
            raw_chunk, _ = stream.read(chunk_size)
            chunk = raw_chunk.flatten()
            raw = chunk.tobytes()
            is_speech = vad.is_speech(raw, sample_rate=fs)

            if is_speech:
                if not speech_detected:
                    recorded_chunks.extend(pre_buffer)
                    pre_buffer.clear()
                silence_count = 0
                speech_detected = True
            elif speech_detected:
                silence_count += 1
                if silence_count >= silence_limit:
                    print(f"Stopped after {silence_limit} silence chunks")
                    break
            else:
                pre_buffer.append(chunk)
                if len(pre_buffer) > pre_buffer_size:
                    pre_buffer.pop(0)

            if speech_detected:
                recorded_chunks.append(chunk)

    if not recorded_chunks:
        print("No speech detected.")
        return None, DEFAULT_LANGUAGE

    recording_int16 = numpy.concatenate(recorded_chunks)

    # float32 version for Whisper language detection
    recording_float32 = whisper.pad_or_trim(recording_int16.astype("float32") / 32768.0)
    mel = whisper.log_mel_spectrogram(recording_float32, n_mels=model.dims.n_mels).to(model.device)
    _, probs = model.detect_language(mel)
    detected = max(probs, key=probs.get)
    language = detected if detected in ALLOWED_LANGUAGES else DEFAULT_LANGUAGE
    print(f"Detected language: {detected}, using: {language}")

    result = model.transcribe(recording_float32, language=language,
                              initial_prompt="Talking to a houseplant. How are you? Are you thirsty? What's your name? Should I water you?"
                              "How do your leaves look? Is your soil dry? Can I help you somehow?"
                              "Tarvitsetko vettä tai valoa? Mikä on nimesi? Miten voit?",
                              condition_on_previous_text=False,
                              temperature=0)
    text = result["text"].strip()
    print(f"Transcription: {text}")
    return text, language
        