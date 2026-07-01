# handle moisture sensor and ESP32 audio streaming
import load_data
import serial
import json
import numpy
from datetime import datetime

AUDIO_SAMPLE_RATE = 8000  # 
_AUDIO_BATCH_SIZE = 64
AUDIO_ENERGY_THRESHOLD = 350  # RMS above this = speech (silence ~220-235, speech ~300+)

active_plant = load_data.read()
last_watering_date = active_plant.get('last_watered')


def read_serial_frame(ser):
    """
    Read one JSON line from the ESP32.
    Returns ('audio', list[int]) for mic batches,
            ('moisture', int)    for moisture readings,
            (None, None)         on empty/error.
    """
    if ser is None:
        return None, None
    try:
        line = ser.readline().decode("utf-8").strip()
        if not line:
            return None, None
        data, _ = json.JSONDecoder().raw_decode(line)
        if not isinstance(data, dict):
            return None, None
        if "a" in data:
            return "audio", data["a"]
        if "m" in data:
            return "moisture", data["m"]
        # backward compat with old {"moisture": ..., "mic_level": ...} format
        if "moisture" in data:
            return "moisture", data["moisture"]
        return None, None
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        print(f"Serial frame error: {e}")
        ser.reset_input_buffer()
        return None, None


def read_sensors(ser) -> dict:
    """
    Drain audio frames until a moisture frame arrives (or up to 200 frames).
    Returns {'moisture': value} or {}.
    """
    if ser is None:
        return {}
    for _ in range(200):
        kind, value = read_serial_frame(ser)
        if kind == "moisture":
            return {"moisture": value}
        if kind is None:
            break
    return {}


def test_mic(ser, duration_sec=3):
    """
    Record for a fixed duration and print RMS levels — no VAD, no silence detection.
    Use this to verify the mic is sending audio before using record_from_esp.
    """
    if ser is None:
        print("No serial connection.")
        return None

    max_frames = int(duration_sec * AUDIO_SAMPLE_RATE / _AUDIO_BATCH_SIZE)
    all_samples = []

    print(f"Recording for {duration_sec}s... speak into the mic")
    for i in range(max_frames):
        kind, value = read_serial_frame(ser)
        if kind != "audio":
            continue
        batch = numpy.array(value, dtype=numpy.float32)
        rms = numpy.sqrt(numpy.mean((batch - 2048.0) ** 2))
        print(f"  frame {i:3d}  RMS={rms:.1f}")
        all_samples.extend(value)

    if not all_samples:
        print("No audio frames received.")
        return None

    raw = numpy.array(all_samples, dtype=numpy.float32)
    audio = (raw - 2048.0) / 2048.0
    print(f"Done. {len(all_samples)} samples, peak={numpy.max(numpy.abs(audio)):.3f}")
    return audio


def record_from_esp(ser, silence_ms=800, energy_threshold=AUDIO_ENERGY_THRESHOLD, max_sec=10, debug=True):
    """
    Record audio from the ESP32 serial stream using simple energy-based VAD.
    Waits for speech (energy > threshold), then records until silence_ms of quiet.
    Returns a float32 numpy array normalised to [-1, 1] at AUDIO_SAMPLE_RATE Hz,
    or None if no speech was detected or ser is None.
    """
    if ser is None:
        return None

    silence_frames_needed = max(1, int((silence_ms / 1000) * AUDIO_SAMPLE_RATE / _AUDIO_BATCH_SIZE))
    max_frames = int(max_sec * AUDIO_SAMPLE_RATE / _AUDIO_BATCH_SIZE)
    pre_buffer_size = 4  # frames to keep before speech starts (~128ms at 2kHz)

    all_samples = []
    pre_buffer = []
    speech_started = False
    silent_count = 0

    for _ in range(max_frames):
        kind, value = read_serial_frame(ser)
        if kind != "audio":
            continue

        batch = numpy.array(value, dtype=numpy.float32)
        rms = numpy.sqrt(numpy.mean((batch - 2048.0) ** 2))

        if debug:
            state = "SPEECH" if rms > energy_threshold else "silence"
            print(f"  RMS={rms:6.1f}  [{state}]", flush=True)

        if rms > energy_threshold:
            if not speech_started:
                # prepend buffered frames so the word start isn't clipped
                for pre in pre_buffer:
                    all_samples.extend(pre)
                pre_buffer.clear()
            speech_started = True
            silent_count = 0
            all_samples.extend(value)
        elif speech_started:
            all_samples.extend(value)
            silent_count += 1
            if silent_count >= silence_frames_needed:
                break
        else:
            pre_buffer.append(value)
            if len(pre_buffer) > pre_buffer_size:
                pre_buffer.pop(0)

    if not all_samples:
        return None

    raw = numpy.array(all_samples, dtype=numpy.float32)
    return (raw - 2048.0) / 2048.0  # normalise 12-bit (0-4095) to [-1, 1]


def get_moisture(sensor_data: dict) -> int | None:
    return sensor_data.get("moisture")


def is_dry(moisture_value: int, threshold: int = 3000) -> bool:
    return moisture_value > threshold


def update_watering_date(previous_dry: bool, current_dry: bool) -> datetime | None:
    global last_watering_date
    if previous_dry and not current_dry:
        last_watering_date = datetime.now()
        print(f"Watering detected at {last_watering_date}")
        load_data.update_plant(active_plant.get('plant_name'), last_watered=last_watering_date.isoformat())
    return last_watering_date


def cleanup(ser):
    if ser is None:
        return
    ser.close()
