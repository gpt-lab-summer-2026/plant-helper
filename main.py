import ollama
from ollama import chat
import datetime
import serial
import json
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

# init serial connection to ESP32 once at startup
ser = serial.Serial("/dev/ttyUSB0", 9600, timeout=2)  # or /dev/ttyAMA0, check with `ls /dev/tty*` when esp is connected to the pi
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
            message, _ = listen_sleep()
            if message and (message.lower() == WAKE_WORD_FI or WAKE_WORD_FI in message.lower()):
                speak("Hei! Miten voin auttaa?", "fi")
                waiting_mode = False
            elif message and (message.lower() == WAKE_WORD_EN or WAKE_WORD_EN in message.lower()):
                speak("Hello! How can I help you?", "en")
                waiting_mode = False

        if not waiting_mode:
            # conversation mode
            user_message = listen_conversation()
            #print("input: ")
            #user_message = input(), "en"
            if user_message[0].lower() == STOP_WORD_FI or user_message[0].lower() == STOP_WORD_EN or STOP_WORD_FI in user_message[0].lower() or STOP_WORD_EN in user_message[0].lower():
                waiting_mode = True
                continue
            print(f"user_message: {user_message}")
            history.append({"role": "user", "content": user_message[0]})
            sensor_data = read_sensors(ser)
            moisture = get_moisture(sensor_data)
            if moisture is not None:
                plant_profile['moisture_percentage'] = round((1 - moisture / 1023) * 100)
                current_dry = is_dry(moisture)
                update_watering_date(previous_dry, current_dry)
                previous_dry = current_dry
            system_prompt(history=history, language=user_message[1])
finally:
    cleanup(ser) # update cleanup() in sensor.py to accept ser as a parameter

