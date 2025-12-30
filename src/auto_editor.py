import os
import json
import asyncio
import edge_tts
# MoviePy v2 compatibility
try:
    from moviepy import VideoFileClip, AudioFileClip, concatenate_videoclips, CompositeAudioClip
except ImportError:
    # Fallback for older versions
    from moviepy.editor import VideoFileClip, AudioFileClip, concatenate_videoclips, CompositeAudioClip

from scenedetect import detect, ContentDetector, AdaptiveDetector

# --- 配置 ---
VIDEO_FILE = "ai数学助手开发过程.mp4"
OUTPUT_FILE = "final_video_auto.mp4"
VOICE = "zh-CN-YunxiNeural"  # 活泼的男声，适合解说
TEMP_AUDIO_DIR = "temp_audio"

# --- 文案 (可以从 clips.json 读取，但为了简单这里直接定义，方便TTS生成) ---
# 注意：这里直接硬编码文案，为了确保 TTS 生成的文件名和顺序一致
# 如果 clips.json 更新了，这里也要更新，或者写个函数读 json。
# 既然已经有了 clips.json，我们还是读 clips.json 吧。

async def generate_tts(text, output_file):
    """生成 TTS 音频"""
    communicate = edge_tts.Communicate(text, VOICE)
    await communicate.save(output_file)

def get_scenes(video_path):
    """使用 scenedetect 获取场景列表"""
    print("正在分析视频场景 (这可能需要几分钟)...")
    # 使用 AdaptiveDetector 适应屏幕录制的细微变化
    scene_list = detect(video_path, AdaptiveDetector(adaptive_threshold=3.0, min_scene_len=15))
    
    # 转换为秒 (start, end)
    scenes_in_seconds = []
    for scene in scene_list:
        start, end = scene
        scenes_in_seconds.append((start.get_seconds(), end.get_seconds()))
    
    return scenes_in_seconds

def select_best_clip(scenes, target_duration, region_start, region_end, used_segments):
    """
    在指定区域内选择最合适的片段
    :param scenes: 场景列表 [(start, end), ...]
    :param target_duration: 目标时长
    :param region_start: 区域开始时间 (秒)
    :param region_end: 区域结束时间 (秒)
    :param used_segments: 已使用的片段列表 (start, end)，避免重复
    :return: (start, end)
    """
    candidates = []
    
    # 筛选在区域内的场景
    for start, end in scenes:
        # 场景中心点在区域内即可
        mid = (start + end) / 2
        if region_start <= mid <= region_end:
            duration = end - start
            if duration >= target_duration:
                candidates.append((start, end, duration))
    
    selected_start = 0
    selected_end = 0
    
    if not candidates:
        # 如果没有合适的场景，直接在区域中间截取
        mid = (region_start + region_end) / 2
        selected_start = mid
        selected_end = mid + target_duration
    else:
        # 优先选择时长最接近的场景，或者最长的场景
        # 这里简单选择第一个满足条件的，或者中间的一个
        best_candidate = candidates[len(candidates)//2] # 选中间的场景
        start, end, _ = best_candidate
        
        # 如果场景比目标长，取前段
        selected_start = start
        selected_end = start + target_duration

    # 简单的防碰撞检查 (如果重叠，往后挪)
    for u_start, u_end in used_segments:
        if not (selected_end <= u_start or selected_start >= u_end):
            # 重叠了，简单粗暴地往后挪
            selected_start = u_end + 1
            selected_end = selected_start + target_duration
    
    return selected_start, selected_end

async def main():
    if not os.path.exists(TEMP_AUDIO_DIR):
        os.makedirs(TEMP_AUDIO_DIR)

    # 1. 读取文案
    with open("clips.json", "r", encoding="utf-8") as f:
        clips_data = json.load(f)

    # 2. 生成语音 & 获取时长
    print("正在生成 AI 配音...")
    audio_clips_info = [] # List of (audio_path, duration)
    
    for i, clip in enumerate(clips_data):
        text = clip["text"]
        audio_path = os.path.join(TEMP_AUDIO_DIR, f"clip_{i}.mp3")
        await generate_tts(text, audio_path)
        
        # 获取音频时长
        # 需要加载音频文件来获取时长
        audioclip = AudioFileClip(audio_path)
        duration = audioclip.duration
        audio_clips_info.append({
            "path": audio_path,
            "duration": duration,
            "text": text,
            "audioclip_obj": audioclip
        })
        print(f"片段 {i+1} 音频时长: {duration:.2f}s")

    # 3. 分析视频场景
    if not os.path.exists(VIDEO_FILE):
        # 尝试自动查找
        files = [f for f in os.listdir('.') if f.endswith('.mp4') and 'output' not in f]
        if files:
            video_path = files[0]
            if "ai数学助手开发过程.mp4" in files:
                video_path = "ai数学助手开发过程.mp4"
        else:
            print("找不到视频文件！")
            return
    else:
        video_path = VIDEO_FILE

    print(f"使用视频源: {video_path}")
    original_video = VideoFileClip(video_path)
    total_video_duration = original_video.duration
    
    # 获取场景分割
    # 如果视频太长，scenedetect 可能很慢。可以考虑跳过这步直接按比例切。
    # 为了"不偷懒"，我们还是尝试跑一下，如果失败就fallback。
    try:
        scenes = get_scenes(video_path)
        if not scenes:
            raise Exception("No scenes detected")
    except Exception as e:
        print(f"场景检测失败或太慢，使用均匀分割模式: {e}")
        # 伪造场景: 每5秒一个场景
        scenes = [(t, t+5) for t in range(0, int(total_video_duration), 5)]

    # 4. 智能匹配画面
    final_clips = []
    used_segments = []
    
    # 定义大致的画面分布策略
    # 我们将视频分为几个区域：开头(0-20%)，中间开发(20-80%)，结尾展示(80-100%)
    # 假设 clips_data 的顺序就是 开头 -> 过程 -> 结尾
    
    num_clips = len(clips_data)
    
    for i, info in enumerate(audio_clips_info):
        target_dur = info["duration"]
        
        # 动态计算搜索区域
        # 将视频按片段数量分段，但允许重叠
        # 例如 4 个片段：
        # 1: 0% - 30%
        # 2: 20% - 50%
        # 3: 40% - 70%
        # 4: 70% - 100%
        
        # 简单的线性映射
        relative_pos = i / num_clips
        region_start_pct = max(0, relative_pos - 0.1)
        region_end_pct = min(1.0, relative_pos + 0.4) # 稍微宽一点的范围
        
        region_start = total_video_duration * region_start_pct
        region_end = total_video_duration * region_end_pct
        
        # 特殊处理：第一个片段必须包含开头，最后一个片段必须包含结尾附近
        if i == 0:
            region_start = 0
            region_end = min(total_video_duration * 0.2, 30) # 前30秒
        elif i == num_clips - 1:
            region_start = max(0, total_video_duration - 30)
            region_end = total_video_duration

        print(f"片段 {i+1} 搜索区域: {region_start:.1f}s - {region_end:.1f}s, 目标时长: {target_dur:.1f}s")
        
        start, end = select_best_clip(scenes, target_dur, region_start, region_end, used_segments)
        
        # 确保不越界
        if end > total_video_duration:
            end = total_video_duration
            start = max(0, end - target_dur)
            
        print(f"  -> 选中: {start:.1f}s - {end:.1f}s")
        used_segments.append((start, end))
        
        # 剪辑视频
        # MoviePy v2 compatibility: subclip -> subclipped
        if hasattr(original_video, 'subclipped'):
            video_sub = original_video.subclipped(start, end)
        else:
            video_sub = original_video.subclip(start, end)
        
        # 混合音频: 原声降低音量 + TTS
        # 如果原视频有声音，保留一点背景音
        if original_video.audio:
            # MoviePy v2 compatibility for volumex
            try:
                original_audio = video_sub.audio.volumex(0.1) # 1.x style
            except AttributeError:
                # 2.x style: might be with_volume_scaled or similar, or just manually
                # Let's try multiply_volume which is common in v2
                if hasattr(video_sub.audio, 'multiply_volume'):
                    original_audio = video_sub.audio.multiply_volume(0.1)
                elif hasattr(video_sub.audio, 'with_volume_scaled'):
                    original_audio = video_sub.audio.with_volume_scaled(0.1)
                else:
                    # Fallback: assume volumex exists on fx or just skip volume reduction if hard
                    # Try importing volumex
                    from moviepy.audio.fx.multiply_volume import multiply_volume
                    original_audio = multiply_volume(video_sub.audio, 0.1)

            final_audio = CompositeAudioClip([original_audio, info["audioclip_obj"]])
        else:
            final_audio = info["audioclip_obj"]
            
        # MoviePy v2 compatibility: set_audio -> with_audio
        if hasattr(video_sub, 'with_audio'):
            video_sub = video_sub.with_audio(final_audio)
        else:
            video_sub = video_sub.set_audio(final_audio)
        
        final_clips.append(video_sub)

    # 5. 合并导出
    print("正在合并视频...")
    final_video = concatenate_videoclips(final_clips)
    final_video.write_videofile(OUTPUT_FILE, codec='libx264', audio_codec='aac')
    print(f"完成！视频已保存为: {OUTPUT_FILE}")

    # 清理
    original_video.close()
    for clip in final_clips:
        clip.close()

if __name__ == "__main__":
    asyncio.run(main())
