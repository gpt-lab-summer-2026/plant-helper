import argparse
import datetime
import glob
import json
import os
import serial
import sys

import ollama
from ollama import chat
from llama_cpp import Llama

from listen import *
from speak import *
from load_data import *
from sensor import *

MAX_HISTORY = 20
STOP_WORD_FI = "lopeta keskustelu"
WAKE_WORD_FI = "aloita keskustelu"
STOP_WORD_EN = "stop conversation"
WAKE_WORD_EN = "start conversation"

waiting_mode = False

SERIAL_BAUDRATE = 115200
DEFAULT_SERIAL_PORTS = ["/dev/ttyUSB0", "/dev/ttyACM0"]


def find_serial_port(preferred_port=None, baudrate=SERIAL_BAUDRATE, timeout=2):
    candidates = []
    if preferred_port:
        candidates.append(preferred_port)
    candidates.extend(DEFAULT_SERIAL_PORTS)
    candidates.extend(glob.glob("/dev/ttyACM*"))
    candidates.extend(glob.glob("/dev/ttyUSB*"))
    candidates.extend(glob.glob("/dev/ttyAMA*"))
    candidates.extend(glob.glob("/dev/serial/by-id/*"))

    seen = []
    for port in candidates:
        if not port or port in seen:
            continue
        seen.append(port)
        try:
            print(f"Trying serial port {port}...")
            return serial.Serial(port, baudrate, timeout=timeout)
        except (serial.SerialException, FileNotFoundError) as e:
            print(f"Could not open serial port {port}: {e}")
    return None


def get_available_serial_ports():
    return sorted(set(glob.glob("/dev/ttyACM*") +
                      glob.glob("/dev/ttyUSB*") +
                      glob.glob("/dev/ttyAMA*") +
                      glob.glob("/dev/serial/by-id/*")))


parser = argparse.ArgumentParser(description="Run Plant Helper.")
parser.add_argument("--serial-port", help="Serial device path for ESP32 (e.g. /dev/ttyUSB0)")
parser.add_argument("--audio-device", help="Audio input device name or index for sounddevice")
parser.add_argument("--disable-sensors", action="store_true", help="Run without reading the ESP32 moisture sensor")
args = parser.parse_args()

preferred_port = args.serial_port or os.environ.get("PLANT_SERIAL_PORT")
audio_device = args.audio_device or os.environ.get("PLANT_AUDIO_DEVICE")
ser = None
if not args.disable_sensors:
    ser = find_serial_port(preferred_port)
    if ser is None:
        available_ports = get_available_serial_ports()
        print("Warning: Could not open any serial port for the ESP32 sensor.")
        print("Available serial devices:", ", ".join(available_ports) if available_ports else "(none)")
        print("Use --serial-port /dev/ttyUSB0 or set PLANT_SERIAL_PORT to select the correct port.")
        print("Continuing without sensor data.")
        if preferred_port:
            print(f"Tried preferred port: {preferred_port}")

previous_dry = False

# load plant profile and examples
plant_profile = read()
_all_examples = load_examples()

# read plant database data
try:
    with open('data/plant_database.json', 'r') as file:
        data = json.load(file)
    plant_database = data
    
except FileNotFoundError:
    print("Error: The file 'data.json' was not found.")

# look up just the matching species entry from the database
species = plant_profile['species'].lower()
plant_info_fi = next(
    (p for p in plant_database if species in p['common_name'].lower() and "fi" in p['language'] or species in p['scientific_name'].lower() and "fi" in p['language']),
    None
)
plant_info_en = next(
    (p for p in plant_database if species in p['common_name'].lower() and "en" in p['language'] or species in p['scientific_name'].lower() and "en" in p['language']),
    None
)

def _few_shot_messages(n=3):
    species_lower = plant_profile['species'].lower()
    matches = [e for e in _all_examples if species_lower in e['SYSTEM'].lower()]
    selected = matches[:n]
    msgs = []
    for ex in selected:
        msgs.append({"role": "user", "content": ex['INPUT']})
        msgs.append({"role": "assistant", "content": ex['OUTPUT']})
    return msgs

def _build_system_prompt(language):
    lang_name = 'Finnish' if language == 'fi' else 'English'
    name = plant_profile['plant_name']
    species = plant_profile['species']
    moisture = plant_profile['moisture_percentage']

    # watering rule from plant_database, matching the style in system_prompts examples
    plant_info = plant_info_fi if language == 'fi' else plant_info_en
    watering = plant_info['watering_recommendation'] if plant_info else "Water as needed"

    # extra facts from plant_database so the model can answer care questions accurately
    if plant_info:
        extras = (
            f"Light needs: {plant_info['light']}. "
            f"Humidity: {plant_info['humidity']}. "
            f"Pet safe: {'yes' if plant_info['pet_safe'] else 'no'}. "
            f"Soil: {plant_info['soil_type']}."
        )
    else:
        extras = ""

    return (
        f"IMPORTANT: Respond in {lang_name}."
        f"You are {name}, a {species} plant."
        f"Your soil moisture is currently {moisture}%."
        f"{watering}. "
        f"{extras} "
        f"Answer as the plant in a friendly tone, keep answers to 3 sentences. Only use text when generating answers."
        f"Only greet if the user greets you."
    )

def system_prompt(history, language):
    trimmed_history = history[-MAX_HISTORY:]
    print("trimmed history length: ", len(trimmed_history))
    few_shot = _few_shot_messages()
    print("thinking...")
    response = chat(
        model='gemma3:4b',
        messages=[
                {'role': 'system', 'content': _build_system_prompt(language)},
                *few_shot,
                *trimmed_history
                ]
    )
    reply = response.message.content
    reply = reply.removeprefix("assistant:").strip().rstrip("\\")
    print(reply)
    speak(reply, language)
    history.append({"role": "assistant", "content": reply})

history = []

try:
    while True:
        if waiting_mode:
            print("listening for wake word")
            message, _ = listen_sleep(audio_device)
            if message and (message.lower() == WAKE_WORD_FI or WAKE_WORD_FI in message.lower()):
                speak("Hei! Miten voin auttaa?", "fi")
                waiting_mode = False
            elif message and (message.lower() == WAKE_WORD_EN or WAKE_WORD_EN in message.lower()):
                speak("Hello! How can I help you?", "en")
                waiting_mode = False

        if not waiting_mode:
            # conversation mode
            user_message = listen_conversation(audio_device)
            #print("input: ")
            #user_message = input(), "en"
            msg = user_message[0].lower()
            if STOP_WORD_FI in msg or STOP_WORD_EN in msg:
                waiting_mode = True
                continue
            print(f"user_message: {user_message}")
            history.append({"role": "user", "content": user_message[0]})
            
            print("getting sensor data")
            sensor_data = read_sensors(ser)
            moisture = get_moisture(sensor_data)
            print(f"mosture from sensor: {moisture}")

            if moisture is not None:
                plant_profile['moisture_percentage'] = round((1 - moisture / 4095) * 100)
                current_dry = is_dry(moisture)
                update_watering_date(previous_dry, current_dry)
                previous_dry = current_dry
            system_prompt(history=history, language=user_message[1])
finally:
    cleanup(ser) # update cleanup() in sensor.py to accept ser as a parameter
