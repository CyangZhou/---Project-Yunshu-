# 爆款短视频自动化生产技能 (Viral Video Production Skill)

> **版本**: 4.0 (Relaxed & Enhanced)
> **类型**: 核心生产力技能
> **描述**: 结合抖音爆款逻辑、语义分析与多模态增强技术，全自动生产高完读率的技术营销短视频。

---

## 1. 核心能力 (Core Capabilities)

### 1.1 逆向时间轴叙事 (Reverse Timeline Storytelling)
*   **痛点**: 传统录屏视频枯燥、平铺直叙。
*   **解法**: 打破线性时间，优先展示“高潮时刻”（成品展示、报错修复），再回溯过程。
*   **实现**: 在脚本中支持 `preferred_start` 参数，强制画面跳转至指定精彩瞬间。

### 1.2 语义锚点匹配 (Semantic Anchor Matching)
*   **痛点**: 解说词与画面“两张皮”，观众不知道在讲哪里。
*   **解法**: 
    *   **视觉感知**: 使用 EasyOCR 每 0.5s 扫描画面，建立 `video_analysis.json` 索引。
    *   **智能去重**: 引入画面相似度检测，跳过静止帧，加速 500%。
    *   **关键词加权**: 优先匹配脚本中定义的 `keywords`，确保说到“报错”时画面必有红字。

### 1.3 爆款文案结构 (Viral Script Formula)
遵循 **Hook-Process-Payoff-CTA** 模型：
1.  **Hook (3s)**: 反常识/冲突提问（"不会写代码也能做软件？"）。
2.  **Process (15s)**: 极速展示过程，强调“简单”、“自动化”。
3.  **Payoff (10s)**: 展示惊艳成品，提供爽感。
4.  **CTA (3s)**: 价值升华，引导关注。

### 1.4 听觉增强 (Audio-Driven Cutting) - *Updated v4.0*
*   **痛点**: 
    *   旧版痛点：TTS 语速过快，剪辑过于紧凑，观众产生焦虑感。
    *   新版优化：追求**“从容不迫”**的专业讲解节奏。
*   **解法**: 
    *   **舒缓语速**: 将 TTS 语速调整为 **-10%**，更接近真人讲师的稳重感。
    *   **保留留白**: 移除激进的静音切除逻辑，保留句间自然停顿，给予观众思考时间。
    *   **风格化 BGM**: 自动下载 Lo-Fi/Tech House 风格背景乐 (如 "Algorithms" by Chad Crouch)，营造沉浸式学习氛围。

### 1.5 视觉增强 (Visual Enhancement) - *Updated v4.0*
*   **痛点**: 
    *   手机观看录屏时字体太小。
    *   字幕在复杂背景下看不清。
*   **解法**: 
    *   **语义变焦**: 检测到“仔细”、“看”、“细节”、“重点”等关键词时，自动对画面进行 1.3x 裁剪放大。
    *   **高亮字幕**: 
        *   **关键词**: 自动识别关键词（如 "Trae", "AI"）并渲染为**金黄色**。
        *   **背景框**: 为字幕添加**半透明黑色背景框**，确保在任何画面背景下均清晰可见。
    *   **效果**: 模拟摄影师推镜头效果，动态引导观众视线，且字幕阅读体验极佳。

### 1.6 多模态混剪 (Multi-Modal Montage)
*   **痛点**: 纯视频内容形式单一，缺乏包装感，片段衔接生硬。
*   **解法**: 
    *   **平滑转场**: 视频片段间自动应用 **1.0s Crossfade (淡入淡出)** 效果，消除跳跃感，提升高级感。
    *   **自动封面**: 使用 PIL 自动生成黑金风格封面图，包含标题与 Logo。
    *   **表情包植入**: 支持通过 `add_meme_overlay` 接口在特定时刻插入表情包。

---

## 2. 项目结构 (Project Structure)

本技能依赖以下标准目录结构：

```text
/
├── src/                    # 核心代码
│   ├── viral_video_engine.py   # 主程序 (v4.0: 降速、字幕框、长转场)
│   ├── download_music.py       # BGM 下载工具 (Lo-Fi/Tech 风格)
│   └── transcribe.py           # Whisper 语音转录
├── config/                 # 配置文件
│   ├── clips_viral.json        # 爆款脚本配置
│   └── clips_v2.xlsx           # Excel 版本脚本
├── resources/              # 媒体素材
│   ├── video.mp4               # 原始录屏
│   ├── background_music.mp3    # 背景音乐 (Chad Crouch - Algorithms)
│   └── ffmpeg.exe              # 本地 FFmpeg
├── output/                 # 产出物
│   ├── final_product_v5.mp4    # 最终成品 (v5.0: 从容风格)
│   └── cover_generated.jpg     # 自动生成的封面
├── data/                   # 中间数据
│   ├── video_analysis.json     # OCR 索引缓存
│   └── ocr_dump.txt            # 调试日志
└── docs/                   # 文档
    └── SEMANTIC_VIDEO_EDITING_MANUAL.md
```

---

## 3. 使用指南 (Usage Guide)

### 3.1 快速启动
```bash
cd src
python viral_video_engine.py
```

### 3.2 脚本编写规范 (JSON)
编辑 `config/clips_viral.json`：

```json
[
  {
    "text": "大家仔细看这个报错...",    // 触发“仔细看”自动变焦
    "keywords": ["Error", "Failed"], // 画面匹配权重 + 字幕自动高亮(金色)
    "preferred_start": 0,            // (可选) 强制画面开始时间
    "min_duration": 4.0              // 最短持续时间
  }
]
```

---

## 4. 维护与迭代

*   **新增语音**: 修改 `src/viral_video_engine.py` 中的 `generate_voiceover` 函数。
*   **调整 BGM**: 修改 `src/download_music.py` 中的 URL (推荐 Free Music Archive 的 Lo-Fi/Tech 分类)。
*   **优化 OCR**: 若识别太慢，调整 `analyze_video` 中的 `interval` 或相似度阈值。
*   **字幕样式**: 修改 `add_subtitle` 中的 `highlight_color` (默认 `#FFD700` 金色)。
