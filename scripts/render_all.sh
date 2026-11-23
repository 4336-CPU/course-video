#!/bin/zsh
# 渲染全片并合上配音：render.py 渲画面 → ffmpeg 接上 voice.wav（按 timings.js 的 END 截断）
# 放在 lessonN/ 目录下：
#   VKF_ENGINE=/path/to/vibe-knowledge-film/engine OUT=../lesson1_full.mp4 ./render_all.sh
# 可选：PY 指定 Python（默认 python3），JOBS 指定并行数（默认 6）
cd "$(dirname "$0")"
: "${VKF_ENGINE:?先设置 VKF_ENGINE 为 vibe-knowledge-film/engine 的路径}"
PY="${PY:-python3}"; JOBS="${JOBS:-6}"; OUT="${OUT:-renders/full.mp4}"
"$PY" "$VKF_ENGINE/render.py" . --jobs "$JOBS" || exit 1
DUR=$("$PY" -c "import re,json;print(json.loads(re.search(r'window.TIM = (.*?);',open('timings.js').read()).group(1))['END'])")
# 不要用 apad + -shortest，进程会停不下来；用 -t 截断
ffmpeg -v error -y -i renders/raw.mp4 -i voice.wav -map 0:v -map 1:a -c:v copy -c:a aac -b:a 192k -t "$DUR" -movflags +faststart "$OUT" || exit 1
echo "完成：$OUT，$DUR 秒"
