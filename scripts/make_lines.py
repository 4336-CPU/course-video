"""把定稿旁白 lessonN_narration.md 转成 lessonN/lines.json（字幕原文 sub + 配音读法 say）。
  python make_lines.py N
放在 video/ 目录下。旁白表格每行形如 | N-节-句 | 旁白 | 画面 |。
先按 SAY 表换读法，剩下的 0 到 99 的整数统一转成汉字；跑完检查「读法里还剩数字的」是否为空，不空就往 SAY 里补。"""
import json, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
# (原文, 读法)，按顺序替换，长的写在前面。字幕里中英文之间不留空格（配音会在空格处停顿）
SAY = [
    # 文件名里的点、下划线不念
    ("train.log", "train log"), ("summary.json", "summary Jason"), ("read_file", "read file"), ("output/", "output"),
    ("JSON", "Jason"),
    # 大于 99 的数、小数、百分比、版本号逐个写（读数末尾的 0 不念）
    ("200多项", "两百多项"), ("52.8%", "百分之五十二点八"), ("0.9240", "零点九二四"), ("GPT-5.2", "GPT五点二"),
    ("2026年", "二零二六年"),
    # 缩写按惯用读法
    ("ICLR", "eye clear"), ("NVIDIA", "英伟达"),
]
DIG = "零一二三四五六七八九"


def cn(n):
    n = int(n)
    if n < 10: return DIG[n]
    if n < 20: return "十" + (DIG[n % 10] if n % 10 else "")
    if n < 100: return DIG[n // 10] + "十" + (DIG[n % 10] if n % 10 else "")
    return str(n)   # 大于 99 的留着，会在最后的检查里报出来，手动写进 SAY


def main():
    k = sys.argv[1] if len(sys.argv) > 1 else "1"
    lines = []
    for l in (HERE / f"lesson{k}_narration.md").read_text(encoding="utf-8").splitlines():
        m = re.match(r"\| (\d+-\d+(?:-\d+)?[a-z]?) \| (.+?) \| (.+?) \|$", l.strip())
        if not m or not m.group(1).startswith(k + "-"): continue
        sub = say = m.group(2)
        for a, b in SAY: say = say.replace(a, b)
        say = re.sub(r"\d+", lambda x: cn(x.group()), say)
        say = say.replace("」「", "、").replace("「", "").replace("」", "")   # 两个引号挨着时中间补顿号，免得两段英文连读
        say = say.replace("《", "").replace("》", "")
        lines.append({"id": m.group(1), "sub": sub, "say": say})
    (HERE / f"lesson{k}/lines.json").write_text(json.dumps(lines, ensure_ascii=False, indent=1), encoding="utf-8")
    left = [(x["id"], re.findall(r"\d+", x["say"])) for x in lines if re.search(r"\d", x["say"])]
    print(len(lines), "句；读法里还剩数字的：", left)


if __name__ == "__main__":
    main()
