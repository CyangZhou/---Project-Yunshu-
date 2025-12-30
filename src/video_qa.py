import cv2
import numpy as np
import sys
import os
try:
    # MoviePy v2.0+
    from moviepy import VideoFileClip
    MOVIEPY_V2 = True
except ImportError:
    # MoviePy v1.x
    from moviepy.editor import VideoFileClip
    MOVIEPY_V2 = False

def analyze_video_quality(video_path):
    """
    Analyzes video for technical quality and 'viral potential' (pacing/motion).
    """
    print(f"🕵️ Analyzing Quality for: {os.path.basename(video_path)}")
    
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print("❌ Error: Could not open video.")
        return

    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = frame_count / fps
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    print(f"📊 Metadata: {width}x{height} | {fps:.2f}fps | {duration:.2f}s")

    # Metrics
    blur_scores = []
    brightness_scores = []
    motion_scores = []
    prev_frame = None
    
    # Sampling: Analyze 1 frame every 0.5 seconds to save time
    sample_rate = int(fps * 0.5) 
    
    frame_idx = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        if frame_idx % sample_rate == 0:
            # 1. Blur Detection (Laplacian Variance)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            blur_val = cv2.Laplacian(gray, cv2.CV_64F).var()
            blur_scores.append(blur_val)
            
            # 2. Brightness
            brightness_val = np.mean(gray)
            brightness_scores.append(brightness_val)
            
            # 3. Motion (Frame Difference)
            if prev_frame is not None:
                diff = cv2.absdiff(gray, prev_frame)
                motion_val = np.mean(diff)
                motion_scores.append(motion_val)
            
            prev_frame = gray

        frame_idx += 1

    cap.release()
    
    # --- Analysis Report ---
    
    # Technical Thresholds
    avg_blur = np.mean(blur_scores) if blur_scores else 0
    avg_bright = np.mean(brightness_scores) if brightness_scores else 0
    
    # Heuristics
    is_blurry = avg_blur < 100  # Threshold varies, <100 often means blurry
    is_dark = avg_bright < 40   # <40 is quite dark
    
    print("\n--- 🛠️ Technical Quality ---")
    print(f"Blur Score: {avg_blur:.2f} ({'⚠️ Blurry' if is_blurry else '✅ Sharp'})")
    print(f"Brightness: {avg_bright:.2f} ({'⚠️ Dark' if is_dark else '✅ OK'})")
    
    # Viral Potential (Pacing & Hook)
    print("\n--- 🚀 Viral Potential ---")
    
    # 1. Gold 3 Seconds Check
    # First 3 seconds = first 6 samples (since we sample every 0.5s)
    hook_samples = motion_scores[:6]
    avg_hook_motion = np.mean(hook_samples) if hook_samples else 0
    avg_overall_motion = np.mean(motion_scores) if motion_scores else 0
    
    print(f"Hook Motion (First 3s): {avg_hook_motion:.2f}")
    print(f"Overall Motion: {avg_overall_motion:.2f}")
    
    if avg_hook_motion > 5.0: # Arbitrary threshold, needs tuning
        print("✅ Hook: Strong visual motion detected in first 3s!")
    elif avg_hook_motion > 2.0:
         print("⚠️ Hook: Moderate motion. Could be punchier.")
    else:
        print("❌ Hook: Static start. Risk of scroll-away!")
        
    # 2. Pacing (Shot detection simulation via motion spikes)
    # Simple peak detection in motion scores
    motion_arr = np.array(motion_scores)
    # A "cut" usually causes a massive spike in frame difference
    # We look for spikes > 3 * standard_deviation
    threshold = np.mean(motion_arr) + 3 * np.std(motion_arr)
    cuts = np.sum(motion_arr > threshold)
    
    est_shot_duration = duration / (cuts + 1)
    print(f"Est. Shot Duration: ~{est_shot_duration:.1f}s")
    
    if est_shot_duration < 4.0:
        print("✅ Pacing: Fast (Good for TikTok/Shorts)")
    else:
        print("⚠️ Pacing: Slow. Consider more cuts.")

    # 3. Audio Check (Volume)
    try:
        clip = VideoFileClip(video_path)
        # Check first 3s audio volume
        if MOVIEPY_V2:
            audio_sub = clip.subclipped(0, min(3, duration))
        else:
            audio_sub = clip.subclip(0, min(3, duration))
            
        max_vol = audio_sub.audio.max_volume()
        print(f"Hook Audio Vol: {max_vol:.2f}")
        if max_vol < 0.2:
            print("❌ Hook Audio: Too quiet! Add SFX or louder speech.")
        else:
            print("✅ Hook Audio: Good volume.")
        clip.close()
    except Exception as e:
        print(f"⚠️ Audio check failed: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        analyze_video_quality(sys.argv[1])
    else:
        print("Usage: python video_qa.py <video_path>")
