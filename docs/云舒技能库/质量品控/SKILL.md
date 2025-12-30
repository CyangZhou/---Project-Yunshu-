# Video Quality Assurance Skill (视频质量自检技能)

## 1. 核心理念 (Core Philosophy)
"先自检，后交付"。任何生成的视频文件必须经过自动化质量验证，确保：
1. **文件完整性**：文件可打开，元数据完整。
2. **流媒体合规**：视频流无解码错误。
3. **视觉正常**：无花屏、绿屏、黑屏等渲染异常。
4. **音频正常**：音轨存在且无爆音/静音。

## 2. 自动化检测流程 (Automated Validation Workflow)

在视频生成脚本 (`viral_video_engine.py`) 末尾必须调用 `validate_video` 函数。

### 2.1 基础文件检查
- 检查文件是否存在。
- 检查文件大小是否合理 (> 1MB)。

### 2.2 FFmpeg 流扫描
使用 `ffmpeg -v error -i output.mp4 -f null -` 命令全量扫描视频流。
- **正常**：输出为空。
- **异常**：输出包含 `Error`, `Invalid data`, `corrupt` 等关键词。

### 2.3 关键帧抽样 (可选)
使用 OpenCV 读取视频的开头、中间、结尾帧，确保能正常读取且非纯色（除非预期）。

## 3. 常见问题与修复 (Troubleshooting)

| 问题现象 | 常见原因 | 解决方案 |
| :--- | :--- | :--- |
| **花屏/绿屏** | 像素格式不匹配 (Float vs Uint8) | 确保所有 MoviePy Filter 返回 `np.uint8` 类型；导出时指定 `-pix_fmt yuv420p`。 |
| **无法播放** | 编码容器损坏 / 缺少 Moov Atom | 使用 `libx264` 编码；确保 `write_videofile` 完整执行完毕。 |
| **音画不同步** | 帧率不统一 | 强制指定 `fps=30`；在合成前统一素材帧率。 |
| **黑屏** | Alpha 通道错误 | 叠加图层时确保 Alpha Mask 正确；背景层不应有透明度。 |

## 4. 代码规范 (Code Standard)

所有视频处理函数必须包含以下类型安全检查：

```python
import numpy as np

def safe_filter(img):
    # 处理逻辑...
    
    # 强制类型转换，防止花屏
    if img.dtype != np.uint8:
        img = (np.clip(img, 0, 1) * 255).astype(np.uint8) if img.max() <= 1.0 else img.astype(np.uint8)
    return img
```
