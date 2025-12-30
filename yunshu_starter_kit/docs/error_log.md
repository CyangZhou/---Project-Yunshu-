# 错误记录本 (The "Small Notebook")

此文档用于记录开发过程中遇到的错误、原因分析及解决方案，以防止重复犯错。

| 日期 | 错误描述 | 原因分析 | 解决方案 | 预防措施 |
| :--- | :--- | :--- | :--- | :--- |
| 2025-12-29 | AttributeError: 'VideoFileClip' object has no attribute 'subclip' | MoviePy v2.0 API 变更，不再支持 .subclip() 方法 | 编写兼容层函数 `subclip_compat`，根据版本动态调用 `.subclipped()` 或 `.subclip()` | 在 `SEMANTIC_VIDEO_EDITING_MANUAL.md` 中记录兼容性规范，后续开发强制使用兼容层。 |
| 2025-12-29 | WinError 2: The system cannot find the file specified (FFmpeg) | 系统环境变量未配置 FFmpeg，且 ImageIO 自动下载失败 | 将本地 `ffmpeg.exe` 放置于项目根目录，并在代码中手动指定路径或通过兼容层处理 | 优先使用本地 FFmpeg 依赖，不依赖系统环境。 |
| 2025-12-29 | BGM 文件无法播放 (内容为 HTML) | 直接使用 requests 下载链接时，链接重定向或需要 Cookie，导致下载了网页而非音频 | 更换为可靠的直接下载链接 (SoundHelix)，并增加文件头检查机制 | 下载资源后必须验证文件有效性 (如大小、魔数)。 |
