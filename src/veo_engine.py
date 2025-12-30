# Google Veo 3.1 Video Generator Wrapper
# Wraps the Gemini API for video generation.
# Requires 'google-genai' package: pip install google-genai

import os
import sys
import time
import requests

# Try importing the official client, but provide a clear error if missing
try:
    from google import genai
    from google.genai import types
except ImportError:
    print("❌ Error: 'google-genai' library not found.")
    print("Please install it: pip install google-genai")
    # We won't exit here to allow the script to be imported for inspection, 
    # but functions will fail.

# --- CONFIGURATION ---
OUTPUT_DIR = r"../output/veo_generated"
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

# API Key should be in environment variable
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

def generate_video_veo(prompt, duration_seconds=5, aspect_ratio="9:16", output_filename=None):
    """
    Generate a video using Google Veo 3.1 via Gemini API.
    
    Args:
        prompt (str): Description of the video.
        duration_seconds (int): Duration (usually 5-8s for Veo).
        aspect_ratio (str): "16:9", "9:16", "1:1".
        output_filename (str): Optional filename.
        
    Returns:
        str: Path to the saved video file.
    """
    if not GEMINI_API_KEY:
        raise ValueError("❌ GEMINI_API_KEY environment variable not set.")
    
    if "genai" not in globals():
        raise ImportError("google-genai library not installed.")

    print(f"🎥 Veo 3.1 Generating: '{prompt}'")
    print(f"   Settings: {aspect_ratio}, {duration_seconds}s")

    client = genai.Client(api_key=GEMINI_API_KEY)
    
    # Map aspect ratio to API format if needed (currently API might infer or use specific enum)
    # For Veo 3.1, config is passed via GenerateVideosConfig
    
    # NOTE: Exact parameter names for Veo 3.1 might vary slightly in preview.
    # Based on latest docs:
    
    try:
        operation = client.models.generate_videos(
            model="veo-3.1-generate-preview", # Or "veo-2.0-generate-preview" if 3.1 unavailable
            prompt=prompt,
            config=types.GenerateVideosConfig(
                aspect_ratio=aspect_ratio,
                duration_seconds=float(duration_seconds),
                # frame_rate=24, # Optional
            )
        )
        
        print("   ⏳ Request sent. Waiting for generation...")
        
        # Poll for completion (if the client doesn't block automatically, usually it returns an LRO)
        # The 'generate_videos' method in new SDK might return a Job/LRO.
        # If it returns a response with video bytes directly (unlikely for video), we save it.
        # Assuming standard LRO pattern:
        
        if hasattr(operation, 'result'):
             response = operation.result() # Wait for result
        else:
             # If it's not an LRO object, it might be the response directly (synchronous)
             response = operation

        # Extract video content
        # Response structure depends on SDK version. 
        # Usually response.generated_videos[0].video.video_bytes
        
        if hasattr(response, 'generated_videos'):
            video_bytes = response.generated_videos[0].video.video_bytes
        else:
             # Fallback exploration of response object
             print(f"   ❓ Unknown response structure: {type(response)}")
             return None

        # Save to file
        if not output_filename:
            # Create safe filename from prompt
            safe_prompt = "".join([c if c.isalnum() else "_" for c in prompt[:20]])
            timestamp = int(time.time())
            output_filename = f"veo_{safe_prompt}_{timestamp}.mp4"
        
        output_path = os.path.join(OUTPUT_DIR, output_filename)
        
        with open(output_path, "wb") as f:
            f.write(video_bytes)
            
        print(f"✅ Video saved to: {output_path}")
        return output_path

    except Exception as e:
        print(f"❌ Generation failed: {e}")
        return None

if __name__ == "__main__":
    # Test run
    test_prompt = "A cinematic close-up of a futuristic cyberpunk city with neon lights, rain falling, 9:16 vertical video"
    try:
        generate_video_veo(test_prompt, duration_seconds=5, aspect_ratio="9:16")
    except Exception as e:
        print(f"Test skipped/failed: {e}")
