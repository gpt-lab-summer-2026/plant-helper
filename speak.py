from piper.voice import PiperVoice
import wave
import subprocess
import sys
# ai speaks to user 

# TO DO: how to select which language
# load voice
voice = PiperVoice.load("voices/en_GB-southern_english_female-low.onnx") # we need .onnx and .json files downloaded, for this only .onnx

def speak(text):
    # sunthesize the text to wav file 
    with wave.open("output.wav", "wb" ) as wav_file:
        voice.synthesize_wav(text, wav_file)
    # play the audio
    player = "afplay" if sys.platform == "darwin" else "aplay"
    return subprocess.run([player, "output.wav"], check=True)
