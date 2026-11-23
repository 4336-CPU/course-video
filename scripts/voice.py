"""旁白配音：一句一段音频，按真实时长排时间轴。放在 lessonN/ 目录下，读同目录的 lines.json。
  python voice.py edge                     # Edge TTS 草稿配音（免费）
  python voice.py minimax                  # MiniMax 正式配音，Key 从环境变量 MINIMAX_API_KEY 读
  python voice.py minimax 2-3-8=1.04 ...   # 只按指定语速重合成这几句
  python voice.py minimax none=1           # 不合成，只按已有音频重排时间轴
  python voice.py dir <目录>               # 用 <目录>/<id>.wav
产出：timings.js（window.TIM 每句起止秒数、SUBTXT 字幕、WORDS 逐词时间、SAYTXT 读法）、voice.wav。
句子编号形如 N-节-句，节号变化时加 SEC_GAP，并在 TIM 里记 sec<节号> 的开始时间。"""
import asyncio, json, re, subprocess, sys, wave
from pathlib import Path
import imageio_ffmpeg, numpy as np

HERE = Path(__file__).resolve().parent
FF = imageio_ffmpeg.get_ffmpeg_exe()
SR, LEAD, GAP, SEC_GAP, TAIL = 24000, 1.2, .35, 1.1, 7.0
# 句间停顿统一：GAP + 0.45 秒，约 0.8 秒。停顿忽长忽短会被听出来，只有少数几处加长：
# 问完问题等答案出来 1.0，留给观众想 3.0，全片最后一句 1.5。插入新段落时可以在这里补零头，让插入时长是整帧
HOLD_DEFAULT = .45
HOLD = {}   # 例：{"1-1-3": 1.0, "1-5-4": 3.0, "1-5-5": 1.5}
ONLY = {a.split("=")[0]: float(a.split("=")[1]) for a in sys.argv[2:] if "=" in a}
LINES = json.loads((HERE / "lines.json").read_text(encoding="utf-8"))


def load(path):
    raw = subprocess.run([FF, "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.int16).astype(np.float32) / 32768


async def edge(out):
    """Edge TTS：同时拿逐词时间戳（WordBoundary），存成 <id>.words.json：[[词在读法里的起始字符, 秒], ...]"""
    import edge_tts
    for ln in LINES:
        p, wp, tp = out / f"{ln['id']}.mp3", out / f"{ln['id']}.words.json", out / f"{ln['id']}.txt"
        # 按句号缓存，但稿子改过的句子必须重新合成（只认 id 会把旧稿的音频接到新句子上）
        if p.exists() and wp.exists() and tp.exists() and tp.read_text(encoding="utf-8") == ln["say"]: continue
        async def one():
            c = edge_tts.Communicate(ln["say"], "zh-CN-YunxiNeural", rate="-15%", boundary="WordBoundary")
            audio, words, pos = bytearray(), [], 0
            async for ch in c.stream():
                if ch["type"] == "audio": audio += ch["data"]
                elif ch["type"] == "WordBoundary":
                    i = ln["say"].find(ch["text"], pos); i = pos if i < 0 else i; pos = i + len(ch["text"])
                    words.append([i, round(ch["offset"] / 1e7, 3)])
            return audio, words
        for k in range(5):   # 网络偶尔卡住或不返回音频：限时 60 秒，重试
            try: audio, words = await asyncio.wait_for(one(), 60); break
            except Exception as e: print("重试", ln["id"], type(e).__name__, flush=True); await asyncio.sleep(3)
        else: raise SystemExit("合成失败：" + ln["id"])
        p.write_bytes(bytes(audio)); wp.write_text(json.dumps(words)); tp.write_text(ln["say"], encoding="utf-8")


MM_VOICE, MM_SPEED, MM_EMO = "Chinese_worker_male", 1.1, "calm"   # MiniMax 现成男声，可换成别的 voice_id
# 不指定情绪时，MiniMax 每句自己猜语气：同一句两次合成能差 1 秒，词中间会断开，
# 英文工具名会念得很「热血」。全稿统一用 calm，语气和语速都稳定得多。
MM_TOL = .10   # 单句语速偏离全稿中位数超过 10% 就按比例改 speed 重合成一次，让全片快慢一致


def rate(ln, words, dur):
    """每秒念多少字：汉字算 1，英文单词算 2（念起来大约两个音节）。"""
    n = len(re.findall(r"[\u4e00-\u9fff]", ln["say"])) + 2 * len(re.findall(r"[A-Za-z]+", ln["say"]))
    return n / max(dur, .5)


def align(say, segs):
    """把 MiniMax 返回的逐字时间戳对到读法文本的字符位置上：[[字符位置, 秒], ...]。
    带多音字表（pronunciation_dict）时，返回里会混进 (hang2) 这类注音，要跳过；
    每个词只在当前位置附近找，找不到就留在原位，不往后推（往后推会让字幕和动作整体提前，和配音对不上）。"""
    import re
    words, pos = [], 0
    for s in segs:
        base = s.get("time_begin", 0)
        for w in s.get("timestamped_words", []):
            x = w["word"].strip()
            if not x or re.fullmatch(r"[，。、：；？！,.!?\s]+", x) or re.fullmatch(r"\(?[a-z]+\d\)?", x): continue
            i = say.find(x, pos, pos + len(x) + 4)
            if i < 0: continue
            tb = w["time_begin"]; tb = tb + base if tb < base else tb
            words.append([i, round(tb / 1000, 3)]); pos = i + len(x)
    return words


def minimax(out):
    """MiniMax speech-2.8-hd：subtitle_type=word 返回逐字时间戳，同样存成 <id>.words.json。
    Key 从环境变量 MINIMAX_API_KEY 读；多音字读法放在 pronunciation.json（格式 {"tone": ["十来行/(shi2)(lai2)(hang2)", "处理/(chu3)(li3)"]}）。"""
    import os, urllib.request, time
    from concurrent.futures import ThreadPoolExecutor
    key = os.environ.get("MINIMAX_API_KEY") or sys.exit("先设置环境变量 MINIMAX_API_KEY")
    pp = HERE / "pronunciation.json"
    pron = json.loads(pp.read_text(encoding="utf-8")) if pp.exists() else {"tone": []}

    def post(body):
        req = urllib.request.Request("https://api.minimaxi.com/v1/t2a_v2", data=json.dumps(body).encode(),
                                     headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"})
        return json.loads(urllib.request.urlopen(req, timeout=120).read())

    def one(ln, speed, force=False):
        p, wp, tp = out / f"{ln['id']}.mp3", out / f"{ln['id']}.words.json", out / f"{ln['id']}.txt"
        tag = f"{MM_VOICE}|{MM_EMO}|"   # 缓存只认音色、情绪和读法；语速由第二遍校准决定，存在 .speed 里
        if not force and p.exists() and wp.exists() and tp.exists() and tp.read_text(encoding="utf-8") == tag + ln["say"]: return
        body = {"model": "speech-2.8-hd", "text": ln["say"], "stream": False, "language_boost": "Chinese",
                "voice_setting": {"voice_id": MM_VOICE, "speed": round(speed, 2), "vol": 1, "pitch": 0, "emotion": MM_EMO},
                "audio_setting": {"sample_rate": 32000, "bitrate": 128000, "format": "mp3", "channel": 1},
                "pronunciation_dict": pron, "subtitle_enable": True, "subtitle_type": "word"}
        for k in range(6):
            try:
                r = post(body)
                if r["base_resp"]["status_code"] != 0: raise RuntimeError(r["base_resp"])
                segs = json.loads(urllib.request.urlopen(r["data"]["subtitle_file"], timeout=60).read())
                break
            except Exception as e:
                print("重试", ln["id"], e, flush=True); time.sleep(8)
        else: raise SystemExit("合成失败：" + ln["id"])
        end = max([w["time_end"] / 1000 for s in segs for w in s.get("timestamped_words", [])] or [0])
        (out / f"{ln['id']}.raw.json").write_text(json.dumps(segs, ensure_ascii=False), encoding="utf-8")
        words = align(ln["say"], segs)
        p.write_bytes(bytes.fromhex(r["data"]["audio"])); wp.write_text(json.dumps(words))
        (out / f"{ln['id']}.speed").write_text(json.dumps([round(speed, 2), round(end, 3)]))
        tp.write_text(tag + ln["say"], encoding="utf-8")
        print("好了", ln["id"], round(speed, 2), flush=True)

    if ONLY:   # voice.py minimax 2-3-8=1.04 …：只按指定语速重合成这几句（校准一次没收住时手动补）
        for ln in LINES:
            if ln["id"] in ONLY: one(ln, ONLY[ln["id"]], True)
        return
    with ThreadPoolExecutor(2) as ex: list(ex.map(lambda ln: one(ln, MM_SPEED), LINES))
    # 第二遍：按语速校准。短句（不到 12 字）不参与，停顿占比太大，量不准
    info = {ln["id"]: json.loads((out / f"{ln['id']}.speed").read_text()) for ln in LINES}
    rs = {ln["id"]: rate(ln, None, info[ln["id"]][1]) / info[ln["id"]][0] for ln in LINES if len(ln["say"]) >= 12}
    base = sorted(rs.values())[len(rs) // 2] * MM_SPEED   # 全稿中位数：speed=MM_SPEED 时每秒的字数
    todo = []
    for ln in LINES:
        sp, dur = info[ln["id"]]
        if ln["id"] not in rs: continue
        rr = rate(ln, None, dur)
        if abs(rr / base - 1) > MM_TOL: todo.append((ln, min(1.5, max(.9, sp * base / rr))))
    print("语速中位数", round(base, 2), "字/秒；要校准的：", [(l["id"], round(s, 2)) for l, s in todo], flush=True)
    with ThreadPoolExecutor(2) as ex: list(ex.map(lambda x: one(x[0], x[1], True), todo))


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "edge"
    if mode == "edge":
        src = HERE / "voice_edge"; src.mkdir(exist_ok=True); asyncio.run(edge(src)); ext = "mp3"
    elif mode == "minimax":
        src = HERE / "voice_minimax"; src.mkdir(exist_ok=True); minimax(src); ext = "mp3"
    else:
        src = Path(sys.argv[2]); ext = "wav"
    t, prev, tim, track, words = LEAD, None, {}, [], {}
    for ln in LINES:
        sec = ln["id"].split("-")[1]   # 编号 2-节-句
        if prev and sec != prev:
            t += SEC_GAP
        if sec != prev:
            tim["sec" + sec] = round(t - .4, 3)
        a = load(src / f"{ln['id']}.{ext}")
        head = int(np.argmax(np.abs(a) > .01))
        a = a[head:len(a) - np.argmax(np.abs(a[::-1]) > .01)]
        tim[ln["id"]] = [round(t, 3), round(t + len(a) / SR, 3)]
        wp = src / f"{ln['id']}.words.json"
        if wp.exists():
            words[ln["id"]] = [len(ln["say"])] + [[c, round(t + max(0, s - head / SR), 3)] for c, s in json.loads(wp.read_text())]
        track.append((t, a)); t += len(a) / SR + GAP + HOLD.get(ln["id"], HOLD_DEFAULT); prev = sec
    tim["END"] = round(t - GAP + TAIL, 3)
    buf = np.zeros(int(tim["END"] * SR) + 1, np.float32)
    for st, a in track: buf[int(st * SR):int(st * SR) + len(a)] += a
    with wave.open(str(HERE / "voice.wav"), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(buf, -1, 1) * 32767).astype(np.int16).tobytes())
    subs = {ln["id"]: ln["sub"] for ln in LINES}; says = {ln["id"]: ln["say"] for ln in LINES}
    (HERE / "timings.js").write_text("window.TIM = " + json.dumps(tim) + ";\nwindow.SUBTXT = " +
                                     json.dumps(subs, ensure_ascii=False) + ";\nwindow.WORDS = " + json.dumps(words) + ";\nwindow.SAYTXT = " + json.dumps(says, ensure_ascii=False) + ";\n", encoding="utf-8")
    print("总长", tim["END"], "秒")


if __name__ == "__main__":
    main()
