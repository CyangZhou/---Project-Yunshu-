import os
import random
import json
import asyncio
import edge_tts
import numpy as np
from PIL import Image, ImageFilter, ImageDraw, ImageFont

try:
    # MoviePy v2.0+
    from moviepy import VideoFileClip, concatenate_videoclips, CompositeVideoClip, TextClip, ColorClip, CompositeAudioClip, AudioFileClip, vfx
    MOVIEPY_V2 = True
except ImportError:
    # MoviePy v1.x
    from moviepy.editor import VideoFileClip, concatenate_videoclips, CompositeVideoClip, TextClip, ColorClip, CompositeAudioClip, AudioFileClip
    import moviepy.video.fx.all as vfx
    MOVIEPY_V2 = False

# Configuration
OUTPUT_DIR = "../output/short_drama"
TEMP_DIR = "../output/temp_short_drama"
FONT_PATH = "C:\\Windows\\Fonts\\msyh.ttc"

# Ensure directories exist
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)

def create_text_clip_compat(text, duration):
    """Compatible TextClip creation"""
    try:
        if MOVIEPY_V2:
            # Attempting v2 syntax
            return TextClip(text=text, font=FONT_PATH, font_size=50, color='yellow', stroke_color='black', stroke_width=2, method='caption', size=(680, None)).with_duration(duration)
        else:
            return TextClip(text, font=FONT_PATH, fontsize=50, color='yellow', stroke_color='black', stroke_width=2, method='caption', size=(680, None)).set_duration(duration)
    except Exception as e:
        print(f"TextClip failed (ImageMagick missing?), using PIL fallback: {e}")
        # Fallback to PIL ImageClip
        return create_text_clip_pil(text, duration)

def create_text_clip_pil(text, duration):
    w, h = 720, 1280
    img = Image.new('RGBA', (w, h), (0,0,0,0))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype(FONT_PATH, 50)
    except:
        font = ImageFont.load_default()
    
    # Simple centered text at bottom
    # We can't do complex caption wrapping easily without library, 
    # but let's just draw it at bottom center
    text_w = draw.textlength(text, font=font)
    x = (w - text_w) / 2
    y = h * 0.8
    
    # Stroke
    stroke_width = 2
    stroke_color = 'black'
    draw.text((x, y), text, font=font, fill='yellow', stroke_width=stroke_width, stroke_fill=stroke_color)
    
    # Create clip
    if MOVIEPY_V2:
        from moviepy import ImageClip
    else:
        from moviepy.editor import ImageClip
        
    return ImageClip(np.array(img)).set_duration(duration) if not MOVIEPY_V2 else ImageClip(np.array(img)).with_duration(duration)

def fl_compat(clip, func):
    if MOVIEPY_V2:
        return clip.transform(func)
    else:
        return clip.fl(func)

def subclip_compat(clip, start, end):
    if MOVIEPY_V2:
        return clip.subclipped(start, end)
    else:
        return clip.subclip(start, end)

def ensure_uint8(img):
    """Ensure image is uint8 range 0-255"""
    if img.dtype != np.uint8:
        if img.max() <= 1.0:
            img = (np.clip(img, 0, 1) * 255).astype(np.uint8)
        else:
            img = np.clip(img, 0, 255).astype(np.uint8)
    return img

def convert_to_vertical_9_16(get_frame, t):
    """
    Converts horizontal frame to vertical (9:16) with blurred background.
    """
    frame = get_frame(t)
    frame = ensure_uint8(frame)
    
    h, w = frame.shape[:2]
    pil_img = Image.fromarray(frame)
    
    # Target dimensions (e.g., 1080x1920 or scaled)
    # We will work with relative sizes to avoid huge processing
    target_aspect = 9/16
    
    # Create Blurred Background (Fill Vertical)
    # Crop center of original to fit 9:16 aspect roughly, then blur
    crop_w = int(h * target_aspect)
    bg = pil_img.resize((int(w * 1.5), int(h * 1.5)), Image.Resampling.LANCZOS) # Scale up
    # Center crop the scaled up image to be the background
    bg_w, bg_h = bg.size
    left = (bg_w - w) // 2 # Rough center
    # Actually, simpler: Resize original to cover the vertical height, keeping aspect ratio?
    # No, standard technique: Original video in center, blurred copy of original video filling background.
    
    # 1. Background: Resize original to fill height (will crop sides) OR fill width (will have black bars top/bottom)
    # Strategy: Resize to fill Height.
    new_h = int(w / target_aspect) # Height needed if we keep width
    # If original is 1920x1080. Target 9:16. 
    # Option A: Fit width (1080). Height = 1920. Original is 1080h. 
    # Background: Resize 1920x1080 -> 3413x1920 (to fill height) -> Crop center 1080x1920.
    
    bg_scale = max(1920/h, 1080/w) # Assume target is 1080x1920 equivalent
    # Let's just output a frame that IS 9:16 relative to input height?
    # Let's fix output resolution to 720x1280 (HD Vertical) for speed.
    out_w, out_h = 720, 1280
    
    # Background
    bg = pil_img.resize((out_w, out_h), Image.Resampling.LANCZOS) # Stretch? No, crop.
    # Proper blur background:
    # 1. Resize to cover (maintain aspect ratio)
    scale_bg = max(out_w/w, out_h/h)
    bg_w_new, bg_h_new = int(w * scale_bg), int(h * scale_bg)
    bg = pil_img.resize((bg_w_new, bg_h_new), Image.Resampling.LANCZOS)
    # Crop center
    left = (bg_w_new - out_w) // 2
    top = (bg_h_new - out_h) // 2
    bg = bg.crop((left, top, left + out_w, top + out_h))
    bg = bg.filter(ImageFilter.GaussianBlur(radius=20))
    
    # Foreground: Fit width
    scale_fg = out_w / w
    fg_w_new, fg_h_new = int(w * scale_fg), int(h * scale_fg)
    fg = pil_img.resize((fg_w_new, fg_h_new), Image.Resampling.LANCZOS)
    
    # Paste Foreground Center
    bg.paste(fg, (0, (out_h - fg_h_new) // 2))
    
    return np.array(bg)

def apply_zoom_effect(get_frame, t):
    """
    Applies a 1.2x Zoom effect (Center Crop)
    """
    frame = get_frame(t)
    frame = ensure_uint8(frame)
    
    h, w = frame.shape[:2]
    pil_img = Image.fromarray(frame)
    
    # Zoom logic: Crop 10% from all sides to get 80% view, then resize back
    zoom_factor = 0.85
    new_w = int(w * zoom_factor)
    new_h = int(h * zoom_factor)
    
    left = (w - new_w) // 2
    top = (h - new_h) // 2
    
    # Crop
    img_cropped = pil_img.crop((left, top, left + new_w, top + new_h))
    # Resize back to original
    img_resized = img_cropped.resize((w, h), Image.Resampling.LANCZOS)
    
    return np.array(img_resized)

async def generate_voiceover(text, voice="zh-CN-YunxiNeural", rate="+30%"):
    # Yunxi is energetic male, good for movie recap. +30% speed is viral standard.
    # Pitch adjustment: pitch="+0Hz" (default) or slightly lower for authority
    output_path = os.path.join(TEMP_DIR, f"tts_{hash(text)}.mp3")
    communicate = edge_tts.Communicate(text, voice, rate=rate, pitch="-5Hz") # Deeper voice
    await communicate.save(output_path)
    return output_path

def create_short_drama_video(video_path, script_sections, output_filename="short_drama_viral.mp4"):
    print(f"🔥 Starting Short Drama Engine for: {video_path}")
    
    final_clips = []
    movie = VideoFileClip(video_path)
    movie_duration = movie.duration
    
    # Force output resolution to 720x1280 (Vertical)
    # We will apply the conversion filter to clips
    
    # --- J-CUT / L-CUT IMPLEMENTATION ---
    # To achieve "Audio Lead" (J-Cut):
    # Next Audio starts BEFORE Current Video ends.
    # We must decouple Video and Audio streams.
    
    global_visuals = []
    global_audios = []
    global_texts = []
    
    J_CUT_DURATION = 0.5 # Seconds
    
    for i, section in enumerate(script_sections):
        text = section['text']
        print(f"⚡ Section {i+1}: {text[:15]}...")
        
        # 1. Generate Audio
        audio_path = asyncio.run(generate_voiceover(text))
        audio_clip = AudioFileClip(audio_path)
        audio_dur = audio_clip.duration
        
        # 2. Determine Video Duration
        # If this is NOT the first clip, we shorten the video by J_CUT_DURATION
        # to "make room" for the audio overlap relative to the visual cut.
        # Wait, the logic is:
        # Video Track: [V0 (d0)][V1 (d1-overlap)]...
        # Audio Track: [A0 (d0)][A1 (d1)]... 
        # A1 starts at (V0_end - overlap).
        
        # So for i > 0, the visual duration we need is (audio_dur - J_CUT_DURATION)
        # But we must ensure it's not too short.
        current_overlap = min(J_CUT_DURATION, audio_dur * 0.3) # Safety cap
        
        if i == 0:
            video_dur = audio_dur
        else:
            video_dur = audio_dur - current_overlap
            
        # 3. Generate Visuals
        # Fast cuts logic within the section
        num_cuts = max(1, int(video_dur / 2.0))
        clip_dur = video_dur / num_cuts
        
        section_visual_clips = []
        for _ in range(num_cuts):
            start = random.uniform(0, movie_duration - clip_dur - 5)
            sub = subclip_compat(movie, start, start + clip_dur)
            
            # Convert to Vertical 9:16
            vert_sub = fl_compat(sub, convert_to_vertical_9_16)
            
            # Smart Jump Cut (Zoom on odd clips)
            if _ % 2 == 1:
                vert_sub = fl_compat(vert_sub, apply_zoom_effect)
            
            # Metadata fix
            try:
                # Update size metadata
                vert_sub.size = (720, 1280)
                if not MOVIEPY_V2:
                    # In v1, we often need to update these explicitly
                    vert_sub.w = 720
                    vert_sub.h = 1280
            except Exception as e:
                print(f"Warning: Could not update clip metadata: {e}")
            
            section_visual_clips.append(vert_sub)
            
        section_video = concatenate_videoclips(section_visual_clips)
        
        # 4. Add Subtitles (Visual only)
        # We add subtitles to the video part directly. 
        # Note: Subtitle timing should match AUDIO, not necessarily VIDEO if they are offset.
        # But for simplicity in v1 J-Cut, we attach subtitle to the visual block.
        # Ideally, subtitle should appear when audio starts.
        # If Audio starts 0.5s early (during previous clip), Subtitle should appear then?
        # That's complex. Let's keep subtitle aligned with Visual Block for now.
        # It means subtitle appears when cut happens.
        
        txt_clip = create_text_clip_compat(text, section_video.duration)
        if txt_clip.w < 720:
             if MOVIEPY_V2:
                 txt_clip = txt_clip.with_position(('center', 0.8), relative=True)
             else:
                 txt_clip = txt_clip.set_position(('center', 0.8), relative=True)
                 
        comp_section = CompositeVideoClip([section_video, txt_clip], size=(720, 1280))
        
        global_visuals.append(comp_section)
        global_audios.append((audio_clip, current_overlap)) # Store overlap used for this clip

    # --- COMPOSITION ---
    print("🎬 Compositing Video & Audio Tracks with J-Cuts...")
    
    # 1. Video Track (Simple Concatenation)
    final_video_track = concatenate_videoclips(global_visuals)
    
    # 2. Audio Track (Composite with Overlaps)
    # Calculate start times
    audio_clips_for_composite = []
    current_time = 0
    
    for i, (audioclip, overlap) in enumerate(global_audios):
        # Calculate start time
        if i == 0:
            start_t = 0
        else:
            # Start 'overlap' seconds before the previous video ended?
            # Previous video ended at 'current_time'.
            # We want to start at current_time - overlap.
            start_t = current_time - overlap
            
        # Apply fading for smooth transition?
        # A simple crossfade is nice.
        # Fade In 0.2s, Fade Out 0.2s?
        # Only if we want to mix. Here we assume sequential speech.
        # But J-Cut usually implies clean cut of audio, just shifted.
        # Let's add small fade to avoid clicks.
        if MOVIEPY_V2:
             audioclip = audioclip.with_start(start_t)
        else:
             audioclip = audioclip.set_start(start_t)
             
        audio_clips_for_composite.append(audioclip)
        
        # Update current_time based on VIDEO duration
        # global_visuals[i].duration should be used.
        current_time += global_visuals[i].duration

    final_audio_track = CompositeAudioClip(audio_clips_for_composite)
    
    # Trim Audio to match Video (or vice versa)
    # Usually Audio might stick out a bit.
    final_duration = final_video_track.duration
    if MOVIEPY_V2:
        final_audio_track = final_audio_track.subclipped(0, final_duration)
        final_video = final_video_track.with_audio(final_audio_track)
    else:
        final_audio_track = final_audio_track.subclip(0, final_duration)
        final_video = final_video_track.set_audio(final_audio_track)
    
    # BGM: Fast paced
    
    # BGM: Fast paced
    # Smart BGM Selection
    bgm_pool = []
    # Load all BGMs
    bgm_base = "../resources/bgm"
    for mood in ["suspense", "epic", "emotional"]:
        mood_dir = os.path.join(bgm_base, mood)
        if os.path.exists(mood_dir):
             for f in os.listdir(mood_dir):
                 if f.endswith(".mp3"):
                     bgm_pool.append(os.path.join(mood_dir, f))
    
    bgm_path = "../resources/background_music.mp3" # Fallback
    if bgm_pool:
        bgm_path = random.choice(bgm_pool)
        print(f"🎵 Selected Viral BGM: {bgm_path}")

    if os.path.exists(bgm_path):
        bgm = AudioFileClip(bgm_path)
        
        # AUTO DUCKING LOGIC
        # We want BGM to be lower when voice is active.
        # Since voice is active almost 100% of time in viral videos,
        # we just set a constant low volume (background).
        # But for 'intro' or 'pauses', we could boost it.
        # For now, constant low volume is safer for viral pace.
        
        target_vol = 0.12 # Slightly louder than 0.1, but safe for voice
        
        if not MOVIEPY_V2:
            bgm = bgm.volumex(target_vol)
            from moviepy.audio.fx.all import audio_loop
            bgm = audio_loop(bgm, duration=final_video.duration)
            final_video = final_video.set_audio(CompositeAudioClip([final_video.audio, bgm]))
        else:
            bgm = bgm.with_volume_scaled(target_vol)
            # v2 loop
            bgm = bgm.with_effects([vfx.Loop(duration=final_video.duration)])
            final_video = final_video.with_audio(CompositeAudioClip([final_video.audio, bgm]))
        
    output_path = os.path.join(OUTPUT_DIR, output_filename)
    if MOVIEPY_V2:
        final_video.write_videofile(output_path, fps=30, bitrate="4000k", audio_codec="aac")
    else:
        final_video.write_videofile(output_path, fps=30, bitrate="4000k", audio_codec="aac")
    print(f"🚀 Viral Video Ready: {output_path}")
    return output_path

if __name__ == "__main__":
    import sys
    
    # Demo Script (Suspense Style)
    demo_script = [
        {"text": "注意看，这个男人叫小帅，他刚刚发现妻子竟然是千亿集团的总裁！"},
        {"text": "上一秒还在被丈母娘羞辱，下一秒无数豪车停在了门口。"},
        {"text": "这一巴掌，直接打得丈母娘怀疑人生！"},
        {"text": "想知道小帅是如何逆袭的吗？左下角链接看全集！"}
    ]
    
    # Determine video path
    test_movie = "../resources/drama_source.mp4"
    
    if len(sys.argv) > 1:
        test_movie = sys.argv[1]
    
    if not os.path.exists(test_movie):
        # Fallback to old default
        test_movie = "../resources/ai数学老师.mp4"
        
    if os.path.exists(test_movie):
        print(f"🔥 Starting Short Drama Engine for: {test_movie}")
        out_file = create_short_drama_video(test_movie, demo_script, output_filename=f"short_drama_{os.path.basename(test_movie).split('.')[0]}.mp4")
        
        # --- AUTO QA ---
        try:
            from video_qa import analyze_video_quality
            print("\n🤖 Running Auto-QA Guard...")
            analyze_video_quality(out_file)
        except ImportError:
            print("⚠️ QA Tool not found, skipping check.")
            
    else:
        print(f"Resource not found: {test_movie}")
