import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import os

# Configuration
VIDEO_FILE = "../resources/ai数学老师.mp4"
OUTPUT_FILE = "../output/cover_horizontal.jpg"
FONT_PATH = "C:\\Windows\\Fonts\\msyh.ttc" # Microsoft YaHei
TITLE = "Trae AI 挑战\n手搓数学老师" # Split into two lines for better safety margin
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

def create_horizontal_cover():
    print(f"Creating horizontal cover for {VIDEO_FILE}...")
    
    # Target dimensions (16:9)
    TARGET_W, TARGET_H = 1920, 1080
    
    # 1. Get Background
    # Using a different frame might be nice, or same one. 
    # Let's try 35s as it had UI elements which look "techy"
    frame = get_video_frame(VIDEO_FILE, time_sec=35.0) 
    
    if frame is None:
        print("Using dark background fallback.")
        img = Image.new('RGB', (TARGET_W, TARGET_H), color=(30, 30, 30))
    else:
        # Resize and Crop to fill 16:9
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
            # Image is taller/narrower, crop height
            new_w = TARGET_W
            new_h = int(new_w / img_ratio)
            img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            top = (new_h - TARGET_H) // 2
            img = img.crop((0, top, TARGET_W, top + TARGET_H))
    
    # 2. Add Dark Overlay for Text Readability
    overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
    draw_overlay = ImageDraw.Draw(overlay)
    
    # Horizontal design: Darken the left side more heavily for text
    # Gradient simulation
    # Full dim
    draw_overlay.rectangle([0, 0, TARGET_W, TARGET_H], fill=(0, 0, 0, 80)) 
    
    # Left side panel (stronger backing for text)
    # Let's make a stylish angled or simple rect
    draw_overlay.rectangle([0, 0, TARGET_W, 300], fill=(0, 0, 0, 100)) # Top bar
    draw_overlay.rectangle([0, 780, TARGET_W, 1080], fill=(0, 0, 0, 100)) # Bottom bar (for subtitle/branding)
    
    img = Image.alpha_composite(img.convert('RGBA'), overlay).convert('RGB')
    
    # 3. Draw Text
    draw = ImageDraw.Draw(img)
    
    try:
        font_title = ImageFont.truetype(FONT_PATH, 140) # Bigger for horizontal
        font_sub = ImageFont.truetype(FONT_PATH, 80)
    except:
        font_title = ImageFont.load_default()
        font_sub = ImageFont.load_default()
    
    # Draw Title (Centered)
    # Support multi-line title for safe zones
    lines = TITLE.split('\n')
    
    # Calculate total height to center the block
    total_text_h = 0
    line_heights = []
    line_gap = 20
    
    # Pre-calculate heights
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font_title)
        h = bbox[3] - bbox[1]
        line_heights.append(h)
        total_text_h += h
    
    total_text_h += line_gap * (len(lines) - 1)
    
    # Start Y position
    current_y = (TARGET_H - total_text_h) / 2 - 50 # Slightly above center
    
    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font_title)
        w = bbox[2] - bbox[0]
        h = line_heights[i]
        
        # Check safe zone (max width 80%)
        safe_width = TARGET_W * 0.8
        if w > safe_width:
             # Scale down just for this line if needed
             scale = safe_width / w
             new_size = int(140 * scale)
             try:
                 temp_font = ImageFont.truetype(FONT_PATH, new_size)
                 bbox = draw.textbbox((0, 0), line, font=temp_font)
                 w = bbox[2] - bbox[0]
                 h = bbox[3] - bbox[1]
                 # Use temp_font for this line
                 font_to_use = temp_font
             except:
                 font_to_use = font_title
        else:
             font_to_use = font_title

        x_line = (TARGET_W - w) / 2
        
        # Shadow
        draw.text((x_line + 5, current_y + 5), line, font=font_to_use, fill="black")
        # Text
        draw.text((x_line, current_y), line, font=font_to_use, fill="#FFD700") # Gold
        
        current_y += h + line_gap

    # Draw Subtitle
    bbox_sub = draw.textbbox((0, 0), SUBTITLE, font=font_sub)
    ws = bbox_sub[2] - bbox_sub[0]
    
    x_sub = (TARGET_W - ws) / 2
    y_sub = current_y + 40 # Below title (current_y is now updated after loop)
    
    draw.text((x_sub + 3, y_sub + 3), SUBTITLE, font=font_sub, fill="black")
    draw.text((x_sub, y_sub), SUBTITLE, font=font_sub, fill="white")

    # Add "Trae AI" branding
    branding = "Powered by Trae"
    font_brand = ImageFont.truetype(FONT_PATH, 50)
    bbox_br = draw.textbbox((0, 0), branding, font=font_brand)
    wb = bbox_br[2] - bbox_br[0]
    draw.text(((TARGET_W - wb)/2, TARGET_H - 100), branding, font=font_brand, fill=(200, 200, 200))

    # Save
    if not os.path.exists("../output"):
        os.makedirs("../output")
        
    img.save(OUTPUT_FILE, quality=95)
    print(f"✅ Horizontal cover saved to: {OUTPUT_FILE}")

if __name__ == "__main__":
    create_horizontal_cover()
