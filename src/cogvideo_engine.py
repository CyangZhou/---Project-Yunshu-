# Zhipu AI (CogVideoX) Video Generator Wrapper
# Wraps the Zhipu AI API for video generation.
# Requires 'zhipuai' package: pip install zhipuai

import os
import time
import requests

# Try importing the official client
try:
    from zhipuai import ZhipuAI
except ImportError:
    print("❌ Error: 'zhipuai' library not found.")
    print("Please install it: pip install zhipuai")

# --- CONFIGURATION ---
OUTPUT_DIR = r"../output/cogvideo_generated"
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

# API Key should be in environment variable
ZHIPU_API_KEY = os.environ.get("ZHIPU_API_KEY")

def generate_video_cogvideo(prompt, duration_seconds=6, aspect_ratio="9:16", output_filename=None):
    """
    Generate a video using Zhipu AI CogVideoX.
    
    Args:
        prompt (str): Description of the video.
        duration_seconds (int): Not always adjustable for CogVideo, usually fixed (e.g. 6s).
        aspect_ratio (str): "16:9", "9:16", "1:1" (CogVideoX usually supports these).
        output_filename (str): Optional filename.
        
    Returns:
        str: Path to the saved video file.
    """
    if not ZHIPU_API_KEY:
        raise ValueError("❌ ZHIPU_API_KEY environment variable not set.")
    
    if "ZhipuAI" not in globals():
        raise ImportError("zhipuai library not installed.")

    print(f"🎥 CogVideoX Generating: '{prompt}'")
    
    client = ZhipuAI(api_key=ZHIPU_API_KEY)
    
    try:
        # 1. Submit Generation Task
        # Note: CogVideoX parameters might vary. 
        # Usually: model="cogvideox", prompt=prompt
        response = client.videos.generations(
            model="cogvideox",
            prompt=prompt,
            # quality="quality", # Optional
            # with_audio=False, # Optional
            # size="720x1280" if aspect_ratio == "9:16" else "1280x720" # Example mapping
        )
        
        # Zhipu API usually returns a task ID immediately
        # Response object structure: response.id (task_id)
        
        task_id = response.id
        print(f"   ⏳ Task submitted. ID: {task_id}")
        print("   ⏳ Waiting for generation (this may take 1-3 minutes)...")
        
        # 2. Poll for Status
        status = "PROCESSING"
        video_url = None
        
        while status == "PROCESSING" or status == "PENDING":
            time.sleep(5) # Poll every 5 seconds
            
            # Check task status
            # client.videos.retrieve_videos_result(id=task_id)
            result_response = client.videos.retrieve_videos_result(id=task_id)
            
            task_status = result_response.task_status
            
            if task_status == "SUCCESS":
                status = "SUCCESS"
                # result_response.video_result is usually a list or object containing url
                # It might be result_response.video_result[0].url
                video_url = result_response.video_result[0].url
                print("   ✅ Generation complete!")
            elif task_status == "FAIL":
                print("   ❌ Generation failed.")
                print(f"   Reason: {result_response}")
                return None
            else:
                print(".", end="", flush=True)
                
        # 3. Download Video
        if video_url:
            print(f"\n   ⬇️ Downloading video from: {video_url[:50]}...")
            
            if not output_filename:
                safe_prompt = "".join([c if c.isalnum() else "_" for c in prompt[:20]])
                timestamp = int(time.time())
                output_filename = f"cogvideo_{safe_prompt}_{timestamp}.mp4"
            
            output_path = os.path.join(OUTPUT_DIR, output_filename)
            
            video_data = requests.get(video_url).content
            with open(output_path, "wb") as f:
                f.write(video_data)
                
            return output_path
            
    except Exception as e:
        print(f"\n❌ Error calling Zhipu API: {e}")
        return None

