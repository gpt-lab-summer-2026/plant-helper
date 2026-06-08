import whisper
import sounddevice as sd
import numpy
# listen to user

# load whisper model, only once 
model = whisper.load_model("tiny")
# add audio we get from mic

# listen function
def listen():
    fs = 16000
    # record audio
    duration = 10.5  # seconds
    myrecording = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype="float32")
    sd.wait()
    myrecording=numpy.squeeze(myrecording)

    transcription = model.transcribe(myrecording)
    print(transcription["text"])
    return transcription["text"]