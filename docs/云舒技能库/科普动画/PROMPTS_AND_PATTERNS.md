# 🧪 科普动画制作指南 (Science Explainer Guide)

> “将复杂的知识，降维成会动的积木。” —— 云舒的技能卡

本文档定义了如何利用 AI (Midjourney/DALL-E) 生成 Kurzgesagt (简笔画) 风格素材，并配合 `science_explainer_engine.py` 实现自动化科普视频生产。

## 1. 视觉风格定义 (Visual Style)
 
我们要模仿的是 **"Flat Vector Motion Graphics" (扁平矢量动态图形)**。
核心特征：
*   **无边框 (Borderless)**: 色块直接拼接，没有黑色描边。
*   **几何化 (Geometric)**: 人物是圆头，树木是三角形，简化细节。
*   **高饱和 (Vibrant)**: 使用霓虹色、对比色，背景通常是深色（深蓝/深紫）以突出主体。

### 🎨 核心提示词公式 (Prompt Formula)
> **[Subject]**, flat vector illustration, minimalist, geometric shapes, vibrant colors, clean lines, no outline, in the style of Kurzgesagt, dark background --ar 1:1 --no text, realistic, shading, 3d

### 🧩 常用元素提示词 (Asset Prompts)

| 元素类型 | 英文 Prompt (Midjourney/DALL-E 3) | 中文意图 |
| :--- | :--- | :--- |
| **细胞/微观** | `flat vector illustration of a biological cell, simple green circle with nucleus, minimalist, icon style, white background --no shadow` | 生成可抠图的细胞素材 |
| **器官/人体** | `flat vector illustration of human lungs, blue and pink, simple geometric style, isolated on white background` | 生成扁平化器官图 |
| **人物** | `simple stick figure character, round head, flat vector, generic human, blue skin, minimalist, isolated on white background` | 生成通用“小蓝人” |
| **背景** | `abstract geometric background, dark purple and blue gradient, floating particles, flat style, science theme --ar 9:16` | 生成竖屏通用背景 |

---

## 2. 动画脚本结构 (Script Pattern)

科普短视频 (Shorts/Reels) 必须遵循 **"Hook -> Visual -> Answer"** 结构。

### ⏱️ 15秒脚本模板
1.  **0-3s (Hook)**:
    *   *Text*: "为什么我们打哈欠会传染？" (大号字体，Slide In)
    *   *Visual*: 一个人打哈欠的动画（张嘴 -> 闭嘴）。
    *   *Audio*: "你有没有发现，只要一个人打哈欠..."
2.  **3-10s (Explanation)**:
    *   *Text*: "镜像神经元 (Mirror Neurons)" (Pop Up)
    *   *Visual*: 大脑图片出现，大脑中一块区域发光（Pulse Effect）。
    *   *Audio*: "...你的大脑里有一种叫‘镜像神经元’的东西就会被激活！"
3.  **10-15s (Conclusion)**:
    *   *Visual*: 很多小人一起打哈欠（复制粘贴）。
    *   *Audio*: "它在模仿别人的行为，这其实是人类共情能力的体现哦！"

---

## 3. 引擎指令集 (Engine Directives)

在编写 Python 脚本调用引擎时，使用以下术语：

*   `Slide In (direction)`: 物体从屏幕外滑入（用于引入新概念）。
*   `Pop Up`: 物体从小变大弹出来（用于强调关键词）。
*   `Pulse`: 物体像心脏一样跳动（用于表示“活跃”、“危险”）。
*   `Float`: 物体上下轻微浮动（用于背景粒子，增加呼吸感）。

## 4. 实战工作流 (Workflow)

1.  **选题**: 找一个“冷知识” (Trivia)。
2.  **素材**: 用上述 Prompt 生成 3-5 张关键图（背景、主体、关键物体）。
3.  **抠图**: 使用 `rembg` 库自动去除素材背景（必须变成透明 PNG）。
4.  **合成**: 放入 `science_explainer_engine.py`，配置动画参数。
5.  **输出**: 得到 9:16 竖屏视频。

## 5. 进阶：Google Veo 3.1 视频生成 (AI Video Generation)

如果不想手写代码做动画，我们可以使用 **Google Veo 3.1** 直接生成高质量视频素材。

### 🔑 接入方式
1.  获取 Gemini API Key (Vertex AI)。
2.  运行 `src/veo_engine.py`。

### 📝 Veo 提示词指南 (Motion Prompts)
Veo 对动态描述非常敏感。不要只描述画面，要描述 **运镜 (Camera Movement)** 和 **动作 (Action)**。

#### 通用公式
> **[Subject]** doing **[Action]**, **[Camera Movement]**, **[Lighting/Style]**, **[Aspect Ratio]**

#### 示例 (Examples)

| 场景 | Veo Prompt (English) | 预期效果 |
| :--- | :--- | :--- |
| **细胞分裂** | `A cinematic microscopic shot of a biological cell dividing into two, vibrant green and blue colors, detailed texture, smooth motion, 9:16 vertical video` | 逼真的细胞分裂过程 |
| **咖啡提神** | `Animation of caffeine molecules (red triangles) blocking adenosine receptors (blue squares), flat vector style, Kurzgesagt art style, clean lines, 9:16 vertical video` | 扁平风格的原理演示 |
| **宇宙爆炸** | `A hyper-realistic supernova explosion in deep space, camera zooming out rapidly, intense light and particles, 8k resolution, 9:16 vertical video` | 震撼的宇宙空镜 |

### ⚠️ 注意事项
*   **时长**: Veo 默认生成 5-8 秒，非常适合做短视频的 B-roll (空镜)。
*   **风格**: 可以在 Prompt 中指定 `Kurzgesagt style` 或 `Flat vector style` 来保持与我们要的科普风格一致。

