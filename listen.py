import numpy
import webrtcvad
import sounddevice as sd
from sensor import *

from faster_whisper import WhisperModel

ALLOWED_LANGUAGES = ["fi", "en"]
DEFAULT_LANGUAGE = "fi"

model_wake = WhisperModel("small", device="cpu", compute_type="int8")
model_sleep = WhisperModel("tiny", device="cpu", compute_type="int8")
vad = webrtcvad.Vad()
vad.set_mode(3)


def _has_audio_device():
    try:
        devices = sd.query_devices()
        return any(d['max_input_channels'] > 0 for d in devices)
    except Exception:
        return False


def _keyboard_fallback(prompt="Type your message: "):
    try:
        text = input(prompt).strip()
        fi_chars = set("äöåÄÖÅ")
        language = "fi" if any(c in fi_chars for c in text) else DEFAULT_LANGUAGE
        return text, language
    except EOFError:
        return None, DEFAULT_LANGUAGE


def _resample(audio, orig_rate, target_rate):
    """Linear interpolation resample — good enough for speech."""
    if orig_rate == target_rate:
        return audio
    new_len = int(len(audio) * target_rate / orig_rate)
    old_idx = numpy.linspace(0, len(audio) - 1, new_len)
    return numpy.interp(old_idx, numpy.arange(len(audio)), audio).astype(numpy.float32)


def _transcribe(recording_float32, fs, model, initial_prompt=None):
    if recording_float32 is None or len(recording_float32) == 0:
        print("No speech detected.")
        return None, DEFAULT_LANGUAGE

    audio_16k = _resample(recording_float32, fs, 16000)

    detected, _, _ = model.detect_language(audio_16k)
    language = detected if detected in ALLOWED_LANGUAGES else DEFAULT_LANGUAGE
    print(f"Detected language: {detected}, using: {language}")

    segments, _ = model.transcribe(
        audio_16k,
        language=language,
        initial_prompt=initial_prompt,
        condition_on_previous_text=False,
        temperature=0.0,
    )
    text = "".join(segment.text for segment in segments).strip().rstrip(".!?,;:")
    print(f"Transcription: {text}")

    return text, language


def listen_sleep(ser, audio_device=None):
    if not _has_audio_device():
        print("Audio input unavailable, falling back to keyboard")
        return _keyboard_fallback("Wake word: ")

    fs = 32000
    chunk_size = 960  # 30ms at 16kHz, required by webrtcvad
    silence_limit = 30
    pre_buffer_size = 5

    silence_count = 0
    speech_detected = False
    recorded_chunks = []
    pre_buffer = []

    try:
        with sd.InputStream(samplerate=fs, channels=1, dtype="int16", device=audio_device) as stream:
            print("listenning")
            while True:
                 # ledi päälle
                ser.write(b"START\n")
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
            ser.write(b"STOP\n")
    except Exception as e:
        print(f"Audio error: {e}, falling back to keyboard")
        return _keyboard_fallback("Wake word: ")

    if not recorded_chunks:
        print("No speech detected.")
        return None, DEFAULT_LANGUAGE

    recording_int16 = numpy.concatenate(recorded_chunks)
    recording_float32 = recording_int16.astype("float32") / 32768.0
    return _transcribe(recording_float32, fs, model_sleep)


def listen_conversation(ser, audio_device=None):
    if not _has_audio_device():
        print("Audio input unavailable, falling back to keyboard")
        return _keyboard_fallback("Type your message: ")

    fs = 32000
    chunk_size = 960  # 30ms at 16kHz, required by webrtcvad
    silence_limit = 30
    pre_buffer_size = 5

    silence_count = 0
    speech_detected = False
    recorded_chunks = []
    pre_buffer = []

   
    try:
        with sd.InputStream(samplerate=fs, channels=1, dtype="int16", device=audio_device) as stream:
            print("speak now")
            while True:
                # ledi päälle
                ser.write(b"START\n")
                raw_chunk, _ = stream.read(chunk_size)
                chunk = raw_chunk.flatten()
                raw = chunk.tobytes()
                is_speech = vad.is_speech(raw, sample_rate=fs)

                if is_speech:
                    #print("speech")
                    if not speech_detected:
                        recorded_chunks.extend(pre_buffer)
                        pre_buffer.clear()
                    silence_count = 0
                    speech_detected = True
                elif speech_detected:
                    #print("silence")
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
            ser.write(b"STOP\n")
    except Exception as e:
        print(f"Audio error: {e}, falling back to keyboard")
        return _keyboard_fallback("Type your message: ")

    if not recorded_chunks:
        print("No speech detected.")
        return None, DEFAULT_LANGUAGE

    recording_int16 = numpy.concatenate(recorded_chunks)
    recording_float32 = recording_int16.astype("float32") / 32768.0

    initial_prompt = (
        "Talking to a houseplant. How are you? Are you thirsty? What's your name? Should I water you?"
        "How do your leaves look? Is your soil dry? Can I help you somehow?"
        "Tarvitsetko vettä tai valoa? Mikä on nimesi? Miten voit?"
    )
    return _transcribe(recording_float32, fs, model_wake, initial_prompt=initial_prompt)
