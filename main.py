import ollama
from ollama import chat
import datetime

from listen import *
from speak import *
from plant_profile import *
#from sensor import *

# main function

# load plant profile
plant_profile = read()

# function to build system prompt using profile + sensor data
def system_prompt(user_input, history):
    print("history length: ", len(history))
    if len(history) < 2:
        response = chat(
            model='phi3:mini',
            messages=[{'role': 'system', 'content': f"You are a {plant_profile['species']} houseplant named {plant_profile['plant_name']}. Your soil moisture is currently {plant_profile['moisture_percentage']}. You were last watered {datetime.datetime.fromisoformat(plant_profile['last_watered'])}."},
                    {'role': 'system', 'content': f"Open plant_database.json file and learn from it. Reply to {user_input} as the plant in a friendly tone and keep answers in 3 sentences."}
                    ]           
        )
        print(response.message.content)
        speak(response.message.content)
    else:
        response = chat(
            model='phi3:mini',
            messages=[
                    {'role': 'system', 'content': f"{history} is conversation history that you should use. Reply to {user_input}. Answer questions as the plant in a friendly tone and keep answers in 3 sentences. Do not greet."}
                    ]           
        )
        print(response.message.content)
        speak(response.message.content)

    history.append({"role": "assistant", "content": response.message.content})

history = []

while True:
    user_message = listen()
    # TO DO: functionality to stop program
    history.append({"role": "user", "content": user_message})
    system_prompt(user_message, history)
