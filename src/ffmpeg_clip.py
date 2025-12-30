import ffmpeg
import json
import os
import sys

def parse_time(time_str):
    """将 HH:MM:SS 格式转换为秒"""
    try:
        parts = list(map(float, time_str.split(':')))
        if len(parts) == 3:
            return parts[0] * 3600 + parts[1] * 60 + parts[2]
        elif len(parts) == 2:
            return parts[0] * 60 + parts[1]
        else:
            return parts[0]
    except ValueError:
        return 0

def clip_video_ffmpeg(video_path, config_path, output_path):
    if not os.path.exists(video_path):
        print(f"错误: 找不到视频文件 {video_path}")
        return
    if not os.path.exists(config_path):
        print(f"错误: 找不到配置文件 {config_path}")
        return

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            clips_data = json.load(f)
    except json.JSONDecodeError:
        print(f"错误: 配置文件 {config_path} 格式不正确")
        return

    # 探测视频信息，检查是否有音频流
    try:
        probe = ffmpeg.probe(video_path)
        has_audio = any(stream['codec_type'] == 'audio' for stream in probe['streams'])
    except ffmpeg.Error as e:
        print("错误: 无法读取视频文件，请确保系统已安装 ffmpeg 并添加到环境变量。")
        print("FFmpeg 错误信息:", e.stderr.decode('utf8') if e.stderr else str(e))
        return

    input_stream = ffmpeg.input(video_path)
    
    streams = []
    print(f"正在处理视频: {video_path}")
    print(f"音频流检测: {'有' if has_audio else '无'}")
    
    valid_clips = 0
    for i, clip in enumerate(clips_data):
        start_str = clip.get('start_time')
        end_str = clip.get('end_time')
        text = clip.get('text', f'片段_{i+1}')
        
        if not start_str or not end_str:
            continue
            
        start_sec = parse_time(start_str)
        end_sec = parse_time(end_str)
        
        if end_sec <= start_sec:
            print(f"警告: 片段 {i+1} 结束时间小于开始时间，跳过。")
            continue

        print(f"准备剪辑片段 {i+1}: {text[:30]}... ({start_str} -> {end_str})")
        
        # 视频剪辑
        v = input_stream.video.trim(start=start_sec, end=end_sec).setpts('PTS-STARTPTS')
        streams.append(v)
        
        # 音频剪辑 (如果有音频)
        if has_audio:
            a = input_stream.audio.filter_('atrim', start=start_sec, end=end_sec).filter_('asetpts', 'PTS-STARTPTS')
            streams.append(a)
        
        valid_clips += 1

    if valid_clips == 0:
        print("没有有效的剪辑片段。")
        return

    print(f"开始合并 {valid_clips} 个片段...")
    
    try:
        # 合并流
        # v=1 表示输出一个视频流，a=1 表示输出一个音频流 (如果原视频有音频)
        if has_audio:
            joined = ffmpeg.concat(*streams, v=1, a=1).node
            out = ffmpeg.output(joined[0], joined[1], output_path)
        else:
            joined = ffmpeg.concat(*streams, v=1, a=0).node
            out = ffmpeg.output(joined[0], output_path)

        # 运行 ffmpeg
        out.run(overwrite_output=True)
        print(f"成功！视频已导出至: {output_path}")
        
    except ffmpeg.Error as e:
        print("导出失败。FFmpeg 错误输出:")
        print(e.stderr.decode('utf8') if e.stderr else str(e))

if __name__ == "__main__":
    # 查找目录下的 mp4 文件
    video_files = [f for f in os.listdir('.') if f.endswith('.mp4') and 'output' not in f]
    
    if not video_files:
        print("当前目录下没有找到 MP4 视频文件。")
        sys.exit(1)
        
    # 优先选择 'ai数学助手开发过程.mp4'，否则选第一个
    target_video = "ai数学助手开发过程.mp4"
    if target_video in video_files:
        VIDEO_FILE = target_video
    else:
        VIDEO_FILE = video_files[0]
        
    CONFIG_FILE = "clips.json"
    OUTPUT_FILE = "final_video.mp4"
    
    clip_video_ffmpeg(VIDEO_FILE, CONFIG_FILE, OUTPUT_FILE)
