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
llm = Llama(model_path="finetuned-model/gemma-3-4b-it.Q4_K_M.gguf", n_ctx=4096)

# look up just the matching species entry from the database
species = plant_profile['species'].lower()
plant_info = next(
    (p for p in plant_database if species in p['common_name'].lower() or species in p['scientific_name'].lower()),
    None
)

MAX_HISTORY = 20  # 10 turns

def system_prompt(history, language):
    print("history length: ", len(history))
    trimmed = history[-MAX_HISTORY:]
    care_info = f"Care info: {plant_info}" if plant_info else ""
    response = llm.create_chat_completion(
        messages=[
                {'role': 'system', 'content': f"You are a {plant_profile['species']} houseplant named {plant_profile['plant_name']}. Your soil moisture is currently {plant_profile['moisture_percentage']} and if it's high, you don't need water. You were last watered {datetime.datetime.fromisoformat(plant_profile['last_watered'])}. {care_info}"
                    f" Answer questions from the user as the plant in a friendly tone and keep answers simple and in 3 sentences. Only greet if the user greets you. You MUST answer in {'Finnish' if language == 'fi' else 'English'} only."
                },
                #*history,
                *trimmed
                ]
    )
    reply = response["choices"][0]["message"]["content"]
    reply = reply.removeprefix("assistant:").strip().rstrip("\\")
    print(reply)
    speak(reply, language)
    history.append({"role": "assistant", "content": reply})

history = []

while True:
    #print("send message: ")
    #user_message = input()
    user_message = listen()

    print(f"user_message: {user_message}")
    history.append({"role": "user", "content": user_message[0]})
    system_prompt(history=history, language=user_message[1])
