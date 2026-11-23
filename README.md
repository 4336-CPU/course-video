# course-video

[中文](#中文) | [English](#english)

## 中文

一个 Agent skill：把一节课或一个技术主题做成暗场科普风的讲解视频。流程是回看前几集 → 定内容方案 → 写旁白稿 → 配音 → 收集真实素材 → 用代码逐帧画动画 → 渲染出片。

画面不用视频生成模型，全部用 Canvas 代码逐帧画，数字和文字可以精确控制。资讯、论文、产品用真实网页截图和 logo，不用 AI 生成。

这套规矩来自一门系列课程连续做好几集视频的过程，每一条都对应过一次返工。

### 内容

- `SKILL.md`：完整流程和两道确认闸门（旁白定稿前、渲染前都要等用户确认）。
- `references/narration_rules.md`：旁白怎么写，包括结构、句子、例子、严谨、交稿前自查清单。
- `references/visual_rules.md`：画面、素材、镜头、排版、渲染，以及只渲片段再拼接的做法。
- `references/voice_rules.md`：配音的读法、语气、语速、停顿，逐字时间戳的坑。
- `scripts/`：可以复制进工程目录的脚本。
  - `make_lines.py`：旁白表格转成字幕和读法。
  - `voice.py`：Edge TTS 草稿配音或 MiniMax 正式配音，生成时间轴。
  - `capture.py`：网页截图并记录高亮位置。
  - `check_subs.py`：检查字幕会不会出画。
  - `render_all.sh`：渲染并合上配音。

### 安装

把 `course-video` 文件夹放进 Agent 的 skill 目录，例如 `~/.claude/skills/course-video`。

依赖：

- 渲染引擎 [vibe-knowledge-film](https://github.com/HeyChengC/vibe-knowledge-film)（MIT）
- Python 3.10+：`pip install playwright numpy imageio-ffmpeg edge-tts`，本机装好 Chrome 和 ffmpeg
- 正式配音可选 MiniMax TTS，Key 用环境变量 `MINIMAX_API_KEY` 传入
- 推荐装上的写作 skill：pyramid-principle、[technical-writing](https://github.com/luoling8192/technical-writing)、[plain-writing](https://github.com/docwriter-org/plain-writing-skill)、[coherent-writing](https://github.com/ericmjl/skills)、humanizer

### 致谢

镜头和画面设计借鉴了 video-talkcraft、NousResearch/hermes-agent 的 manim-video、yudong-94/storytelling-viz 的做法，只借思路，没有使用它们的代码。

## English

An agent skill for turning a lesson or a technical topic into a dark-themed explainer video. The workflow covers reviewing earlier episodes, planning content, writing narration, voice-over, collecting real source material, drawing frame-by-frame animation in code, and rendering.

Visuals are drawn with Canvas code instead of video generation models, so numbers and text stay exact. News, papers and products are shown with real web screenshots and logos, not AI-generated images.

The rules come from producing several episodes of a course series. Each rule exists because something had to be redone. The skill text is written in Chinese.

### Contents

- `SKILL.md`: the full workflow, with two checkpoints where the agent waits for the user (before narration is final and before rendering).
- `references/narration_rules.md`: how to write narration, with a pre-submission checklist.
- `references/visual_rules.md`: visuals, source material, camera, layout, rendering, and re-rendering only changed clips.
- `references/voice_rules.md`: TTS pronunciation, tone, speed, pauses, and word-timestamp pitfalls.
- `scripts/`: helper scripts to copy into a project (narration to lines, TTS and timeline, web capture, subtitle width check, render).

### Install

Put the `course-video` folder in your agent's skill directory, for example `~/.claude/skills/course-video`.

Requirements: [vibe-knowledge-film](https://github.com/HeyChengC/vibe-knowledge-film) (MIT) as the render engine; Python 3.10+ with `playwright numpy imageio-ffmpeg edge-tts`; Chrome and ffmpeg. MiniMax TTS is optional and reads its key from `MINIMAX_API_KEY`.

### Credits

Camera and visual design ideas were borrowed from video-talkcraft, the manim-video skill in NousResearch/hermes-agent, and yudong-94/storytelling-viz. Only the ideas were used, not their code.

## License

[MIT](LICENSE)
