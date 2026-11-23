---
name: course-video
description: >-
  把一节课或一个技术主题做成暗场科普风的讲解视频：回看前几集 → 定内容方案 → 写旁白稿 → 配音 → 收集真实素材
  → 用代码逐帧画动画 → 渲染出片。用户说「做视频」「做课程视频」「下一集视频」「写旁白稿」「改旁白」「配音」
  「渲染视频」「第 N 课视频」，或者要把一份提纲、一篇文章做成讲解视频时使用。
  不用于 Seedance、可灵这类视频生成模型出片，也不用于海报、封面等静态物料。
---

# 讲解视频制作流程

这套流程来自一门系列课程连续做了好几集讲解视频的过程，里面每一条规矩都对应过一次返工。开工前读完三个参考文件：

- `references/narration_rules.md`：旁白怎么写。
- `references/visual_rules.md`：画面、素材、渲染的细则和踩过的坑。
- `references/voice_rules.md`：配音的读法、语气、语速、停顿，以及只改一句时怎么替换。

`scripts/` 里是可以直接复制进工程目录的脚本，用法写在各自文件开头。

## 依赖

- 渲染引擎：[vibe-knowledge-film](https://github.com/HeyChengC/vibe-knowledge-film)（MIT）。Canvas 按时间 t 逐帧算画面，Playwright 驱动本机 Chrome 截帧，ffmpeg 合成。`engine/render.py` 支持 `--stills`、`--sheet`、`--motion`、`--clip`、`--jobs`。
- Python 3.10+：`playwright`、`numpy`、`imageio-ffmpeg`、`edge-tts`；本机装好 Chrome 和 ffmpeg。
- 正式配音可选 MiniMax TTS（付费），Key 用环境变量 `MINIMAX_API_KEY` 传入。
- 写作 skill（推荐装上，旁白每一版都要调用）：
  - `pyramid-principle`（stefan-jansen/claude-code-toolkit，MIT）：结论先行。
  - `technical-writing`（[luoling8192/technical-writing](https://github.com/luoling8192/technical-writing)，MIT）：删过场句、空评价词。
  - `plain-writing`（[docwriter-org/plain-writing-skill](https://github.com/docwriter-org/plain-writing-skill)，MIT）：降低信息密度。
  - `coherent-writing`（[ericmjl/skills](https://github.com/ericmjl/skills)，MIT）：查话题跳跃、因果断开、前后重复。
  - `humanizer`：去 AI 腔，口语化。

## 工程目录约定

```
video/
  course_continuity.md     # 各集衔接记录：结论、例子、数字、留给后面的素材、视觉元素
  lessonN_narration.md     # 第 N 集旁白稿（内容方案 + 逐句表格 + 出处与核实）
  make_lines.py            # 旁白表格 → lessonN/lines.json（sub 字幕 / say 读法）
  lessonN/
    index.html             # 加载引擎、timings.js、logos.js、common.js、s1.js…sK.js、film.js
    common.js              # 共用组件：字幕、地面网格、截图面板、机位 CAM
    sK.js                  # 第 K 节画面，挂到 window.CH.sK
    film.js                # 总时间轴、每节机位和转场
    voice.py  lines.json  timings.js  voice.wav  pronunciation.json
    capture.py  check_subs.py  render_all.sh
    assets/（img、logos、shots）  review/  renders/
```

新一集复制上一集的目录结构来改，`common.js` 里的组件直接复用。

## 两道闸门（每次都停下来等用户确认）

1. **每一版旁白稿之后**：初稿、每次修改稿、为补时长加的新句子，都先发给用户，等他明确说「可以」「定稿」再往下走。不边改稿边配音、边做画面。
2. **每次渲染之前**：全片渲染、`--clip` 片段渲染、改完后的重渲都算。先给用户看截帧拼图（`--sheet`、`--stills` 只是截图，不算渲染），说明这次画面改了什么、预计渲多久，等用户说「渲吧」再开始。

用户某一次说「直接渲染，不用给我看拼图」，只对那一次有效，下一次照样要问。闸门之外的事直接做：查资料、实跑实验拿数据、截图、写动画代码、截帧自查。

## 阶段零：回看已完成的几集（每次定内容前必须做）

1. **读前面每一集的定稿旁白** `video/lessonK_narration.md`（K < N），包括画面列和文末「出处与核实」。记下每集的结论、用过的例子和数字、结尾预告了什么。
2. **看前面每一集的成片。** 模型看不了连续播放，用抽帧的办法看：在工程目录跑 `render.py <工程> --sheet 24`，或者用 ffmpeg 每 10 秒抽一帧拼成一张图，再对照 `lines.json` 和 `timings.js`。要看的是用了哪些视觉元素、颜色代表什么、片尾卡怎么写。新一集沿用，不另起一套。
3. **读 `video/course_continuity.md`。** 第一集做完时创建它。
4. **参考课程规划或大纲。** 规划只告诉你这一集大致讲什么，最终结构按讲清楚、讲成体系来定。

## 阶段一：定内容方案

内容方案写在旁白稿开头，和初稿一起过闸门 1：

- **一句话结论**：这一集讲完，观众应该记住的那一句。
- **结构**：分几节，每节结论各一句。各节是递进关系，前一节的结论是后一节的前提，不是并列堆起来的话题。
- **承上**：上一集结尾预告了什么，本集开头用一两句接住，然后直接给本集结论。
- **贯穿例子**：全系列用同一个任务做例子（比如同一份数据、同一个评分脚本），数字和前几集对得上。前几集留给本集的素材要用上。
- **启下**：结尾预告下一集，和课程规划一致。
- **术语表**：沿用前几集定下的叫法，同一个概念不换名字。
- **需要的真实证据**：要实跑的实验、要引用的原文、要截图的页面、要放 logo 的产品。

每集定稿后更新 `course_continuity.md`：本集结论、各节结论、用过的例子和数字（带出处）、成绩、留给后面的素材、结尾预告、新增的视觉元素。

## 阶段二：写旁白稿（闸门 1）

动笔前读 `references/narration_rules.md`。

1. **格式**：文件开头写内容方案，然后每节一张表 `| # | 旁白 | 画面 |`，编号 `N-节-句`（插入的句子在末尾加字母，如 `1-2-3a`），一行一段配音。旁白列保留阿拉伯数字（字幕用），画面列写这句话在屏上具体发生什么。文末写「出处与核实」，每个数字对应一个记录文件或原文。
2. **先做教学设计**：写出「看完能做到什么」2 到 4 条，按 Gagné 九步里适合视频的几步排顺序。
3. **每一版都主动大改润色，不等用户提醒。** 用 Skill 工具真的调用这五个 skill，按顺序：pyramid-principle → technical-writing → plain-writing → coherent-writing → humanizer。只读过 skill 文件不算调用。humanizer 那一遍要几乎每句重写成讲课时说的话。交稿时写明各 skill 改了什么。
4. **交稿前自查**：按 `narration_rules.md` 末尾的清单逐条过，语序单独逐句查一遍。用户指出一句，就把全稿同类句子都改掉。
5. **交稿**：把旁白全文贴在回复里（只贴旁白，不贴画面列），附文件路径；标出新增和改动的句子；给句数、字数和估计时长（先只合成配音量时长最准）。需要用户拍板的地方单独列出。然后停下等确认。
6. **用户自己在文件里改过的句子**直接用他的版本，不覆盖、不再润色。任何导出文件（字幕、配音稿）被用户改过，先合回旁白稿再重新导出。
7. **时长不够时**，先回到课程规划，找本集规划过、稿子还没讲的知识点；再去同类课程、教学长文、科普视频里找讲同一主题的做法，用到自己的实验数据上。给几个选项，写明每条回答本集哪个问题、加多少秒，用户选了再写。不靠加停顿、放慢语速凑时长，也不把已有例子换个说法再讲一遍。

## 阶段三：配音和时间轴

动笔前读 `references/voice_rules.md`。

1. `scripts/make_lines.py N` 把定稿表格转成 `lessonN/lines.json`，每句有 `sub`（字幕）和 `say`（读法）。数字、百分比、版本号转成汉字读法，书名号去掉，文件名的点和下划线不念。跑完确认读法里不剩阿拉伯数字。
2. `scripts/voice.py edge`：内容定稿前一律用免费的 Edge TTS 出草稿配音，同时拿逐词时间戳，生成 `timings.js` 和 `voice.wav`。
3. `scripts/voice.py minimax`：内容全部定稿、用户同意付费后再出正式配音。用现成音色，不复刻任何人的声音。
4. 只改一句或只加几句时，只合成这几句，见 `voice_rules.md`。

## 阶段四：素材和画面

动笔前读 `references/visual_rules.md`。核心几条：

- 要像视频，不像 PPT：句子里说到什么，屏上就发生什么。
- 提到资讯、论文、榜单，放真实网页截图（`scripts/capture.py`）；提到产品，放真实 logo。不用 AI 生成这类素材。拿不到的，把网址发给用户请他截。
- 画面上不放来源角标和「示意」标签，出处统一放片尾资料卡。
- 不用机器人这类比喻形象。讲一个结构，就把它一层一层画出来。

## 阶段五：截帧自查，然后渲染（闸门 2）

1. 先自己看：`--sheet 16` 看全片，`--motion a b` 看转场和动作，`--stills` 看关键句。查数字对不对、字有没有被遮、高亮框和原文对不对齐、动作是不是在念到那个词时发生。
2. 把拼图和改动说明给用户，等他说可以渲。
3. 渲染用 `scripts/render_all.sh`。长任务放后台，告诉用户在跑什么、大概多久；用户问进度时查进程和分段文件大小，如实回答。
4. 出片后再查一遍：时长和音轨、整片拼图、转场处的 motion 图。模型听不到声音、看不了连续播放，交付时说清楚哪些没检查到。
5. 只改了几处时只渲片段再拼接，做法见 `visual_rules.md`。

## 一直要守的规矩

- **科学严谨在有趣之上，但不钻牛角尖。** 数字只用实跑记录或核对过的原文。发现定稿里有事实错误，先告诉用户、给替换句，等他确认。
- **博采众长。** 可以去 GitHub 找做视频、写技术文的 skill 和包借鉴，借之前先看许可证：没有许可证或只允许非商业使用的，只借做法，不用代码和素材。MIT 仓库里的示例片、风格图、BGM 也不拿来发布。
- **Key 不进脚本、不进文档。** 用环境变量或权限 600 的本地文件。用户把 Key 贴进对话时，提醒他用完去控制台重置。
- **如实汇报。** 没检查到的、没跑通的、后台任务失败的，都直说。
- **改稿、改画面时把本 skill 和三个参考文件的规矩全部过一遍**，不只改用户点到的地方。
