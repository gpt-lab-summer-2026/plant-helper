# Plant Helper
Have you ever wanted to have a chat with your house plant? Plant Helper is small machine that you can plug into a plant pot. It can help you take care of the plant using AI.

## Features
Communicate with your plant by simply talking to it! After setting up a [plant profile](data/plant_profile.json), you can ask the plant about things related to it, such as:

> Hello, what is your name?

> How are you?

> Would you like some more water? When should I water you?

The plant can also discuss other plant species, topics related to gardening and other nature-related topics. The plant does is not made for discussing unrelated topics.

## Hardware
Plant Helper is built with a Raspberry Pi, a humidity sensor, a microphone and a speaker. It is small enough to fit into a regular plant pot.

## Software
Plant Helper listens to the user with Whisper, thinks of a response through Ollama gemma3:4b, and speaks to user with Piper. We have implemented RAG by using a [plant-database](data/plant_database.json) that was created with Claude. 

## Supported Languages
Plant Helper currently supports English and Finnish, featuring a unique voice for each language.
