from piper.voice import PiperVoice
import wave
import subprocess
import sys
# ai speaks to user 

# TO DO: how to select which language
# openclaw could detect which language
# load voice
voice_fi = PiperVoice.load("voices/fi_FI-harri-low.onnx") 
voice_en = PiperVoice.load("voices/en_GB-southern_english_female-low.onnx") 

def speak(text, language):
    # synthesize the text to wav file 
    if language == 'fi':
        voice = voice_fi
    elif language == 'en':
        voice = voice_en

    with wave.open("output.wav", "wb" ) as wav_file:
        voice.synthesize_wav(text, wav_file)
    # play the audio
    player = "afplay" if sys.platform == "darwin" else "aplay"
    return subprocess.run([player, "output.wav"], check=True)

# speak("how are you, how you doing", 'fi')