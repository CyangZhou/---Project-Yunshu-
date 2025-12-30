import os
import requests

# BGM Source: Free Music Archive (FMA) / Pixabay (Simulated for this demo)
# For the purpose of this demo, we will download specific tracks from FMA that match the vibe.
# NOTE: In a real "Viral" scenario, users might manually drop in famous tracks like "Monkeys Spinning Monkeys"
# Here we provide high-quality "look-alikes".

# Dictionary of high-quality tracks (Direct MP3 links)
# Replacing previous single track with a curated list
VIRAL_TRACKS = {
    "suspense": [
        {
            "name": "suspense_drone.mp3",
            "url": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-15.mp3"
        }
    ],
    "emotional": [
        {
            "name": "sad_piano.mp3",
            "url": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-16.mp3" # Placeholder for Emotional
        }
    ],
    "epic": [
        {
            "name": "epic_action.mp3",
            "url": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3" # Placeholder for Epic
        }
    ]
}

def download_file(url, filepath):
    if os.path.exists(filepath):
        print(f"✅ Exists: {filepath}")
        return
        
    print(f"⬇️ Downloading: {filepath}...")
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print("✅ Download Complete.")
    except Exception as e:
        print(f"❌ Download Failed: {e}")

def setup_bgm_library():
    base_dir = "../resources/bgm"
    
    for category, tracks in VIRAL_TRACKS.items():
        cat_dir = os.path.join(base_dir, category)
        os.makedirs(cat_dir, exist_ok=True)
        
        for track in tracks:
            filepath = os.path.join(cat_dir, track['name'])
            download_file(track['url'], filepath)

if __name__ == "__main__":
    setup_bgm_library()
