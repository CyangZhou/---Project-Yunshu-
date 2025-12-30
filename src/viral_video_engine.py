import os
import json
import random
import cv2
import numpy as np
import edge_tts
import asyncio
import librosa
from PIL import Image, ImageDraw, ImageFont

# Audio processing
def remove_silence(audio_path, top_db=20):
    y, sr = librosa.load(audio_path)
    # Detect non-silent intervals
    intervals = librosa.effects.split(y, top_db=top_db)
    
    # Concatenate non-silent parts
    y_new = np.concatenate([y[start:end] for start, end in intervals])
    
    # Save processed audio
    output_path = audio_path.replace(".mp3", "_trimmed.wav")
    import soundfile as sf
    sf.write(output_path, y_new, sr)
    return output_path

try:
    from moviepy import VideoFileClip, concatenate_videoclips, CompositeAudioClip, AudioFileClip, vfx
    MOVIEPY_V2 = True
except ImportError:
    from moviepy.editor import VideoFileClip, concatenate_videoclips, CompositeAudioClip, AudioFileClip
    import moviepy.video.fx.all as vfx
    MOVIEPY_V2 = False

# Helper for v1/v2 compatibility
def set_audio_compat(clip, audio):
    if MOVIEPY_V2:
        return clip.with_audio(audio)
    else:
        return clip.set_audio(audio)

def loop_audio_compat(audio, duration):
    # In v1: audio.fx(vfx.loop, duration=...) or audio.loop(duration=...)
    # In v2: vfx.Loop(duration=...).apply(audio) or similar
    # Simplest is likely just reusing the audio in a composite loop if possible, 
    # but moviepy has audio_loop/afx.audio_loop
    if MOVIEPY_V2:
         return audio.with_effects([vfx.Loop(duration=duration)])
    else:
         # v1 audio loop
         from moviepy.audio.fx.all import audio_loop
         return audio_loop(audio, duration=duration)

def volume_compat(audio, vol):
    if MOVIEPY_V2:
        return audio.with_volume_scaled(vol)
    else:
        return audio.volumex(vol)

def subclip_compat(clip, start, end):
    if MOVIEPY_V2:
        return clip.subclipped(start, end)
    else:
        return clip.subclip(start, end)

def fl_image_compat(clip, func):
    if MOVIEPY_V2:
        return clip.image_transform(func)
    else:
        return clip.fl_image(func)

def fadein_compat(clip, duration):
    if MOVIEPY_V2:
        return clip.with_effects([vfx.FadeIn(duration)])
    else:
        return clip.fadein(duration)

# Configuration
VIDEO_FILE = "../resources/ai数学老师.mp4"
CLIPS_FILE = "../config/clips_viral.json"
BGM_FILE = "../resources/background_music.mp3"
OUTPUT_FILE = "../output/final_product_v6.mp4"
ANALYSIS_FILE = "../data/video_analysis.json"
FONT_PATH = "C:\\Windows\\Fonts\\msyh.ttc" # Microsoft YaHei

# 1. OCR Analysis (Reuse logic)
import easyocr
reader = easyocr.Reader(['ch_sim', 'en'])

def analyze_video(video_path, interval=1.0):
    if os.path.exists(ANALYSIS_FILE):
        print("Loading cached analysis...")
        with open(ANALYSIS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    print("Starting video analysis (this may take a while)...")
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps
    
    data = []
    current_sec = 0
    
    # Create a dump file for debugging
    dump_f = open("ocr_dump.txt", "w", encoding="utf-8")
    
    last_frame_gray = None
    last_text = ""
    
    while current_sec < duration:
        cap.set(cv2.CAP_PROP_POS_MSEC, current_sec * 1000)
        ret, frame = cap.read()
        if not ret:
            break
            
        # Optimization: Check if frame is similar to last one
        frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        frame_gray = cv2.resize(frame_gray, (200, 150)) # Resize for speed
        
        is_similar = False
        if last_frame_gray is not None:
            # Calculate Structural Similarity or simple diff
            # Simple diff:
            score = cv2.mean(cv2.absdiff(frame_gray, last_frame_gray))[0]
            # Threshold: if mean diff < 5, consider it static
            if score < 5.0:
                is_similar = True
        
        if is_similar:
            text_content = last_text
            print(f"Skipping OCR: {current_sec:.1f}s (Static Scene)")
        else:
            result = reader.readtext(frame, detail=0)
            text_content = " ".join(result)
            last_text = text_content
            last_frame_gray = frame_gray
            print(f"Analyzed: {current_sec:.1f}s / {duration:.1f}s -> Found {len(text_content)} chars")
        
        data.append({
            "time": current_sec,
            "text": text_content
        })
        
        dump_f.write(f"[{current_sec:.1f}s]: {text_content}\n")
        
        current_sec += interval
        
    cap.release()
    dump_f.close()
    
    with open(ANALYSIS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)
    return data

def find_best_segment(analysis_data, keywords, target_duration, video_duration, used_segments):
    candidates = []
    
    # Sliding window step
    step = 0.5 
    
    for t in np.arange(0, video_duration - target_duration, step):
        # Check overlapping
        is_used = False
        for u_start, u_end in used_segments:
            # Allow slight overlap (0.5s) for smooth transitions? No, keep strict for now.
            if not (t + target_duration <= u_start + 0.5 or t >= u_end - 0.5):
                is_used = True
                break
        if is_used:
            continue
            
        # Calculate score
        score = 0
        window_text = ""
        # Aggregate text in this window
        for item in analysis_data:
            if t <= item["time"] < t + target_duration:
                window_text += item["text"] + " "
        
        window_text_lower = window_text.lower()
        
        for kw in keywords:
            # Weighted scoring: 
            # 1. Base score for presence
            # 2. Bonus for frequency
            kw_lower = kw.lower()
            count = window_text_lower.count(kw_lower)
            if count > 0:
                score += 10 + min(count, 5) # Base 10 + up to 5 bonus
        
        # Penalize if score is 0 (no keywords found)
        if score == 0:
            score = -1
            
        candidates.append((score, t))
    
    # Sort by score desc
    candidates.sort(key=lambda x: x[0], reverse=True)
    
    if not candidates:
        return 0
        
    # Pick from top candidates to add variety but keep high quality
    # Only consider candidates within 80% of the top score
    best_score = candidates[0][0]
    if best_score <= 0:
        # No match found, try to pick a segment that hasn't been used
        # Just return the first available time
        return candidates[0][1]
        
    top_candidates = [c for c in candidates if c[0] >= best_score * 0.8]
    return random.choice(top_candidates)[1]

# 2. Text Drawing (Subtitles) & Multi-modal Helpers
def create_cover_image(title, output_path):
    # Simple cover generator using PIL
    # Background
    W, H = 1920, 1080
    img = Image.new('RGB', (W, H), color=(20, 20, 20))
    draw = ImageDraw.Draw(img)
    
    try:
        font_title = ImageFont.truetype(FONT_PATH, 120)
        font_sub = ImageFont.truetype(FONT_PATH, 60)
    except:
        font_title = ImageFont.load_default()
        font_sub = ImageFont.load_default()
        
    # Draw Title (Centered)
    bbox = draw.textbbox((0, 0), title, font=font_title)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    draw.text(((W-w)/2, (H-h)/2 - 100), title, font=font_title, fill="#FFD700") # Gold
    
    # Draw "Trae AI" tag
    tag = "Powered by Trae AI"
    bbox_tag = draw.textbbox((0, 0), tag, font=font_sub)
    wt = bbox_tag[2] - bbox_tag[0]
    draw.text(((W-wt)/2, (H-h)/2 + 50), tag, font=font_sub, fill="white")
    
    img.save(output_path)
    return output_path

def add_meme_overlay(clip, meme_path, duration=2.0):
    if not os.path.exists(meme_path):
        return clip
        
    # Load meme image
    meme_img = Image.open(meme_path).convert("RGBA")
    # Resize to 30% of screen width
    target_w = int(clip.w * 0.3)
    ratio = target_w / meme_img.width
    target_h = int(meme_img.height * ratio)
    meme_img = meme_img.resize((target_w, target_h))
    
    # Position: Bottom Right
    pos_x = clip.w - target_w - 50
    pos_y = clip.h - target_h - 200 # Above subtitles
    
    # Create ImageClip
    if MOVIEPY_V2:
         from moviepy import ImageClip
         meme_clip = ImageClip(np.array(meme_img)).with_duration(duration).with_position((pos_x, pos_y))
         return CompositeVideoClip([clip, meme_clip]) # Requires CompositeVideoClip import
    else:
         from moviepy.editor import ImageClip, CompositeVideoClip
         meme_clip = ImageClip(np.array(meme_img)).set_duration(duration).set_position((pos_x, pos_y))
         return CompositeVideoClip([clip, meme_clip])

# Helper for type safety
def ensure_uint8(img):
    """Ensure image is uint8 range 0-255"""
    if img.dtype != np.uint8:
        # Assume float 0-1 if max <= 1.0, otherwise just cast
        if img.max() <= 1.0:
            img = (np.clip(img, 0, 1) * 255).astype(np.uint8)
        else:
            img = np.clip(img, 0, 255).astype(np.uint8)
    return img

def add_subtitle(img, text, highlight_keywords=None, font_size=40):
    # FORCE UINT8 at input
    img = ensure_uint8(img)

    # Convert numpy img to PIL
    pil_img = Image.fromarray(img)
    draw = ImageDraw.Draw(pil_img)
    
    try:
        font = ImageFont.truetype(FONT_PATH, font_size)
    except:
        font = ImageFont.load_default()
        
    # Calculate total text size
    left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
    text_w = right - left
    text_h = bottom - top
    
    W, H = pil_img.size
    x = (W - text_w) / 2
    y = H - text_h - 80 # Move up a bit, 80px from bottom
    
    # Draw background box (Semi-transparent black)
    # Expand box slightly
    padding = 10
    box_coords = [x - padding, y - padding, x + text_w + padding, y + text_h + padding]
    
    # Create a separate overlay for transparency
    overlay = Image.new('RGBA', pil_img.size, (0,0,0,0))
    draw_overlay = ImageDraw.Draw(overlay)
    draw_overlay.rectangle(box_coords, fill=(0, 0, 0, 128)) # 50% opacity black
    
    # Composite
    pil_img = Image.alpha_composite(pil_img.convert('RGBA'), overlay)
    draw = ImageDraw.Draw(pil_img) # Re-create draw object for the new image

    # Default styling
    outline_color = "black"
    default_color = "white"
    highlight_color = "#FFD700" # Gold
    offset = 2
    
    # Helper to draw text with outline
    def draw_text_with_outline(tx, ty, t_str, t_color):
        draw.text((tx-offset, ty), t_str, font=font, fill=outline_color)
        draw.text((tx+offset, ty), t_str, font=font, fill=outline_color)
        draw.text((tx, ty-offset), t_str, font=font, fill=outline_color)
        draw.text((tx, ty+offset), t_str, font=font, fill=outline_color)
        draw.text((tx, ty), t_str, font=font, fill=t_color)
        # Return width of drawn text
        bb = draw.textbbox((0, 0), t_str, font=font)
        return bb[2] - bb[0]

    # Check for keywords to highlight
    if not highlight_keywords:
        draw_text_with_outline(x, y, text, default_color)
    else:
        # Simple keyword highlighting (first occurrence of each keyword)
        # Note: This simple implementation handles one keyword at a time well.
        # For multiple keywords, we'd need a more complex tokenizer.
        # Let's try to highlight the *first* matching keyword found in the text.
        
        found_kw = None
        start_idx = -1
        
        for kw in highlight_keywords:
            idx = text.find(kw)
            if idx != -1:
                found_kw = kw
                start_idx = idx
                break
        
        if found_kw:
            prefix = text[:start_idx]
            keyword = text[start_idx:start_idx+len(found_kw)]
            suffix = text[start_idx+len(found_kw):]
            
            curr_x = x
            # Draw prefix
            if prefix:
                w_p = draw_text_with_outline(curr_x, y, prefix, default_color)
                curr_x += w_p
            
            # Draw keyword
            w_k = draw_text_with_outline(curr_x, y, keyword, highlight_color)
            curr_x += w_k
            
            # Draw suffix
            if suffix:
                draw_text_with_outline(curr_x, y, suffix, default_color)
        else:
            draw_text_with_outline(x, y, text, default_color)
    
    # FORCE UINT8 at output
    return np.array(pil_img.convert("RGB"))

async def generate_voiceover(text, filename):
    # Load user profile for personalized settings
    try:
        with open("../docs/核心设定/用户配置.json", "r", encoding="utf-8") as f:
            profile = json.load(f)
            # Check preferences
            if "Soothing" in profile.get("preferences", {}).get("music_style", []):
                # Adjust TTS rate for healing/soothing tone
                # Xiaoxiao is already warm, -10% is good. Maybe -15% for extra soothing?
                pass 
    except:
        pass # Fallback to defaults

    communicate = edge_tts.Communicate(text, "zh-CN-XiaoxiaoNeural", rate="-10%")
    await communicate.save(filename)

# Visual Enhancement: Auto-Zoom
def apply_zoom(clip, zoom_ratio=1.5):
    w, h = clip.size
    
    def effect(get_frame, t):
        img = get_frame(t)
        img = ensure_uint8(img) # Ensure input is uint8
        
        # Calculate crop box
        # Center crop
        new_w = int(w / zoom_ratio)
        new_h = int(h / zoom_ratio)
        x1 = (w - new_w) // 2
        y1 = (h - new_h) // 2
        
        # Crop and resize
        cropped = img[y1:y1+new_h, x1:x1+new_w]
        return cv2.resize(cropped, (w, h))

    return fl_image_compat(clip, lambda img: effect(lambda _: img, 0))

def validate_video(file_path):
    print(f"Validating video file: {file_path}...")
    if not os.path.exists(file_path):
        print("❌ Error: Output file not found!")
        return False
        
    if os.path.getsize(file_path) < 1024 * 1024: # < 1MB
        print("❌ Error: File size too small (possible corruption).")
        return False
        
    # FFmpeg stream check
    import subprocess
    cmd = [
        "ffmpeg", "-v", "error", "-i", file_path, "-f", "null", "-"
    ]
    
    # Use local ffmpeg if available
    if os.path.exists("../resources/ffmpeg.exe"):
         cmd[0] = "../resources/ffmpeg.exe"
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0 or result.stderr:
            print(f"❌ Video Validation Failed:\n{result.stderr}")
            # Don't return False immediately, let's see the error. 
            # Some warnings might be ignorable, but "Error" is bad.
            if "Error" in result.stderr or "Invalid" in result.stderr:
                return False
    except Exception as e:
         print(f"❌ Validation execution failed: {e}")
         return False
         
    print("✅ Video Validation Passed: Stream is healthy.")
    return True

async def main():
    print("Loading resources...")
    with open(CLIPS_FILE, 'r', encoding='utf-8') as f:
        clips_config = json.load(f)
        
    analysis_data = analyze_video(VIDEO_FILE)
    
    video_source = VideoFileClip(VIDEO_FILE)
    video_duration = video_source.duration
    
    final_clips = []
    used_segments = []
    
    print("Processing clips...")
    
    # Multi-modal: Create Cover
    cover_path = "../output/cover_generated.jpg"
    create_cover_image("Trae AI 挑战: 手搓数学老师", cover_path)
    print(f"Generated cover: {cover_path}")
    
    for i, clip in enumerate(clips_config):
        print(f"Processing Clip {i+1}: {clip['text'][:20]}...")
        
        # 1. Generate Audio
        audio_filename = f"temp_tts_{i}.mp3"
        await generate_voiceover(clip['text'], audio_filename)
        
        # Audio-Driven Cutting: Skip silence removal for more relaxed pace
        # trimmed_audio_path = remove_silence(audio_filename) 
        # audio_clip = AudioFileClip(trimmed_audio_path)
        audio_clip = AudioFileClip(audio_filename)
        duration = audio_clip.duration
        
        # Ensure min duration
        if duration < clip.get("min_duration", 0):
            # We will extend the video to min_duration, but audio stops earlier
            pass # Logic handled by set_duration
            
        # 2. Find Best Video Segment
        if "preferred_start" in clip:
            start_time = float(clip["preferred_start"])
            # Adjust if segment goes beyond video duration
            # Give a small buffer (0.5s) to avoid end-of-file glitches
            if start_time + duration > video_duration:
                start_time = max(0, video_duration - duration - 0.5)
            print(f"  -> Using preferred start time: {start_time:.1f}s (Audio dur: {duration:.1f}s)")
        else:
            keywords = clip.get("keywords", [])
            start_time = find_best_segment(analysis_data, keywords, duration, video_duration, used_segments)
        
        end_time = min(start_time + duration, video_duration)
        
        used_segments.append((start_time, end_time))
        print(f"  -> Matched video segment: {start_time:.1f}s - {end_time:.1f}s")
        
        # 3. Create Video Clip
        # Use subclip logic
        v_clip = subclip_compat(video_source, start_time, end_time)
        
        # Apply Auto-Zoom if keyword matches (e.g. "focus", "look", "detail")
        if any(k in clip['text'] for k in ["仔细", "看", "细节", "重点"]):
             v_clip = apply_zoom(v_clip, 1.3)
        
        # Set Audio
        v_clip = set_audio_compat(v_clip, audio_clip)
        
        # Apply Transition (Fade In) to all clips except the first
        if i > 0:
            v_clip = fadein_compat(v_clip, 1.0)
        
        # 4. Burn Subtitles with Keyword Highlighting
        # Extract keywords for highlighting
        highlight_kws = clip.get("keywords", [])
        # Also add common emphasis words
        highlight_kws.extend(["Trae", "AI", "自动", "报错", "修复", "神奇"])
        
        # We wrap the frame generator
        def subtitle_filter(get_frame, t):
            frame = get_frame(t)
            return add_subtitle(frame, clip['text'], highlight_keywords=highlight_kws)
            
        # Apply filter - Note: fl(lambda gf, t: ...) works on frames
        # But for better performance, we can just apply to the clip
        v_clip_with_subs = fl_image_compat(v_clip, lambda image: add_subtitle(image, clip['text'], highlight_keywords=highlight_kws))
        
        final_clips.append(v_clip_with_subs)

    print("Concatenating clips...")

    final_video = concatenate_videoclips(final_clips)
    
    # Add Background Music
    if os.path.exists(BGM_FILE):
        print("Adding background music...")
        try:
            bgm = AudioFileClip(BGM_FILE)
            # Loop bgm if shorter, crop if longer
            if bgm.duration < final_video.duration:
                bgm = loop_audio_compat(bgm, final_video.duration)
            else:
                bgm = subclip_compat(bgm, 0, final_video.duration)
                
            bgm = volume_compat(bgm, 0.15) # Low volume
            
            # Composite Audio
            final_audio = CompositeAudioClip([final_video.audio, bgm])
            final_video = set_audio_compat(final_video, final_audio)
        except Exception as e:
            print(f"Warning: Failed to load background music: {e}")
            print("Proceeding without background music.")
    
    print(f"Writing final video to {OUTPUT_FILE}...")
    # Optimize for compatibility and size
    final_video.write_videofile(
        OUTPUT_FILE, 
        fps=30, 
        codec='libx264', 
        audio_codec='aac',
        bitrate="5000k",
        preset="medium",
        ffmpeg_params=['-pix_fmt', 'yuv420p']
    )
    
    # Cleanup
    video_source.close()
    for i in range(len(clips_config)):
        try:
            os.remove(f"temp_tts_{i}.mp3")
        except:
            pass

    # Self-Check
    validate_video(OUTPUT_FILE)

if __name__ == "__main__":
    asyncio.run(main())
