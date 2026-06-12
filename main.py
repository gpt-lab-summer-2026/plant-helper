import ollama
from ollama import chat
import datetime
import json

from listen import *
from speak import *
from plant_profile import *
#from sensor import *

# main function

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

# function to build system prompt using profile + sensor data
def system_prompt(history, language):
    print("history length: ", len(history))
    response = chat(
        model='gemma3:4b',
        messages=[
                {'role': 'system', 'content': f"You are a {plant_profile['species']} houseplant named {plant_profile['plant_name']}. Your soil moisture is currently {plant_profile['moisture_percentage']} and if it's high, you don't need water. You were last watered {datetime.datetime.fromisoformat(plant_profile['last_watered'])}."
                    f"Find correct plant species from {plant_database} and learn about that plant. Answer questions from the user as the plant in a friendly tone and keep answers simple and in 3 sentences. Only greet if the user greets you. Answer in finnish or english based on user's language. "
                },
                *history
                ]           
    )
    print(response.message.content)
    speak(response.message.content, language)

    history.append({"role": "assistant", "content": response.message.content})

history = []

while True:
    #print("send message: ")
    #user_message = input()
    user_message = listen()
    # TO DO: functionality to stop program
    print(f"user_message: {user_message}")
    history.append({"role": "user", "content": str(user_message)})
    system_prompt(history=history, language=user_message[1])
