import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import os
import textwrap

# Configuration
VIDEO_FILE = "../resources/ai数学老师.mp4"
OUTPUT_FILE = "../output/cover_vertical.jpg"
FONT_PATH = "C:\\Windows\\Fonts\\msyh.ttc" # Microsoft YaHei
TITLE = "Trae AI 挑战\n手搓数学老师" # Use \n for manual line break
SUBTITLE = "不会写代码也能做软件？"

def get_video_frame(video_path, time_sec=5.0):
    """Extract a frame from the video at specific time"""
    if not os.path.exists(video_path):
        print(f"Video not found: {video_path}")
        return None
        
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    cap.set(cv2.CAP_PROP_POS_MSEC, time_sec * 1000)
    ret, frame = cap.read()
    cap.release()
    
    if ret:
        # Convert BGR to RGB
        return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    return None

def create_vertical_cover():
    print(f"Creating vertical cover for {VIDEO_FILE}...")
    
    # Target dimensions (9:16)
    TARGET_W, TARGET_H = 1080, 1920
    
    # 1. Get Background
    frame = get_video_frame(VIDEO_FILE, time_sec=35.0) # Pick a frame with UI
    
    if frame is None:
        print("Using dark background fallback.")
        img = Image.new('RGB', (TARGET_W, TARGET_H), color=(30, 30, 30))
    else:
        # Resize and Crop to fill 9:16
        img = Image.fromarray(frame)
        
        # Calculate aspect ratios
        img_ratio = img.width / img.height
        target_ratio = TARGET_W / TARGET_H
        
        if img_ratio > target_ratio:
            # Image is wider than target, crop width
            new_h = TARGET_H
            new_w = int(new_h * img_ratio)
            img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            # Center crop
            left = (new_w - TARGET_W) // 2
            img = img.crop((left, 0, left + TARGET_W, TARGET_H))
        else:
            # Image is taller than target (unlikely for landscape video), crop height
            new_w = TARGET_W
            new_h = int(new_w / img_ratio)
            img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            top = (new_h - TARGET_H) // 2
            img = img.crop((0, top, TARGET_W, top + TARGET_H))
    
    # 2. Add Dark Overlay for Text Readability
    overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
    draw_overlay = ImageDraw.Draw(overlay)
    # Gradient-like overlay (top and bottom dark)
    # Since PIL doesn't have simple gradient, use semi-transparent rects
    draw_overlay.rectangle([0, 0, TARGET_W, TARGET_H], fill=(0, 0, 0, 100)) # General dim
    draw_overlay.rectangle([0, 200, TARGET_W, 800], fill=(0, 0, 0, 50)) # Darker area for text
    
    img = Image.alpha_composite(img.convert('RGBA'), overlay).convert('RGB')
    
    # 3. Draw Text
    draw = ImageDraw.Draw(img)
    
    try:
        font_title = ImageFont.truetype(FONT_PATH, 100)
        font_sub = ImageFont.truetype(FONT_PATH, 60)
    except:
        font_title = ImageFont.load_default()
        font_sub = ImageFont.load_default()
    
    # Draw Title
    # Center vertically roughly
    center_y = TARGET_H // 3
    
    # Split title by lines
    lines = TITLE.split('\n')
    current_y = center_y
    
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font_title)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        
        # Shadow
        draw.text(((TARGET_W - w)/2 + 4, current_y + 4), line, font=font_title, fill="black")
        # Text
        draw.text(((TARGET_W - w)/2, current_y), line, font=font_title, fill="#FFD700") # Gold
        
        current_y += h + 20
        
    # Draw Subtitle
    bbox_sub = draw.textbbox((0, 0), SUBTITLE, font=font_sub)
    ws = bbox_sub[2] - bbox_sub[0]
    draw.text(((TARGET_W - ws)/2 + 2, current_y + 50 + 2), SUBTITLE, font=font_sub, fill="black")
    draw.text(((TARGET_W - ws)/2, current_y + 50), SUBTITLE, font=font_sub, fill="white")

    # Add "Trae AI" branding at bottom
    branding = "Powered by Trae"
    bbox_br = draw.textbbox((0, 0), branding, font=font_sub)
    wb = bbox_br[2] - bbox_br[0]
    draw.text(((TARGET_W - wb)/2, TARGET_H - 150), branding, font=font_sub, fill=(200, 200, 200))

    # Save
    if not os.path.exists("../output"):
        os.makedirs("../output")
        
    img.save(OUTPUT_FILE, quality=95)
    print(f"✅ Vertical cover saved to: {OUTPUT_FILE}")

if __name__ == "__main__":
    create_vertical_cover()
