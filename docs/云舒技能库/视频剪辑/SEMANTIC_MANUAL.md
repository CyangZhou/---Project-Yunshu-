# 语义感知型 AI 视频剪辑工作手册 (Semantic Video Editing Manual)

> **版本**: 2.0 (Consolidated)
> **适用场景**: 全自动将“长视频素材 + 营销文案”转换为“高质量短视频”。
> **核心哲学**: **先看后剪 (See Before Cut)** —— 拒绝盲目随机剪辑，AI 必须理解画面内容与文案的语义关联。

---

## 1. 核心工作流 (Core Workflow)

本工作流遵循 **P-P-E (Perception-Planning-Execution)** 架构：

1.  **感知 (Perception)**: 
    *   **工具**: `EasyOCR` + `OpenCV`
    *   **动作**: 逐帧扫描视频，提取画面中的文字信息（如代码、报错信息、PPT标题）。
    *   **产出**: `video_analysis.json` (时间戳 -> 文本内容的索引)。
2.  **规划 (Planning)**:
    *   **工具**: 自定义语义匹配算法 (Semantic Matcher)
    *   **动作**: 将文案关键词与 `video_analysis.json` 进行比对，寻找最佳匹配片段。
    *   **策略**: 关键词命中率优先，兼顾时间连续性与随机性。
3.  **执行 (Execution)**:
    *   **工具**: `MoviePy` (兼容 v1/v2) + `EdgeTTS`
    *   **动作**: 合成语音 -> 裁剪视频 -> 烧录字幕 -> 混入背景音乐。

---

## 2. 环境配置 (Environment Setup)

### 2.1 依赖库 (Dependencies)
请确保安装以下 Python 库（推荐使用 `pip install -r requirements.txt`）：

```text
moviepy>=1.0.3
edge-tts
easyocr
opencv-python
numpy
Pillow
requests
pandas
openpyxl
```

### 2.2 外部工具 (External Tools)
*   **FFmpeg**: 
    *   本方案推荐使用**本地 `ffmpeg.exe`** 放置于项目根目录，以避免复杂的环境变量配置。
    *   如果在 Docker 或 Linux 环境，请通过包管理器安装 (`apt install ffmpeg`)。
*   **ImageMagick** (可选): 如果使用 MoviePy 的高级文字特效可能需要，但本方案使用 PIL 绘制字幕，因此**不需要**安装 ImageMagick。

### 2.3 语音配置 (Voice Configuration)
*   **默认语音**: 本方案默认使用 `zh-CN-XiaoxiaoNeural` (女声) 或 `zh-CN-YunxiNeural` (男声)。
*   **关于“周云舒”语音**:
    *   目前 Edge TTS 官方库中暂无名为“周云舒”的专用语音模型。
    *   作为替代，建议使用 `zh-CN-XiaoxiaoNeural`，其声线温暖亲切，符合“乖巧女儿”的人设。
    *   若需定制化语音，需接入第三方 TTS 服务（如 Azure Custom Voice 或 GPT-SoVITS）并更新 `main.py` 中的 `generate_voiceover` 函数。

---

## 3. 关键代码模式 (Core Code Patterns)

### 3.1 视觉分析与缓存 (Visual Analysis with Caching)
*避免重复分析，首次运行慢，后续运行秒级完成。*

```python
import easyocr
import cv2
import json
import os

reader = easyocr.Reader(['ch_sim', 'en']) # 初始化一次

def analyze_video(video_path, interval=2.0):
    cache_file = "video_analysis.json"
    if os.path.exists(cache_file):
        with open(cache_file, 'r', encoding='utf-8') as f:
            return json.load(f)
            
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    duration = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) / fps
    
    data = []
    for sec in range(0, int(duration), int(interval)):
        cap.set(cv2.CAP_PROP_POS_MSEC, sec * 1000)
        ret, frame = cap.read()
        if ret:
            text = " ".join(reader.readtext(frame, detail=0))
            data.append({"time": sec, "text": text})
            
    with open(cache_file, 'w', encoding='utf-8') as f:
        json.dump(data, f)
    return data
```

### 3.2 MoviePy 跨版本兼容 (Version Compatibility)
*这是最关键的部分，确保代码在 MoviePy v1.x 和 v2.x 下都能运行。*

```python
try:
    from moviepy import VideoFileClip, vfx
    MOVIEPY_V2 = True
except ImportError:
    from moviepy.editor import VideoFileClip
    import moviepy.video.fx.all as vfx
    MOVIEPY_V2 = False

def set_audio_compat(clip, audio):
    return clip.with_audio(audio) if MOVIEPY_V2 else clip.set_audio(audio)

def subclip_compat(clip, start, end):
    return clip.subclipped(start, end) if MOVIEPY_V2 else clip.subclip(start, end)

def fl_image_compat(clip, func):
    # v2 uses image_transform, v1 uses fl_image
    return clip.image_transform(func) if MOVIEPY_V2 else clip.fl_image(func)

def loop_audio_compat(audio, duration):
    if MOVIEPY_V2:
         return audio.with_effects([vfx.Loop(duration=duration)])
    else:
         from moviepy.audio.fx.all import audio_loop
         return audio_loop(audio, duration=duration)

def volume_compat(audio, vol):
    return audio.with_volume_scaled(vol) if MOVIEPY_V2 else audio.volumex(vol)
```

---

## 4. 脚本管理 (Script Management)

支持两种格式的脚本输入：

### 4.1 Excel (推荐)
使用 `clips_v2.xlsx`，适合非技术人员。
*   **列**: `text` (文案), `keywords` (匹配关键词, 逗号分隔), `min_duration` (最少持续秒数)。
*   **读取**:
    ```python
    import pandas as pd
    df = pd.read_excel("clips_v2.xlsx")
    clips_config = df.to_dict('records')
    # 处理 keywords 字符串转列表
    for c in clips_config:
        if isinstance(c['keywords'], str):
            c['keywords'] = c['keywords'].split(',')
    ```

### 4.2 JSON (开发者用)
使用 `clips.json`，适合程序生成。
```json
[
  {
    "text": "文案内容",
    "keywords": ["关键词1", "关键词2"],
    "min_duration": 5.0
  }
]
```

---

## 5. 操作指南 (Operation Guide)

1.  **准备素材**:
    *   将视频命名为 `video.mp4` (或在代码中修改 `VIDEO_FILE`)。
    *   (可选) 准备背景音乐 `background_music.mp3`。
2.  **编写脚本**:
    *   编辑 `clips_v2.xlsx` 或 `clips.json`。
    *   确保 `keywords` 里的词在视频画面中确实出现过（如 PPT 标题、代码关键字）。
3.  **运行程序**:
    *   运行主程序 (例如 `final_producer.py`)。
    *   首次运行会进行 OCR 分析（较慢），后续运行将读取缓存（秒级）。
4.  **查看结果**:
    *   输出文件通常为 `final_product_v2.mp4`。

---

## 6. 常见问题 (Troubleshooting)

*   **Q: 报错 `AttributeError: 'VideoFileClip' object has no attribute 'subclip'`**
    *   **A**: 这是 MoviePy v2.0 的 API 变动。请务必使用 **3.2 节** 中的 `subclip_compat` 兼容函数，不要直接调用 `.subclip()`。
*   **Q: 报错 `No module named 'moviepy.editor'`**
    *   **A**: 说明安装的是 MoviePy v2.0+。请使用 `from moviepy import ...` 而不是 `from moviepy.editor import ...`，参考 **3.2 节** 的导入代码。
*   **Q: OCR 识别不准确？**
    *   **A**: 尝试调整 `analyze_video` 中的 `interval` 参数（例如从 2.0 改为 1.0）以获得更密集的采样。
