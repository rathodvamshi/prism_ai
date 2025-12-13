import edge_tts
import uuid
import os

# Create a folder for audio files if it doesn't exist
AUDIO_DIR = "static/audio"
os.makedirs(AUDIO_DIR, exist_ok=True)

async def text_to_speech(text: str) -> str:
    """
    Converts text to an MP3 file and returns the file path.
    """
    filename = f"{uuid.uuid4()}.mp3"
    file_path = os.path.join(AUDIO_DIR, filename)
    
    # "en-US-AriaNeural" is a very friendly, high-quality female voice
    communicate = edge_tts.Communicate(text, "en-US-AriaNeural")
    
    await communicate.save(file_path)
    
    return file_path