import os
import random
import json
import asyncio
import edge_tts
import numpy as np
from PIL import Image, ImageFilter
from moviepy.editor import VideoFileClip, concatenate_videoclips, CompositeVideoClip, TextClip, ColorClip, CompositeAudioClip, AudioFileClip
import moviepy.video.fx.all as vfx

# Configuration
OUTPUT_DIR = "../output/movie_commentary"
TEMP_DIR = "../output/temp"
FONT_PATH = "C:\\Windows\\Fonts\\msyh.ttc"

# Ensure directories exist
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)

def ensure_uint8(img):
    """Ensure image is uint8 range 0-255"""
    if img.dtype != np.uint8:
        if img.max() <= 1.0:
            img = (np.clip(img, 0, 1) * 255).astype(np.uint8)
        else:
            img = np.clip(img, 0, 255).astype(np.uint8)
    return img

def create_safe_visual(get_frame, t):
    """
    Applies 'Safe Mode' visual filter:
    1. Background: Blurred and zoomed version of the frame.
    2. Foreground: Original frame scaled down.
    """
    frame = get_frame(t)
    frame = ensure_uint8(frame)
    
    h, w = frame.shape[:2]
    pil_img = Image.fromarray(frame)
    
    # Create Background (Zoomed + Blurred)
    bg = pil_img.resize((int(w * 1.2), int(h * 1.2)), Image.Resampling.LANCZOS)
    bg = bg.crop((int(w*0.1), int(h*0.1), int(w*1.1), int(h*1.1))) # Center crop back to original size
    bg = bg.filter(ImageFilter.GaussianBlur(radius=15))
    
    # Create Foreground (Scaled Down)
    fg_scale = 0.85
    fg_w, fg_h = int(w * fg_scale), int(h * fg_scale)
    fg = pil_img.resize((fg_w, fg_h), Image.Resampling.LANCZOS)
    
    # Composite
    bg.paste(fg, ((w - fg_w) // 2, (h - fg_h) // 2))
    
    return np.array(bg)

def process_clip_safely(clip):
    """
    Takes a raw clip and applies the safe visual filter.
    Also ensures no audio from original clip (unless specified).
    """
    # Apply the visual effect
    # We use fl(make_frame) instead of fl_image for performance if possible, but fl_image is easier for PIL
    safe_clip = clip.fl_image(lambda img: create_safe_visual(lambda t: img, 0)) # Hacky adaptation for fl_image
    # Correct way for fl:
    safe_clip = clip.fl(create_safe_visual)
    
    return safe_clip.set_audio(None) # Remove original audio

async def generate_voiceover(text, voice="zh-CN-XiaoxiaoNeural", rate="-10%"):
    output_path = os.path.join(TEMP_DIR, f"tts_{hash(text)}.mp3")
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    await communicate.save(output_path)
    return output_path

def create_commentary_video(movie_path, script_sections, output_filename="commentary_video.mp4"):
    """
    script_sections: List of dicts [{'text': '...', 'duration_est': 5}, ...]
    """
    print(f"🎬 Processing Movie: {movie_path}")
    
    final_clips = []
    
    # Load Movie (lazy load)
    movie = VideoFileClip(movie_path)
    movie_duration = movie.duration
    
    current_time = 0
    
    for i, section in enumerate(script_sections):
        text = section['text']
        print(f"Processing section {i+1}: {text[:20]}...")
        
        # 1. Generate Audio
        audio_path = asyncio.run(generate_voiceover(text))
        audio_clip = AudioFileClip(audio_path)
        audio_duration = audio_clip.duration
        
        # 2. Select Video Segments
        # Strategy: Pick a random start time, or use sequential if meaningful
        # Safety: Each visual clip must be < 4 seconds.
        # So we might need multiple visual clips for one audio section.
        
        needed_duration = audio_duration
        segment_clips = []
        
        while needed_duration > 0:
            clip_dur = min(needed_duration, 3.5) # Max 3.5s per cut
            
            # Pick random spot (avoiding end)
            start = random.uniform(0, movie_duration - clip_dur - 10)
            
            # Extract
            raw_clip = movie.subclip(start, start + clip_dur)
            
            # Apply Safety Filter
            safe_clip = raw_clip.fl(create_safe_visual)
            
            segment_clips.append(safe_clip)
            needed_duration -= clip_dur
            
        # Concatenate visual segments for this section
        section_video = concatenate_videoclips(segment_clips)
        
        # Set Audio
        section_video = section_video.set_audio(audio_clip)
        
        # Add Subtitles (Simple TextClip)
        txt_clip = TextClip(text, font=FONT_PATH, fontsize=30, color='white', bg_color='rgba(0,0,0,0.6)', method='caption', size=(movie.w * 0.8, None))
        txt_clip = txt_clip.set_position(('center', 'bottom')).set_duration(section_video.duration)
        
        final_section = CompositeVideoClip([section_video, txt_clip])
        final_clips.append(final_section)
        
    # Final Concatenation
    final_video = concatenate_videoclips(final_clips)
    
    # Add BGM if exists
    bgm_path = "../resources/background_music.mp3"
    if os.path.exists(bgm_path):
        bgm = AudioFileClip(bgm_path).volumex(0.1) # Low volume
        # Loop BGM
        bgm = bgm.fx(vfx.audio_loop, duration=final_video.duration)
        final_video = final_video.set_audio(CompositeAudioClip([final_video.audio, bgm]))
        
    output_path = os.path.join(OUTPUT_DIR, output_filename)
    final_video.write_videofile(output_path, fps=24, bitrate="3000k")
    print(f"✅ Video saved to: {output_path}")
    return output_path

if __name__ == "__main__":
    # Demo Script
    demo_script = [
        {"text": "大家好，今天我们来看这部非常离谱的电影。"},
        {"text": "你看这个男主，他竟然在这个时候选择了开门，简直是自寻死路。"},
        {"text": "导演在这里用了一个非常长的镜头，试图表现角色的内心纠结，但我觉得有点拖沓。"},
        {"text": "总的来说，这部电影虽然逻辑感人，但特效还是不错的。"}
    ]
    
    # Use the existing ai math teacher video as a 'movie' for testing
    test_movie = "../resources/ai数学老师.mp4"
    if os.path.exists(test_movie):
        create_commentary_video(test_movie, demo_script)
    else:
        print("Test movie not found.")
