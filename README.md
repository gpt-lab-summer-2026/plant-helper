# Plant Helper

Have you ever wanted to have a chat with your house plant? Plant Helper is small machine that you can plug into a plant pot; it can help you take care of your plant. You can chat with plant helper and it gives you info about the plant and suggestions how to take care of the plant.

## Features

Communicate with your plant by simply talking to it! After setting up a [plant profile](data/plant_profile.json), you can ask the plant about things related to it, such as:

> Hello, what is your name?

> How are you?

> Would you like some more water? When should I water you?

The plant can also discuss other plant species, topics related to gardening and other nature-related topics. The plant does is not made for discussing unrelated topics.

## Hardware

Plant Helper is built with a Raspberry Pi, ESP, a moisture sensor, a microphone, a speaker and a led. It is small enough to fit into a regular plant pot. Moisture sensor and led are connected to ESP-32-C6 (any other ESP works as well, then code just needs to be updated) and the ESP is connected to the Raspberry Pi via usb-c cable. Microphone is connected via usb to Raspberry Pi and the speaker is connected via Bluetooth. 

## Software

Plant Helper listens to the user with Whisper, thinks of a response through Ollama gemma3:4b, and speaks to user with Piper. We have implemented RAG by using a [plant-database](data/plant_database.json) that was created with help of Claude.

## Supported Languages

Plant Helper currently supports English and Finnish, featuring a unique voice for each language.

## Running program

Before running install correct libraries from requirements.txt, language model(gemma-3-4b) from here and and after that program can be run via main.py. 

When installed, run: 

  ```pip install -r requirements.txt``` 

to install correct depencies. Install language model gemma-3-4b-q4 .gguf-file (other models work as well if they aren't too big for the raspberry pi). Run the program via

  ```python main.py.```
