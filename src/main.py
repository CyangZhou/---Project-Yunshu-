import json
import os
from moviepy.editor import VideoFileClip, concatenate_videoclips

def parse_time(time_str):
    """将 HH:MM:SS 格式的时间转换为秒"""
    h, m, s = map(float, time_str.split(':'))
    return h * 3600 + m * 60 + s

def clip_video(video_path, config_path, output_path):
    """
    根据配置文件剪辑视频
    
    :param video_path: 原视频路径
    :param config_path: 剪辑配置 JSON 路径
    :param output_path: 输出视频路径
    """
    if not os.path.exists(video_path):
        print(f"错误: 找不到视频文件 {video_path}")
        return

    if not os.path.exists(config_path):
        print(f"错误: 找不到配置文件 {config_path}")
        return

    print(f"正在加载视频: {video_path}...")
    try:
        video = VideoFileClip(video_path)
    except Exception as e:
        print(f"加载视频失败: {e}")
        return

    with open(config_path, 'r', encoding='utf-8') as f:
        clips_data = json.load(f)

    sub_clips = []
    print("开始处理片段...")
    
    for i, clip_info in enumerate(clips_data):
        start_str = clip_info.get('start_time')
        end_str = clip_info.get('end_time')
        text = clip_info.get('text', f'片段_{i+1}')
        
        if not start_str or not end_str:
            print(f"跳过无效片段: {clip_info.get('id', i)}")
            continue
            
        try:
            start_time = parse_time(start_str)
            end_time = parse_time(end_str)
            
            if end_time <= start_time:
                print(f"警告: 片段 {i+1} 时间无效 ({start_str} -> {end_str})，跳过。")
                continue

            print(f"剪辑片段 {i+1}: {text[:20]}... ({start_str} -> {end_str})")
            
            # 提取片段
            sub_clip = video.subclip(start_time, end_time)
            sub_clips.append(sub_clip)
            
        except Exception as e:
            print(f"处理片段 {i+1} 时出错: {e}")

    if not sub_clips:
        print("没有有效的剪辑片段。")
        video.close()
        return

    print(f"正在合并 {len(sub_clips)} 个片段...")
    try:
        final_clip = concatenate_videoclips(sub_clips)
        final_clip.write_videofile(output_path, codec='libx264', audio_codec='aac')
        print(f"成功导出视频: {output_path}")
    except Exception as e:
        print(f"导出视频失败: {e}")
    finally:
        # 释放资源
        video.close()
        for clip in sub_clips:
            clip.close()
        if 'final_clip' in locals():
            final_clip.close()

if __name__ == "__main__":
    # 自动查找 mp4 文件
    video_files = [f for f in os.listdir('.') if f.endswith('.mp4') and 'output' not in f]
    
    if not video_files:
        print("错误: 当前目录下没有找到 MP4 视频文件。")
    else:
        # 优先选择 'ai数学助手开发过程.mp4'
        target_video = "ai数学助手开发过程.mp4"
        if target_video in video_files:
            VIDEO_FILE = target_video
        else:
            VIDEO_FILE = video_files[0]
            
        CONFIG_FILE = "clips.json"
        OUTPUT_FILE = "output_moviepy.mp4"
        
        print(f"使用视频: {VIDEO_FILE}")
        clip_video(VIDEO_FILE, CONFIG_FILE, OUTPUT_FILE)
