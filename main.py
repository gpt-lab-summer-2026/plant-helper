import ollama
from ollama import chat
import datetime

#from listen import *
from speak import *
from plant_profile import *
#from sensor import *

# main function


# load plant profile
plant_profile = read()

# function to build system prompt using profile + sensor data
def system_prompt():
    response = chat(
        model='phi3:mini',
        messages=[{'role': 'system', 'content': f"You are a {plant_profile['species']} plant named {plant_profile['plant_name']}."},
                  {'role': 'system', 'content': f"Your soil moisture is currently {plant_profile['moisture_percentage']}. You were last watered {datetime.datetime.fromisoformat(plant_profile['last_watered'])} which was {datetime.datetime.now()-datetime.datetime.fromisoformat(plant_profile['last_watered'])} days ago."},
                  {'role': 'system', 'content': f"Answer questions as the plant in a friendly tone and keep answers in 5 sentences."}
                ]           
    )
    print(response.message.content)
    speak(response.message.content)

system_prompt()