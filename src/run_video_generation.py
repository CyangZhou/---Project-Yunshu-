# Universal Video Generation Script (Veo + CogVideo)
# This script helps you generate videos based on today's Douyin trends
# using either Google Veo (Quality) or Zhipu CogVideo (Free Tier Friendly).

import os
import sys

# Import engines
try:
    from veo_engine import generate_video_veo
except ImportError:
    generate_video_veo = None

try:
    from cogvideo_engine import generate_video_cogvideo
except ImportError:
    generate_video_cogvideo = None

# --- 2025-12-30 Douyin Trending Topics & Prompts ---
TRENDS = {
    "1": {
        "title": "🌌 海王星的恐惧 (Why Neptune is Scary)",
        "desc": "今日热榜：为何看到海王星觉得恐惧？巨物恐惧症+深海幽闭感。",
        "prompt": "Cinematic flyby of planet Neptune, deep blue thick atmosphere, giant dark storm spot, eerie and mysterious mood, vast space background, hyper-realistic, 8k resolution, 9:16 vertical video"
    },
    "2": {
        "title": "👵 硬核CS大妈 (Gamer Grandma)",
        "desc": "今日热榜：59岁阿姨'娟姨'爆头世界冠军。",
        "prompt": "A cool 60-year-old grandmother wearing professional esports headphones, playing a intense FPS game in a neon-lit cyber room, focused expression, glowing screen reflections on glasses, cyberpunk style, cinematic lighting, 9:16 vertical video"
    },
    "3": {
        "title": "🍟 薯片危机 (Junk Food Art)",
        "desc": "今日热榜：医生称薯片是垃圾食品之王。",
        "prompt": "Slow motion extreme close-up of potato chips falling and shattering, grease particles flying, unhealthy yellow lighting, dramatic food cinematography, macro photography, 9:16 vertical video"
    },
    "4": {
        "title": "🔬 显微镜下的打工妹洗漱包 (Museum Artifact)",
        "desc": "今日热榜：深圳博物馆展出'打工妹洗漱三件套'。",
        "prompt": "Cinematic museum display case shot of a vintage red plastic washbasin and a worn towel, spotlight, floating dust particles, emotional nostalgia atmosphere, high detail, 9:16 vertical video"
    }
}

def main():
    print("==========================================")
    print("   🎬 AI Video Generator (Veo + CogVideo) ")
    print("   📅 Based on Douyin Trends (2025-12-30) ")
    print("==========================================")

    # 1. Select Engine
    print("\n🔧 Select AI Engine:")
    print("  [1] Google Veo 3.1 (High Quality, Requires Vertex AI/Gemini Key)")
    print("  [2] Zhipu CogVideoX (Free Trial Available, Requires Zhipu API Key)")
    print("  [3] 🆓 How to use for FREE? (Guide & Notebook)")
    
    engine_choice = input("👉 Select engine (1, 2 or 3): ").strip()
    
    if engine_choice == "3":
        print("\n📚 --- FREE VIDEO GENERATION GUIDE ---")
        print("1. 🎁 Zhipu AI (智谱): New users get ~25M free tokens (enough for 50+ videos).")
        print("   -> Register at: https://bigmodel.cn/")
        print("2. ☁️ Google Colab / ModelScope: Run open-source models on free cloud GPUs.")
        print("   -> Use the notebook I created: notebooks/Free_Video_Generation.ipynb")
        print("3. 🌐 Web Tools: Kling AI (可灵) & Luma have daily free quotas on their websites.")
        print("   -> Check docs/云舒技能库/视频生成/FREE_TOOLS_GUIDE.md for details.")
        print("\n💡 Recommendation: Try Zhipu first (Option 2), it's the easiest 'Free API'.")
        return

    engine_func = None
    api_key_name = ""
    
    if engine_choice == "1":
        engine_func = generate_video_veo
        api_key_name = "GEMINI_API_KEY"
    elif engine_choice == "2":
        engine_func = generate_video_cogvideo
        api_key_name = "ZHIPU_API_KEY"
    else:
        print("❌ Invalid engine selection.")
        return

    if engine_func is None:
        print(f"❌ Selected engine module could not be imported. Check dependencies.")
        return

    # 2. Check API Key
    api_key = os.environ.get(api_key_name)
    if not api_key:
        print(f"\n⚠️  {api_key_name} not found in environment variables.")
        if api_key_name == "GEMINI_API_KEY":
            print("   💡 Get free key at: https://aistudio.google.com/")
        else:
            print("   💡 Get free key at: https://bigmodel.cn/ (New users get free tokens)")
            
        key_input = input(f"Please paste your {api_key_name} here: ").strip()
        if key_input:
            os.environ[api_key_name] = key_input
        else:
            print("❌ No API Key provided. Exiting.")
            return

    # 3. Select Topic
    print("\n🔥 Today's Trending Topics:")
    for key, val in TRENDS.items():
        print(f"  [{key}] {val['title']} - {val['desc']}")
    print("  [0] Custom Prompt (自定义提示词)")

    choice = input("\n👉 Select a number (0-4): ").strip()

    prompt = ""
    if choice in TRENDS:
        selected = TRENDS[choice]
        print(f"\n✅ Selected: {selected['title']}")
        print(f"📝 Prompt: {selected['prompt']}")
        prompt = selected['prompt']
    elif choice == "0":
        prompt = input("\n✍️  Enter your prompt (English recommended): ").strip()
    else:
        print("❌ Invalid selection.")
        return

    if not prompt:
        print("❌ Empty prompt.")
        return

    # 4. Confirm & Generate
    print(f"\n🚀 Ready to generate video (Engine: {'Veo' if engine_choice=='1' else 'CogVideo'})...")
    confirm = input("Press ENTER to start (or 'n' to cancel): ")
    if confirm.lower() == 'n':
        print("Cancelled.")
        return

    try:
        # CogVideo usually fixed to 6s, Veo flexible.
        duration = 8 if engine_choice == "1" else 6
        output_path = engine_func(prompt, duration_seconds=duration, aspect_ratio="9:16")
        
        if output_path:
            print(f"\n✨ Success! Video saved to:\n{output_path}")
            # Optional: Open the folder
            # os.startfile(os.path.dirname(output_path))
        else:
            print("\n❌ Generation failed (check logs above).")
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    main()
