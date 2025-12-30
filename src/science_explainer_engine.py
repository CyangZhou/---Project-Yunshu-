import os
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import math

try:
    from moviepy.editor import VideoFileClip, ImageClip, TextClip, CompositeVideoClip, ColorClip, vfx
    MOVIEPY_V2 = False
except ImportError:
    try:
        from moviepy import VideoFileClip, ImageClip, TextClip, CompositeVideoClip, ColorClip, vfx
        MOVIEPY_V2 = True
    except ImportError:
        print("Error: MoviePy not found. Please install it.")
        sys.exit(1)

# --- CONFIGURATION ---
OUTPUT_DIR = r"../output/science_explainer"
ASSET_DIR = r"../output/science_explainer/assets"
TEMP_DIR = r"../output/science_explainer/temp"

# Ensure directories exist
for d in [OUTPUT_DIR, ASSET_DIR, TEMP_DIR]:
    if not os.path.exists(d):
        os.makedirs(d)

# --- COMPATIBILITY LAYERS ---

def create_text_clip_compat(text, fontsize=70, color='white', font='Arial', duration=3.0, bg_color=None):
    """
    Creates a TextClip compatible with MoviePy v1 and v2.
    Uses PIL to generate text image to avoid ImageMagick dependency issues.
    """
    # Create text image using PIL
    # Estimate size
    try:
        # Try to use a font that supports Chinese if possible, otherwise default
        # Windows: msyh.ttc (Microsoft YaHei), SimHei.ttf
        font_path = "arial.ttf" # Default
        if sys.platform == "win32":
             # Common Chinese fonts on Windows
             possible_fonts = ["msyh.ttc", "simhei.ttf", "arial.ttf"]
             for f in possible_fonts:
                 try:
                     # Check if we can load it (requires path or system look up, PIL does system lookup well)
                     ImageFont.truetype(f, fontsize)
                     font_path = f
                     break
                 except:
                     continue
        
        pil_font = ImageFont.truetype(font_path, fontsize)
    except IOError:
        pil_font = ImageFont.load_default()

    # Get text size
    left, top, right, bottom = pil_font.getbbox(text)
    w = right - left
    h = bottom - top
    
    # Add some padding
    w += 40
    h += 40

    # Create image
    if bg_color:
        img = Image.new('RGBA', (w, h), bg_color)
    else:
        img = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    
    draw = ImageDraw.Draw(img)
    # Draw text centered
    draw.text(((w - (right-left))/2, (h - (bottom-top))/2 - top), text, font=pil_font, fill=color)

    # Convert to numpy array for MoviePy
    img_np = np.array(img)
    
    # Create clip
    if MOVIEPY_V2:
        clip = ImageClip(img_np).with_duration(duration)
    else:
        clip = ImageClip(img_np).set_duration(duration)
        
    return clip

# --- ASSET GENERATION ---

def create_gradient_bg(size=(720, 1280), color1=(20, 20, 40), color2=(60, 40, 100)):
    """Create a vertical gradient background."""
    w, h = size
    base = Image.new('RGB', (w, h), color1)
    top = Image.new('RGB', (w, h), color2)
    mask = Image.new('L', (w, h))
    mask_data = []
    for y in range(h):
        mask_data.extend([int(255 * (y / h))] * w)
    mask.putdata(mask_data)
    base.paste(top, (0, 0), mask)
    
    if MOVIEPY_V2:
        return ImageClip(np.array(base)).with_duration(5) # Default duration, override later
    else:
        return ImageClip(np.array(base)).set_duration(5)

def create_shape(shape_type, color, size=(200, 200), filename=None):
    """
    Create a simple geometric shape asset.
    shape_type: 'circle', 'triangle', 'square', 'star'
    """
    img = Image.new('RGBA', size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    w, h = size
    
    if shape_type == 'circle':
        draw.ellipse([0, 0, w, h], fill=color)
    elif shape_type == 'square':
        draw.rectangle([0, 0, w, h], fill=color)
    elif shape_type == 'triangle':
        # Pointing up
        points = [(w/2, 0), (0, h), (w, h)]
        draw.polygon(points, fill=color)
    elif shape_type == 'star':
        # Simple 5-point star (rough approximation)
        cx, cy = w/2, h/2
        r_outer = w/2
        r_inner = w/4
        points = []
        for i in range(10):
            angle = i * 36 * math.pi / 180 - math.pi / 2
            r = r_outer if i % 2 == 0 else r_inner
            x = cx + r * math.cos(angle)
            y = cy + r * math.sin(angle)
            points.append((x, y))
        draw.polygon(points, fill=color)
        
    if filename:
        path = os.path.join(ASSET_DIR, filename)
        img.save(path)
        return path
    return img

# --- ANIMATION FUNCTIONS ---

def animate_slide_in(clip, direction='left', duration=1.0, width=720, height=1280):
    """
    Animate a clip sliding in from a direction.
    direction: 'left', 'right', 'bottom', 'top'
    """
    w, h = clip.w, clip.h
    
    def pos(t):
        if t < duration:
            # Ease out cubic: 1 - (1 - t)^3
            progress = t / duration
            progress = 1 - (1 - progress) ** 3
            
            if direction == 'left':
                start_x = -w
                end_x = (width - w) // 2
                x = int(start_x + (end_x - start_x) * progress)
                return (x, 'center')
            elif direction == 'right':
                start_x = width
                end_x = (width - w) // 2
                x = int(start_x + (end_x - start_x) * progress)
                return (x, 'center')
            elif direction == 'bottom':
                start_y = height
                end_y = (height - h) // 2
                y = int(start_y + (end_y - start_y) * progress)
                return ('center', y)
            elif direction == 'top':
                start_y = -h
                end_y = (height - h) // 2
                y = int(start_y + (end_y - start_y) * progress)
                return ('center', y)
        else:
            return ('center', 'center')
        
    if MOVIEPY_V2:
        return clip.with_position(pos)
    else:
        return clip.set_position(pos)

def animate_pulse(clip, duration=1.0):
    """
    Animate a clip pulsing (scale up and down).
    """
    def resize_func(t):
        # Pulse frequency: 1Hz, Amplitude 10%
        scale = 1.0 + 0.1 * np.sin(2 * np.pi * t * 2) # Faster pulse
        return scale

    if MOVIEPY_V2:
         # Note: vfx.Resize might not be dynamic in all versions, but let's try
         # For dynamic resize in moviepy, usually clip.resize(lambda t: ...)
         return clip.with_effects([vfx.Resize(resize_func)]) 
    else:
         return clip.resize(resize_func)

def animate_float(clip, amplitude=20, speed=1.0):
    """
    Animate a clip floating gently (up and down).
    Must be applied to a clip that already has a base position.
    This is complex because we need to know the base position.
    Instead, we'll return a position function that assumes center-ish or relative.
    Actually, simpler: use relative position if possible, or just oscillate Y.
    """
    # Assuming the clip is centered, we add an offset
    w, h = clip.w, clip.h
    
    def pos(t):
        # Base is center
        base_x = (720 - w) // 2
        base_y = (1280 - h) // 2
        
        offset_y = amplitude * np.sin(2 * np.pi * t * speed)
        return (base_x, int(base_y + offset_y))

    if MOVIEPY_V2:
        return clip.with_position(pos)
    else:
        return clip.set_position(pos)

# --- DEMO GENERATOR: COFFEE EXPLAINER ---

def create_coffee_demo():
    print("☕ Brewing Coffee Explainer Demo...")
    
    # 1. Create Assets
    # Background: Deep Blue/Purple (Kurzgesagt Night/Space feel)
    bg_clip = create_gradient_bg(size=(720, 1280), color1=(20, 20, 50), color2=(50, 30, 90))
    bg_clip = bg_clip.set_duration(15) if not MOVIEPY_V2 else bg_clip.with_duration(15)
    
    # Assets
    create_shape('circle', (100, 200, 255, 255), size=(150, 150), filename='adenosine.png') # Blue Circle
    create_shape('triangle', (255, 50, 50, 255), size=(150, 150), filename='caffeine.png') # Red Triangle
    create_shape('square', (255, 200, 50, 255), size=(200, 100), filename='receptor.png') # Yellow Receptor (Platform)
    
    # Load Assets as Clips
    adenosine_img = os.path.join(ASSET_DIR, 'adenosine.png')
    caffeine_img = os.path.join(ASSET_DIR, 'caffeine.png')
    receptor_img = os.path.join(ASSET_DIR, 'receptor.png')
    
    def get_clip(path, dur):
        if MOVIEPY_V2:
            return ImageClip(path).with_duration(dur)
        else:
            return ImageClip(path).set_duration(dur)

    # --- SCENE 1: HOOK (0-3s) ---
    # Text: "为什么咖啡能提神？"
    title_txt = create_text_clip_compat("为什么咖啡能提神？", fontsize=60, color='white', duration=3)
    title_txt = animate_slide_in(title_txt, direction='top', duration=0.8, height=1280)
    
    # Visual: Caffeine Cup (Represented by Red Triangle for now) sliding in
    cup = get_clip(caffeine_img, 3).resize(1.5) if not MOVIEPY_V2 else get_clip(caffeine_img, 3).with_effects([vfx.Resize(1.5)])
    cup = animate_slide_in(cup, direction='bottom', duration=0.8, height=1280)
    
    # --- SCENE 2: ADENOSINE (3-8s) ---
    # Text: "腺苷 = 困意"
    scene2_start = 3
    scene2_dur = 5
    
    adenosine_txt = create_text_clip_compat("腺苷 (Adenosine)\n积累 = 困意", fontsize=50, color='#AAAAFF', duration=scene2_dur)
    if MOVIEPY_V2:
        adenosine_txt = adenosine_txt.with_position(('center', 200)).with_start(scene2_start)
    else:
        adenosine_txt = adenosine_txt.set_position(('center', 200)).set_start(scene2_start)
        
    # Visual: Adenosine floating
    mol1 = get_clip(adenosine_img, scene2_dur)
    mol1 = animate_float(mol1, amplitude=30, speed=0.5)
    if MOVIEPY_V2:
        mol1 = mol1.with_start(scene2_start)
    else:
        mol1 = mol1.set_start(scene2_start)
        
    # --- SCENE 3: CAFFEINE BLOCK (8-15s) ---
    # Text: "咖啡因 = 阻断！"
    scene3_start = 8
    scene3_dur = 7
    
    caffeine_txt = create_text_clip_compat("咖啡因 (Caffeine)\n抢占位置！", fontsize=50, color='#FF5555', duration=scene3_dur)
    if MOVIEPY_V2:
        caffeine_txt = caffeine_txt.with_position(('center', 200)).with_start(scene3_start)
    else:
        caffeine_txt = caffeine_txt.set_position(('center', 200)).set_start(scene3_start)
    
    # Visual: Receptor at bottom, Caffeine lands on it
    receptor = get_clip(receptor_img, scene3_dur)
    if MOVIEPY_V2:
        receptor = receptor.with_position(('center', 800)).with_start(scene3_start)
    else:
        receptor = receptor.set_position(('center', 800)).set_start(scene3_start)
        
    # Caffeine falling in
    blocker = get_clip(caffeine_img, scene3_dur)
    
    def fall_anim(t):
        # Fall from top to receptor (y=800)
        # Start y=0, End y=650 (sitting on receptor)
        if t < 1.0:
            y = int(0 + 650 * (t/1.0))
            return ('center', y)
        else:
            return ('center', 650)
            
    if MOVIEPY_V2:
        blocker = blocker.with_position(fall_anim).with_start(scene3_start)
        # Pulse after landing (approx t > 9s total, t > 1s local)
        # Complex to chain effects in simple script, leaving pulse out for simplicity or apply to separate clip
    else:
        blocker = blocker.set_position(fall_anim).set_start(scene3_start)

    # Composite
    final_clips = [bg_clip, title_txt, cup, adenosine_txt, mol1, caffeine_txt, receptor, blocker]
    final = CompositeVideoClip(final_clips, size=(720, 1280)).set_duration(15) if not MOVIEPY_V2 else CompositeVideoClip(final_clips, size=(720, 1280)).with_duration(15)
    
    output_path = os.path.join(OUTPUT_DIR, "coffee_explainer.mp4")
    print(f"MoviePy - Building video {output_path}")
    final.write_videofile(output_path, fps=24)
    print(f"✅ Demo saved to: {output_path}")

if __name__ == "__main__":
    create_coffee_demo()
