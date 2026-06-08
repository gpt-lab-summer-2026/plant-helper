import json

# handle plant data and everything related to it

# load profile data from json
# if the name of the plant is known
plant_name = "tatti"

# read json file
try:
    data = json.load('data/plant_profile.json')
    print("File data =", data)
except FileNotFoundError:
    print("Error: file not found")
except json.JSONDecodeError:
    print("Error: Failed to decode JSON from the file.")

# get correct data and add it to variables

# function to store data