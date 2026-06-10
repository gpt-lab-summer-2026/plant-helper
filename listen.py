import whisper
import sounddevice as sd
import numpy
# listen to user

# load whisper model, only once 
model = whisper.load_model("tiny")

# listen function
def listen():
    fs = 16000
    # record audio
    # TO DO: stop recording when no one is speaking, esim. webrtcvad
    duration = 5  # seconds
    print("speak now")
    myrecording = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype="float32")
    sd.wait()
    myrecording=numpy.squeeze(myrecording)

    transcription = model.transcribe(myrecording)
    print(transcription["text"])
    return transcription["text"]

# test print
# print(listen())