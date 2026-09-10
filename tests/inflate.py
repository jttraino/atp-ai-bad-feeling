#!/usr/bin/env python3
"""Grow the mock transcripts to the length a real 45-minute station actually produces.

The fixtures are written to be readable, at roughly 600 words each. The ATP planning
call ran 45 minutes and transcribed to just over 9,000 words, and the stations get a
similar slot. Timing the pipeline against 600-word inputs would flatter it badly, so
this pads each transcript with more exchanges of the same shape until it reaches the
target word count, keeping the Teams format and advancing the timestamps.

Usage: inflate.py <fixture-dir> <out-dir> <target-words-per-station>
"""
import pathlib, random, re, sys

src, dst, target = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]), int(sys.argv[3])
dst.mkdir(parents=True, exist_ok=True)
random.seed(17)  # deterministic: two runs must be comparable

FILLER = [
    "Yeah, we saw the same thing, though for us it was closer to a third of that.",
    "Can you say that again toward the laptop? I want to make sure that one lands.",
    "I'd push back on that slightly. In our case the vendor did warn us, we just didn't read it.",
    "That matches what we found, and it took us about four months to notice.",
    "We're a smaller shop so the numbers are different, but the shape is identical.",
    "Right, and nobody owns it, which is the part that actually costs you.",
    "We tried that and it made the problem less visible without making it smaller.",
    "Our finance team asked the same question and we didn't have an answer for a quarter.",
    "It went to a steering committee, which is where these things go to rest.",
    "Honestly, I think we got lucky. I don't think we'd catch it again.",
]

for f in sorted(src.glob("*.txt")):
    lines = f.read_text().split("\n")
    head, body = lines[:6], lines[6:-4]
    tail = lines[-4:]
    speakers = sorted({m.group(1) for l in body
                       if (m := re.match(r"^([A-Z][A-Za-z.'\- ]+?) \d+:\d\d$", l))})
    out, words, t = list(body), len(" ".join(body).split()), 3000
    while words < target:
        who = random.choice(speakers)
        text = random.choice(FILLER)
        out += ["[]", f"{who} {t//60}:{t%60:02d}", text, ""]
        words += len(text.split()); t += 41
    (dst / f.name).write_text("\n".join(head + out + tail))
    print(f"  {f.name}: {words} words")
