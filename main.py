import argparse
import datetime
import glob
import json
import os
import serial
import sys
import threading
import time

from llama_cpp import Llama

from listen import *
from speak import *
from load_data import *
from sensor import *

MAX_HISTORY = 20
STOP_WORD_FI = "lopeta"
WAKE_WORD_FI = "aloita"
STOP_WORD_EN = "stop"
WAKE_WORD_EN = "start"

# (seconds since thinking started, phrase to speak) - escalating filler
# phrases so the plant only comments on the wait once it's actually long.
THINKING_PHRASES = {
    "fi": [
        (10, "Hmm, annas kun mietin..."),
        (20, "Tämä vaatii vielä hetken miettimistä..."),
        (30, "Anteeksi, mietin edelleen vastausta..."),
    ],
    "en": [
        (10, "Hmm, let me think..."),
        (20, "Still thinking about this one..."),
        (30, "Sorry, I'm still working out my answer..."),
    ],
}

waiting_mode = False

SERIAL_BAUDRATE = 921600
DEFAULT_SERIAL_PORTS = ["/dev/ttyUSB0", "/dev/ttyACM0", "/dev/cu.usbserial-0001"]


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
parser.add_argument("--model-backend", choices=["llama_cpp"],
                    default=os.environ.get("PLANT_MODEL_BACKEND", "llama_cpp"),
                    help="Choose the model backend to use.")
parser.add_argument("--llama-model-path",
                    default=os.environ.get("PLANT_LLAMA_MODEL_PATH", "gemma-3-4b-it-Q4_0.gguf"),
                    help="Path to a local llama.cpp model file (gguf).")
args = parser.parse_args()

preferred_port = args.serial_port or os.environ.get("PLANT_SERIAL_PORT")
audio_device = args.audio_device or os.environ.get("PLANT_AUDIO_DEVICE")
model_backend = args.model_backend

llama_model_path = args.llama_model_path
llama_model = None

if model_backend == "llama_cpp":
    if not llama_model_path:
        print("Error: --llama-model-path is required when using llama_cpp backend.")
        sys.exit(1)
    llama_model = Llama(
        model_path=llama_model_path,
        n_threads = 4,
        n_batch=128,
        n_ctx=2048,
    )

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
        plant_database = json.load(file)
except FileNotFoundError:
    print("Error: data/plant_database.json was not found.")
    sys.exit(1)

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


def _llama_chat(messages, model):
    response = model.create_chat_completion(
        messages=messages,
        max_tokens=128,
        temperature=0.7,
    )
    if hasattr(response, "choices") and response.choices:
        return getattr(response.choices[0].message, "content", "") or ""
    if isinstance(response, dict):
        return response.get("choices", [{}])[0].get("message", {}).get("content", "")
    return ""


def _speak_thinking_fillers(language, done_event):
    phrases = THINKING_PHRASES.get(language, THINKING_PHRASES["en"])
    elapsed = 0
    for delay, phrase in phrases:
        if done_event.wait(timeout=delay - elapsed):
            return
        elapsed = delay
        speak(phrase, language)


def system_prompt(history, language):
    trimmed_history = history[-MAX_HISTORY:]
    print("trimmed history length: ", len(trimmed_history))
    few_shot = _few_shot_messages()
    print("thinking...")
    messages = [
        {'role': 'system', 'content': _build_system_prompt(language)},
        *few_shot,
        *trimmed_history
    ]

    result = {}

    def _run_chat():
        result["reply"] = _llama_chat(messages, llama_model)

    done_event = threading.Event()
    chat_thread = threading.Thread(target=_run_chat)
    filler_thread = threading.Thread(target=_speak_thinking_fillers, args=(language, done_event))
    chat_thread.start()
    filler_thread.start()

    chat_thread.join()
    done_event.set()
    filler_thread.join()

    reply = result.get("reply", "").strip()

    print(reply)
    speak(reply, language)
    history.append({"role": "assistant", "content": reply})

history = []

try:
    while True:
        if waiting_mode:
            print("listening for wake word")
            print("getting sensor data")
            sensor_data = read_sensors(ser)
            moisture = get_moisture(sensor_data)
            print(f"moisture from sensor: {moisture}")
            if moisture >= 3000:
                print(speak("I need water!!", "en"))
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
            if not user_message or not user_message[0]:
                continue
            msg = user_message[0].lower()
            if user_message[0].lower() == STOP_WORD_FI or user_message[0].lower() == STOP_WORD_EN or STOP_WORD_FI in user_message[0].lower() or STOP_WORD_EN in user_message[0].lower():
                waiting_mode = True
                continue
            print(f"user_message: {user_message}")
            history.append({"role": "user", "content": user_message[0]})
            
            print("getting sensor data")
            sensor_data = read_sensors(ser)
            moisture = get_moisture(sensor_data)
            print(f"moisture from sensor: {moisture}")
            if moisture is not None:
                moisture_percentage = str(round((1 - moisture / 4095) * 100))+"%"
                
                current_dry = is_dry(moisture)
                update_watering_date(previous_dry, current_dry)
                previous_dry = current_dry
                
                plant_profile['moisture_percentage'] = update_moisture(moisture_percentage=moisture_percentage)

            system_prompt(history=history, language=user_message[1])
except KeyboardInterrupt:
    pass
except Exception:
    import traceback
    traceback.print_exc()
finally:
    cleanup(ser)
    os._exit(0)  # force-kill llama_cpp native threads that ignore normal exit
