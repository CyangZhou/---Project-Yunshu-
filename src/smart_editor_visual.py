import os
import json
import asyncio
import numpy as np
import cv2
import easyocr
import edge_tts
import torch
# MoviePy v2 compatibility
try:
    from moviepy import VideoFileClip, concatenate_videoclips, CompositeAudioClip, AudioFileClip
except ImportError:
    from moviepy.editor import VideoFileClip, concatenate_videoclips, CompositeAudioClip, AudioFileClip

# --- 配置 ---
VIDEO_FILE = "ai数学助手开发过程.mp4"
OUTPUT_FILE = "final_video_visual.mp4"
ANALYSIS_FILE = "video_analysis.json"
CLIPS_FILE = "clips.json"
TEMP_AUDIO_DIR = "temp_audio"
VOICE = "zh-CN-YunxiNeural"

# 检查 CUDA
USE_GPU = torch.cuda.is_available()
print(f"使用 GPU 加速 OCR: {USE_GPU}")

# 初始化 EasyOCR
reader = easyocr.Reader(['en', 'ch_sim'], gpu=USE_GPU)

async def generate_tts(text, output_file):
    """生成 TTS 音频"""
    communicate = edge_tts.Communicate(text, VOICE)
    await communicate.save(output_file)

def analyze_video(video_path, interval=2.0):
    """
    分析视频内容：每隔 interval 秒提取一帧并识别文字
    """
    if os.path.exists(ANALYSIS_FILE):
        print(f"发现已有分析结果 {ANALYSIS_FILE}，直接加载...")
        with open(ANALYSIS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)

    print(f"开始分析视频 (间隔 {interval}s)... 这可能需要一点时间")
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps
    
    results = []
    
    current_sec = 0
    while current_sec < duration:
        # 跳转到指定时间
        cap.set(cv2.CAP_PROP_POS_MSEC, current_sec * 1000)
        ret, frame = cap.read()
        if not ret:
            break
            
        # 缩小图片以加快 OCR (可选)
        # frame = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
        
        try:
            # EasyOCR 识别
            # detail=0 只返回文本列表
            text_list = reader.readtext(frame, detail=0)
            
            # 简单的图像哈希 (判断画面变化) - 这里暂时只存 OCR 结果
            # 也可以加 perceptual hash
            
            results.append({
                "timestamp": round(current_sec, 2),
                "text": text_list
            })
            print(f"已分析: {current_sec:.1f}s / {duration:.1f}s -> 识别到 {len(text_list)} 个词")
            
        except Exception as e:
            print(f"分析出错 ({current_sec}s): {e}")

        current_sec += interval
    
    cap.release()
    
    # 保存结果
    with open(ANALYSIS_FILE, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
        
    return results

def find_best_segment(analysis_data, keywords, target_duration, video_duration, used_segments):
    """
    根据关键词寻找最佳片段
    """
    # 1. 给每个时间点打分
    scores = [] # (timestamp, score)
    
    for frame in analysis_data:
        ts = frame['timestamp']
        text_content = " ".join(frame['text']).lower()
        
        score = 0
        match_count = 0
        for kw in keywords:
            kw = kw.lower()
            if kw in text_content:
                score += 1
                match_count += 1
        
        # 额外加分：如果关键词多，分数高
        if match_count > 0:
            scores.append((ts, score))
    
    # 按分数排序
    scores.sort(key=lambda x: x[1], reverse=True)
    
    best_start = 0
    best_score = -1
    
    # 尝试找到一个未使用的高分段
    found = False
    for ts, score in scores:
        # 检查是否与已使用的重叠
        # 我们假设以 ts 为中心，或者 ts 为开始
        # 简单起见，以 ts 为开始
        candidate_start = ts
        candidate_end = ts + target_duration
        
        if candidate_end > video_duration:
            continue
            
        overlap = False
        for u_start, u_end in used_segments:
            # 检查重叠
            if not (candidate_end <= u_start or candidate_start >= u_end):
                overlap = True
                break
        
        if not overlap:
            best_start = candidate_start
            best_score = score
            found = True
            break
    
    if not found:
        print("  -> 未找到关键词匹配片段，使用默认策略 (未使用的最早片段)")
        # 简单寻找一个未使用的空隙
        # 这里简化处理：直接往后找空地
        cursor = 0
        while cursor + target_duration <= video_duration:
            overlap = False
            for u_start, u_end in used_segments:
                if not (cursor + target_duration <= u_start or cursor >= u_end):
                    overlap = True
                    break
            if not overlap:
                best_start = cursor
                found = True
                break
            cursor += 5 # 步进 5s
            
        if not found:
            print("  -> 警告：视频太短，不得不重叠使用")
            best_start = 0 

    return best_start, best_start + target_duration, best_score

async def main():
    if not os.path.exists(TEMP_AUDIO_DIR):
        os.makedirs(TEMP_AUDIO_DIR)

    # 1. 准备资源
    if not os.path.exists(VIDEO_FILE):
        # 查找 mp4
        files = [f for f in os.listdir('.') if f.endswith('.mp4') and 'output' not in f and 'final' not in f]
        if files:
            # 优先找 'ai数学助手'
            target = "ai数学助手开发过程.mp4"
            video_path = target if target in files else files[0]
        else:
            print("没有找到视频文件")
            return
    else:
        video_path = VIDEO_FILE
        
    print(f"使用视频: {video_path}")
    
    # 2. 视觉分析 (OCR)
    analysis_data = analyze_video(video_path, interval=2.0)
    
    # 3. 加载文案
    with open(CLIPS_FILE, 'r', encoding='utf-8') as f:
        clips_data = json.load(f)

    original_video = VideoFileClip(video_path)
    video_duration = original_video.duration
    
    final_clips = []
    used_segments = [] # (start, end)
    
    print("\n开始智能匹配...")
    
    for i, clip in enumerate(clips_data):
        text = clip['text']
        keywords = clip.get('keywords', [])
        
        # 生成语音
        audio_path = os.path.join(TEMP_AUDIO_DIR, f"visual_clip_{i}.mp3")
        await generate_tts(text, audio_path)
        audioclip = AudioFileClip(audio_path)
        duration = audioclip.duration
        
        print(f"\n片段 {i+1}: '{text[:15]}...' (时长 {duration:.1f}s)")
        print(f"  关键词: {keywords}")
        
        # 寻找最佳片段
        start, end, score = find_best_segment(analysis_data, keywords, duration, video_duration, used_segments)
        
        print(f"  -> 匹配结果: {start:.1f}s - {end:.1f}s (匹配分: {score})")
        
        used_segments.append((start, end))
        
        # 剪辑
        # MoviePy v2 check
        if hasattr(original_video, 'subclipped'):
            video_sub = original_video.subclipped(start, end)
        else:
            video_sub = original_video.subclip(start, end)
            
        # 音频处理
        if original_video.audio:
             # MoviePy v2 compatibility for volumex
             try:
                 original_audio = video_sub.audio.volumex(0.1) 
             except AttributeError:
                 if hasattr(video_sub.audio, 'multiply_volume'):
                     original_audio = video_sub.audio.multiply_volume(0.1)
                 else:
                     # fallback
                     original_audio = video_sub.audio
             
             final_audio = CompositeAudioClip([original_audio, audioclip])
        else:
             final_audio = audioclip
             
        if hasattr(video_sub, 'with_audio'):
            video_sub = video_sub.with_audio(final_audio)
        else:
            video_sub = video_sub.set_audio(final_audio)
            
        final_clips.append(video_sub)
        
    # 4. 合成
    print("\n正在合成最终视频...")
    final_video = concatenate_videoclips(final_clips)
    final_video.write_videofile(OUTPUT_FILE, codec='libx264', audio_codec='aac')
    print(f"完成！请查看: {OUTPUT_FILE}")
    
    original_video.close()
    for c in final_clips:
        c.close()

if __name__ == "__main__":
    asyncio.run(main())
