import ollama
from ollama import chat
import datetime
import json
from llama_cpp import Llama

#from listen import *
from listen import *
from speak import *
from plant_profile import *
#from sensor import *

MAX_HISTORY = 20
STOP_WORD_FI = "lopeta keskustelu"
WAKE_WORD_FI = "aloita keskustelu"
STOP_WORD_EN = "stop conversation"
WAKE_WORD_EN = "start conversation"

waiting_mode = False

# load plant profile
plant_profile = read()

# read plant database data
try:
    with open('data/plant_database.json', 'r') as file:
        data = json.load(file)
    #print("File data =", data)
    plant_database = data
    
except FileNotFoundError:
    print("Error: The file 'data.json' was not found.")

# load model
llm = Llama(model_path="finetuned-models/gemma3-second/gemma-3-4b-it.Q8_0.gguf", n_ctx=4096)

# look up just the matching species entry from the database
# database in finnish as well??
species = plant_profile['species'].lower()
plant_info = next(
    (p for p in plant_database if species in p['common_name'].lower() or species in p['scientific_name'].lower()),
    None
) 

def system_prompt(history, language):
    print("history length: ", len(history))
    trimmed_history = history[-MAX_HISTORY:]
    care_info = f"Care info: {plant_info}" if plant_info else ""
    lang_name = 'Finnish' if language == 'fi' else 'English'

    response = llm.create_chat_completion(
        messages=[
                {'role': 'system', 'content': 
                    f"IMPORTANT: You MUST respond in {lang_name} only. Do not use any other language.\n"
                    f"You are a {plant_profile['species']} houseplant named {plant_profile['plant_name']}. Your soil moisture is currently {plant_profile['moisture_percentage']} and if it's high, you don't need water. You were last watered {datetime.datetime.fromisoformat(plant_profile['last_watered'])}. {care_info}"
                    f" Answer questions from the user as the plant in a friendly tone and keep answers simple and in 3 sentences. Only greet if the user greets you."
                },
                #*history,
                *trimmed_history
                ]
    )
    reply = response["choices"][0]["message"]["content"]
    reply = reply.removeprefix("assistant:").strip().rstrip("\\")
    print(reply)
    speak(reply, language)
    history.append({"role": "assistant", "content": reply})

history = []

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
        if user_message[0].lower() == STOP_WORD_FI or user_message[0].lower() == STOP_WORD_EN or STOP_WORD_FI in user_message[0].lower() or STOP_WORD_EN in user_message[0].lower():
            waiting_mode = True
            continue
        print(f"user_message: {user_message}")
        history.append({"role": "user", "content": user_message[0]})
        system_prompt(history=history, language=user_message[1])

