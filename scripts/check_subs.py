"""字幕宽度检查：放在 lessonN/ 目录下运行，读 lines.json。
按 common.js 里字幕组件同样的切法切句（句号、问号后另起一条，单条超过 24 字就切），
估算每条宽度（汉字算 1，英文、数字算 0.55），超过 LIM 的会出画。切法或字号改了要同步改这里。"""
import json, re
LIM = 34
bad = []
for ln in json.load(open("lines.json", encoding="utf-8")):
    parts, cur = [], ""
    for m in re.finditer(r"[^，。；：？]+[，。；：？]?", ln["sub"]):
        if cur and (re.search(r"[。？]$", cur) or len(cur + m.group()) > 24): parts.append(cur); cur = m.group()
        else: cur += m.group()
    if cur: parts.append(cur)
    for p in parts:
        w = sum(1 if ord(c) > 0x2E80 else .55 for c in p)
        if w > LIM: bad.append((ln["id"], round(w, 1), p))
print(bad or "字幕都在屏幕内")
