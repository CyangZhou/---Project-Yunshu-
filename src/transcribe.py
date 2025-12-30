import whisper
import os

# Set local ffmpeg path if needed, though whisper usually expects it in PATH.
# If this fails, we might need to add current dir to PATH temporarily.
os.environ["PATH"] += os.pathsep + os.getcwd()

def transcribe_audio(audio_path):
    print(f"Loading Whisper model... (this may take a while)")
    model = whisper.load_model("base")
    print(f"Transcribing {audio_path}...")
    result = model.transcribe(audio_path, language="zh")
    return result["text"]

if __name__ == "__main__":
    audio_file = "temp_audio.mp3"
    if not os.path.exists(audio_file):
        print(f"Error: {audio_file} not found.")
    else:
        text = transcribe_audio(audio_file)
        print("\nTranscription Result:")
        print(text)
        
        with open("transcript.txt", "w", encoding="utf-8") as f:
            f.write(text)
