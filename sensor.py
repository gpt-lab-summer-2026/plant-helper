# handle moisture sensor and ESP32 audio streaming
import load_data
import serial
import json
from datetime import datetime

active_plant = load_data.read()
last_watering_date = active_plant.get('last_watered')

def read_serial_frame(ser):
    """
    Read one JSON line from the ESP32.
    Returns 
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
