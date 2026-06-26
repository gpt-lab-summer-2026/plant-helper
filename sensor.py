# handle moisture sensor things
import load_data
import serial
import json
from datetime import datetime

SERIAL_PORT = "/dev/ttyS0"  # or /dev/ttyAMA0, check with `ls /dev/tty*`
BAUD_RATE = 9600

ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=2)
active_plant = load_data.read()  # Load active plant data
last_watering_date = active_plant.get('last_watered')  # Initialize from saved data

def read_sensors() -> dict:
    """
    Read a JSON line from ESP and return parsed sensor data.
    Returns empty dict on read failure.
    """
    try:
        line = ser.readline().decode("utf-8").strip()
        return json.loads(line)
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        print(f"Sensor read error: {e}")
        return {}

def get_moisture(sensor_data: dict) -> int | None:
    """
    Extract moisture value from sensor data.
    Raw value: 0 (wet) to 1023 (dry) on most ESP ADCs.
    """
    return sensor_data.get("moisture")

def is_dry(moisture_value: int, threshold: int = 700) -> bool:
    """
    Returns True if soil needs watering.
    Adjust threshold by calibrating your specific sensor.
    """
    return moisture_value > threshold

def update_watering_date(previous_dry: bool, current_dry: bool) -> datetime | None:
    """
    Detects dry -> moist transition as a watering event.
    Update last_watering_date in plant_profile.json
    """
    global last_watering_date
    if previous_dry and not current_dry:
        last_watering_date = datetime.now()
        print(f"Watering detected at {last_watering_date}")
        load_data.update_plant(active_plant.get('plant_name'), last_watered=last_watering_date.isoformat())
    return last_watering_date

def cleanup():
    ser.close()