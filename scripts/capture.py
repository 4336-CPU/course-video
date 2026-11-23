"""网页截图：滚到关键句附近，截当前视口（1440×1100，2 倍像素），记录关键句在截图里的位置，供画面画高亮框。
放在 lessonN/ 目录下：
  python capture.py            # 截 JOBS 里的全部
  python capture.py 名字 ...   # 只截这几张
输出 assets/img/<名字>.png，位置写进 assets/img/meta.json：{名字: {w, h, hl: [[x, y, w, h], ...]}}。
需要 playwright 和本机 Chrome。截不到的页面（人机验证等）把网址交给用户手动截。"""
import json, sys
from pathlib import Path
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
IMG = HERE / "assets/img"
JOBS = {   # 页面 → [(输出名, 关键句列表（第一句用来定位，其余只高亮）, 关键句在视口里的目标 y)]
    "https://www.anthropic.com/research/demystifying-evals-for-ai-agents": [
        ("an_graders", ["Agent evaluations typically combine three types of graders"], 60)],
}
ONLY = set(sys.argv[1:])
# 隐藏吸顶导航、Cookie 条这类固定元素，展开折叠内容
CLEAN = """() => { for (const e of document.querySelectorAll('body *')) { const s = getComputedStyle(e);
  if (s.position === 'fixed' || (s.position === 'sticky' && !/^(TH|TD|TR|THEAD)$/.test(e.tagName))) e.style.display = 'none'; }
  for (const d of document.querySelectorAll('details')) d.open = true; }"""
FIND = """(k) => { const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT); let n;
  while ((n = w.nextNode())) { const i = n.textContent.indexOf(k); if (i < 0) continue;
    const r = document.createRange(); r.setStart(n, i); r.setEnd(n, i + k.length); const b = r.getBoundingClientRect();
    if (b.width > 0) return [b.x, b.y, b.width, b.height]; }
  for (const e of document.querySelectorAll('td,p,li,span')) { if (e.innerText && e.innerText.includes(k) && e.children.length < 8) {
    const b = e.getBoundingClientRect(); if (b.width > 0) return [b.x, b.y, b.width, b.height]; } }
  return null; }"""


def main():
    IMG.mkdir(parents=True, exist_ok=True)
    mp = IMG / "meta.json"
    meta = json.loads(mp.read_text()) if mp.exists() else {}
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome")
        pg = b.new_page(viewport={"width": 1440, "height": 1100}, device_scale_factor=2)
        for url, jobs in JOBS.items():
            if ONLY and not any(name in ONLY for name, _, _ in jobs): continue
            pg.goto(url, wait_until="domcontentloaded", timeout=90000); pg.wait_for_timeout(5000); pg.evaluate(CLEAN)
            for name, keys, ty in jobs:
                if ONLY and name not in ONLY: continue
                if keys:
                    r = pg.evaluate(FIND, keys[0])
                    if not r: print("没找到", name, keys[0], flush=True); continue
                    pg.evaluate(f"window.scrollBy(0, {r[1] - ty})"); pg.wait_for_timeout(1200); pg.evaluate(CLEAN); pg.wait_for_timeout(300)
                else:
                    pg.evaluate("window.scrollTo(0, 0)"); pg.wait_for_timeout(800); pg.evaluate(CLEAN)
                pg.screenshot(path=str(IMG / f"{name}.png"))
                hl = [[v * 2 for v in box] for box in (pg.evaluate(FIND, k) for k in keys) if box]
                meta[name] = {"w": 2880, "h": 2200, "hl": hl}
                print("ok", name, hl, flush=True)
        b.close()
    mp.write_text(json.dumps(meta, indent=1))


if __name__ == "__main__":
    main()
