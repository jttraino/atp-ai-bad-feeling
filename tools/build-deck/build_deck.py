#!/usr/bin/env python3
"""Turn a validated JSON payload into the self-contained Throne Room deck.

The model's only job is content: a lede, some points, and a takeaway per station,
plus the cross-cutting patterns. Everything else about the deck (structure, order,
branding, the method screens, the QR code, navigation) is generated here, in code,
where it cannot vary between runs.

That split is deliberate and it is the whole reliability argument:
  - The model does the part that genuinely needs judgment.
  - Code does the part that has one correct answer.
  - Invalid model output is rejected outright, and an existing deck is never
    overwritten with something that failed validation.

Usage:
  build_deck.py --payload payload.json --out closing-keynote/presentation.html
  build_deck.py --payload payload.json --out ... --mode seeded
"""

import argparse
import base64
import html
import json
import pathlib
import re
import sys
from datetime import datetime

REPO = pathlib.Path(__file__).resolve().parents[2]
QR_PATH = REPO / "assets" / "repo-qr-code.png"
REPO_URL = "https://github.com/jttraino/atp-ai-bad-feeling"

STATIONS = [
    ("sky-city", "Sky City", "Infrastructure and integration with third-party tools"),
    ("swamp-planet", "Swamp Planet", "Technical debt and data quality"),
    ("ice-planet", "Ice Planet", "Development-stage use cases stuck in limbo"),
    ("snow-monster-cave", "Snow Monster Cave", "Unexpected costs and security vulnerabilities"),
    ("asteroid-field", "Asteroid Field", "Compliance, legal obstacles, and scope creep"),
]
STATION_IDS = [s[0] for s in STATIONS]
STATION_NAME = {s[0]: s[1] for s in STATIONS}
STATION_THEME = {s[0]: s[2] for s in STATIONS}

# Cosmetic caps. These protect the layout, not the truth, so going over one is not a
# reason to throw away a whole run at 7:50pm. Overlong text is trimmed on a word
# boundary and reported. Structural problems (a missing station, a bad id, the wrong
# number of points, output that isn't JSON) are still hard rejections, because those
# mean the model misunderstood the task rather than got wordy.
LIMITS = {"lede": 500, "takeaway": 280, "t": 150, "d": 560, "closing_line": 360}

CLAMPED = []


class ValidationError(Exception):
    pass


# --------------------------------------------------------------------------- validate

def _text(value, field, limit_key, required=True):
    if value is None or (isinstance(value, str) and not value.strip()):
        if required:
            raise ValidationError(f"{field}: missing or empty")
        return ""
    if not isinstance(value, str):
        raise ValidationError(f"{field}: expected a string, got {type(value).__name__}")
    value = " ".join(value.split())
    limit = LIMITS[limit_key]
    if len(value) > limit:
        cut = value[:limit - 1]
        if " " in cut[limit // 2:]:
            cut = cut.rsplit(" ", 1)[0]
        CLAMPED.append(f"{field}: {len(value)} chars, trimmed to {len(cut) + 1} (cap {limit})")
        value = cut.rstrip(" ,;:.") + "\u2026"
    return value


def _points(raw, field, lo=3, hi=5):
    if not isinstance(raw, list):
        raise ValidationError(f"{field}: expected a list")
    if not (lo <= len(raw) <= hi):
        raise ValidationError(f"{field}: {len(raw)} points, expected {lo} to {hi}")
    out = []
    for i, p in enumerate(raw):
        if not isinstance(p, dict):
            raise ValidationError(f"{field}[{i}]: expected an object with t and d")
        out.append({
            "t": _text(p.get("t"), f"{field}[{i}].t", "t"),
            "d": _text(p.get("d"), f"{field}[{i}].d", "d"),
        })
    return out


def validate(payload, sources):
    """sources maps station id -> "transcript"|"fallback", established by the caller
    from what is actually on disk. Any `source` the model volunteers is discarded.
    We do not ask the model to report a fact we already know, so it cannot get it
    wrong, and it cannot launder a fallback into a transcript."""
    if not isinstance(payload, dict):
        raise ValidationError("top level: expected a JSON object")

    raw_stations = payload.get("stations")
    if not isinstance(raw_stations, list):
        raise ValidationError("stations: expected a list")

    seen, stations = {}, []
    for i, st in enumerate(raw_stations):
        if not isinstance(st, dict):
            raise ValidationError(f"stations[{i}]: expected an object")
        sid = st.get("id")
        if sid not in STATION_IDS:
            raise ValidationError(
                f"stations[{i}].id: {sid!r} is not one of {', '.join(STATION_IDS)}")
        if sid in seen:
            raise ValidationError(f"stations[{i}].id: {sid!r} appears twice")
        seen[sid] = True
        claimed = st.get("source")
        source = sources[sid]
        if claimed in ("transcript", "fallback") and claimed != source:
            print(f"NOTE: model claimed {sid} was a {claimed}; it was a {source}. "
                  f"Ignoring the model and using what is on disk.", file=sys.stderr)
        stations.append({
            "id": sid,
            "name": STATION_NAME[sid],
            "theme": STATION_THEME[sid],
            "source": source,
            "lede": _text(st.get("lede"), f"stations[{i}].lede", "lede"),
            "points": _points(st.get("points"), f"stations[{i}].points"),
            "takeaway": _text(st.get("takeaway"), f"stations[{i}].takeaway", "takeaway"),
        })

    missing = [s for s in STATION_IDS if s not in seen]
    if missing:
        raise ValidationError(f"stations: missing {', '.join(missing)}")

    stations.sort(key=lambda s: STATION_IDS.index(s["id"]))
    return {
        "stations": stations,
        "patterns": _points(payload.get("patterns"), "patterns"),
        "closing_line": _text(payload.get("closing_line"), "closing_line", "closing_line"),
    }


# --------------------------------------------------------------------------- render

def e(s):
    return html.escape(s, quote=False)


def points_html(points):
    items = "".join(
        '<li><span class="n">{n:02d}</span><span><span class="t">{t}</span>'
        '<br><span class="d">{d}</span></span></li>'.format(n=i + 1, t=e(p["t"]), d=e(p["d"]))
        for i, p in enumerate(points))
    return f'<ol class="points">{items}</ol>'


def qr_data_uri():
    if not QR_PATH.exists():
        return ""
    return "data:image/png;base64," + base64.b64encode(QR_PATH.read_bytes()).decode()


def method_screens(mode, generated_at, counts):
    live, fell_back = counts
    qr = qr_data_uri()
    qr_block = (f'<img class="qr" alt="QR code to {REPO_URL}" src="{qr}">' if qr else "")

    if mode == "seeded":
        provenance = (
            "This copy was built <b>before the stations ran</b>, from the question lists and "
            "the answers we expected to hear. It is the floor, not the deck: if every recording "
            "in the building had failed, this is what you would be looking at, and it would say "
            "so on every screen.")
    else:
        provenance = (
            f"This copy was built <b>in the room, minutes ago</b>. {live} of 5 stations came from "
            f"a real transcript" + (f", {fell_back} fell back to the pre-written question list"
                                    if fell_back else ", none needed a fallback") + ".")

    return [
        {
            "id": "method",
            "kicker": "How this was made",
            "title": "Five rooms, one picture, ten minutes",
            "takeaway": "The AI did the reading. Everything that had one correct answer was done by code.",
            "body":
                '<p class="lede">Five stations ran in parallel. Nobody was in more than one of them. '
                'This deck existed before the last one finished talking.</p>'
                + points_html([
                    {"t": "Every station was recorded to its own meeting, hosted by one person",
                     "d": "Not by the sponsor running the room. One account owned all five, so no session "
                          "depended on a presenter remembering to press a button correctly."},
                    {"t": "Ending the meeting is what starts the transcript",
                     "d": "Teams generates a transcript 2.5 to 5 minutes after a meeting is ended, not "
                          "left. Five staggered endings, then one to three minutes for the model to read "
                          "every word said in this building and answer. That is the budget you just "
                          "watched us spend, and every number in it was measured in rehearsal."},
                    {"t": "The model was given the transcripts and a written brief, and asked for data",
                     "d": "Not for a deck. It returns structured content, which is checked against a schema "
                          "before anything is rendered. Wrong shape, wrong station name, too many bullets: "
                          "rejected, and the previous deck stands."},
                    {"t": "The slides you are looking at were generated by code, not by the model",
                     "d": "Order, branding, navigation, this screen, the QR code: all deterministic. "
                          "The model only wrote the parts that needed judgment about what was said."},
                    {"t": "There was always a deck",
                     "d": "A version of this file was built days ago from the question lists alone. Every "
                          "run since then could only improve on it. Nothing could leave us with nothing."},
                ])
                + f'<div class="callout"><div class="h">Provenance of this copy</div>'
                  f'<div class="b">{provenance} Generated {generated_at}.</div></div>',
        },
        {
            "id": "reliability",
            "kicker": "The transferable part",
            "title": "Why this worked when your AI program did not",
            "takeaway": "Give the model the judgment call. Never give it the parts you can verify.",
            "body":
                '<p class="lede">Nothing here needed a better model. It needed the boring things '
                'around the model to be decided in advance.</p>'
                + points_html([
                    {"t": "One source of truth, in version control, before the event",
                     "d": "Roles, deadlines, failure modes, and the exact fallback behavior were written "
                          "down and argued over in a public repo. AI fails when there is no good source "
                          "of truth, and it fails silently."},
                    {"t": "Constrain the output, then validate it",
                     "d": "A free-text answer cannot be checked. A schema can. The narrower the thing you "
                          "ask for, the more of the result you can verify automatically."},
                    {"t": "Design the degraded path first",
                     "d": "We knew what a failed recording would look like on screen before we knew whether "
                          "any recording would fail. A fallback invented under time pressure is not a fallback."},
                    {"t": "Label provenance where the audience can see it",
                     "d": "Any station on a fallback is marked as one, on its own slide. The failure mode "
                          "to fear is not a wrong answer, it is a wrong answer that looks exactly like a "
                          "right one."},
                    {"t": "Rehearse the whole pipeline, not the parts",
                     "d": "We ran the night end to end against mock transcripts, including every disaster, "
                          "and timed it. That found four real defects, one of which only appears at full "
                          "transcript length and would have failed live, in this room, tonight."},
                ])
                + '<div class="callout"><div class="h">Take it with you</div>'
                  f'<div class="b">The event runbooks, the synthesis tool, the guiding brief, and the '
                  f'rehearsal harness that produced this deck are all public. Scan the code or go to '
                  f'<b>{REPO_URL}</b>.</div>{qr_block}</div>',
        },
    ]


def station_screen(st):
    flagged = st["source"] == "fallback"
    banner = ('<div class="flag"><b>Not from a transcript.</b> This station\'s recording did not '
              'produce usable audio. What follows is built from the question list its sponsor '
              'prepared, and the answers we expected, not from what the room actually said.</div>'
              if flagged else "")
    tag = '<span class="pill warn">FALLBACK</span>' if flagged else '<span class="pill">TRANSCRIPT</span>'
    return {
        "id": st["id"],
        "kicker": st["name"],
        "title": st["theme"],
        "takeaway": st["takeaway"],
        "body": banner + f'<p class="lede">{e(st["lede"])} {tag}</p>' + points_html(st["points"]),
    }


def build(data, mode, generated_at):
    live = sum(1 for s in data["stations"] if s["source"] == "transcript")
    qr = qr_data_uri()
    qr_block = f'<img class="qr" alt="QR code to {REPO_URL}" src="{qr}">' if qr else ""

    screens = method_screens(mode, generated_at, (live, 5 - live))
    screens += [station_screen(s) for s in data["stations"]]
    screens.append({
        "id": "patterns",
        "kicker": "Across all five",
        "title": "What nobody in one room could see",
        "takeaway": data["closing_line"],
        "body":
            '<p class="lede">Each station saw its own failure mode. These showed up in more than '
            'one of them, which is the only reason this session exists.</p>'
            + points_html(data["patterns"])
            + '<div class="callout"><div class="h">' + e(data["closing_line"]) + '</div>'
              '<div class="b">Everything behind this deck, including the station transcripts and the '
              'tool that built it, is at <b>' + REPO_URL + '</b>. Take it and run this at your own '
              'company.</div>' + qr_block + '</div>',
    })
    return screens


TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>__TITLE__</title>
<style>
  :root {
    --brand: #2F7FE4;
    --warn: #B4610C;
    --ink: #14181a;
    --ink-2: #4a5257;
    --ink-3: #7b8489;
    --line: #e3e7e9;
    --fill: #f5f7f8;
    --bg: #ffffff;
  }
  * { box-sizing: border-box; }
  html, body {
    margin: 0; padding: 0;
    background: var(--fill); color: var(--ink);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
    font-size: 15px; line-height: 1.5;
  }
  .shell { max-width: 940px; margin: 0 auto; padding: 28px 24px 64px; }
  .stage { background: var(--bg); border: 1px solid var(--line); border-radius: 6px; padding: 34px 38px 30px; }

  .rail { display: flex; gap: 4px; margin-bottom: 22px; }
  .rail span { flex: 1; height: 3px; background: #dfe4e6; cursor: pointer; }
  .rail span.done { background: #b9c1c4; }
  .rail span.now { background: var(--brand); }

  .topline { display: flex; align-items: center; gap: 10px; margin-bottom: 6px; }
  .wordmark { color: var(--brand); font-weight: 800; letter-spacing: .18em; font-size: 12px; }
  .divider-v { width: 1px; height: 12px; background: var(--line); }
  .kicker { font-size: 12px; letter-spacing: .08em; color: var(--ink-3); text-transform: uppercase; }
  .count { margin-left: auto; font-size: 12px; color: var(--ink-3); font-variant-numeric: tabular-nums; }

  h1 { font-size: 24px; line-height: 1.25; margin: 4px 0 0; font-weight: 650; }
  .rule { width: 48px; height: 2px; background: var(--brand); margin: 12px 0 24px; }
  p { margin: 0 0 12px; }
  .lede { font-size: 16px; margin-bottom: 20px; }

  ol.points { list-style: none; margin: 0; padding: 0; }
  ol.points li { display: flex; gap: 14px; margin-bottom: 15px; }
  ol.points .n { color: var(--brand); font-weight: 700; font-variant-numeric: tabular-nums; min-width: 20px; }
  ol.points .t { font-weight: 600; }
  ol.points .d { color: var(--ink-2); }

  .pill { display: inline-block; font-size: 10.5px; letter-spacing: .07em; font-weight: 700;
          color: var(--brand); border: 1px solid var(--brand); border-radius: 3px;
          padding: 1px 6px; vertical-align: 2px; margin-left: 4px; }
  .pill.warn { color: var(--warn); border-color: var(--warn); }

  .flag { border: 1px solid var(--warn); border-left-width: 3px; background: #fdf6ee;
          color: var(--ink-2); padding: 11px 14px; border-radius: 4px; margin-bottom: 18px; font-size: 14px; }
  .flag b { color: var(--warn); }

  .callout { border: 1px solid var(--line); border-left: 3px solid var(--brand); background: var(--fill);
             padding: 12px 14px; border-radius: 4px; margin-top: 20px; }
  .callout .h { font-weight: 650; margin-bottom: 4px; }
  .callout .b { color: var(--ink-2); }
  .qr { display: block; width: 132px; height: 132px; margin: 12px 0 2px; image-rendering: pixelated; }

  .takeaway { border-left: 3px solid var(--brand); background: var(--fill); padding: 10px 14px; margin-top: 24px; }
  .takeaway .h { font-size: 11.5px; letter-spacing: .08em; color: var(--ink-3); font-weight: 700; margin-bottom: 3px; }
  .takeaway .b { font-weight: 600; }

  .nav { display: flex; align-items: center; gap: 8px; margin-top: 22px; }
  button { font: inherit; font-size: 13px; padding: 6px 14px; border-radius: 4px; border: 1px solid var(--line); background: #fff; cursor: pointer; }
  button.primary { background: var(--ink); color: #fff; border-color: var(--ink); }
  button:disabled { opacity: .4; cursor: default; }
  .nav .right { margin-left: auto; font-size: 12px; color: var(--ink-3); }

  #printAll { display: none; }
  @media print {
    body { background: #fff; }
    .rail, .nav, .stage { display: none !important; }
    .shell { max-width: none; padding: 0; }
    #printAll { display: block; }
    #printAll .page { page-break-after: always; padding: 0 0 24px; }
    #printAll .page:last-child { page-break-after: auto; }
  }
</style>
</head>
<body>
<div class="shell">
  <div class="stage">
    <div class="rail" id="rail"></div>
    <div class="topline">
      <span class="wordmark">ATP</span>
      <span class="divider-v"></span>
      <span class="kicker" id="kicker"></span>
      <span class="count" id="count"></span>
    </div>
    <h1 id="title"></h1>
    <div class="rule"></div>
    <div id="body"></div>
    <div class="takeaway">
      <div class="h">THE LINE FOR THE ROOM</div>
      <div class="b" id="takeaway"></div>
    </div>
    <div class="nav">
      <button id="prev">Previous</button>
      <button id="next" class="primary">Next</button>
      <div class="right">__FOOTER__</div>
    </div>
  </div>
  <div id="printAll"></div>
</div>
<script>
const SCREENS = __SCREENS__;
let i = 0;
const el = id => document.getElementById(id);

function render() {
  const s = SCREENS[i];
  el("kicker").textContent = s.kicker.toUpperCase();
  el("count").textContent = (i + 1) + " / " + SCREENS.length;
  el("title").textContent = s.title;
  el("body").innerHTML = s.body;
  el("takeaway").textContent = s.takeaway;

  const rail = el("rail");
  rail.innerHTML = "";
  SCREENS.forEach((sc, n) => {
    const seg = document.createElement("span");
    seg.title = (n + 1) + ". " + sc.title;
    seg.className = n === i ? "now" : n < i ? "done" : "";
    seg.onclick = () => { i = n; render(); };
    rail.appendChild(seg);
  });

  el("prev").disabled = i === 0;
  el("next").disabled = i === SCREENS.length - 1;
  window.scrollTo(0, 0);
}
el("prev").onclick = () => { i = Math.max(0, i - 1); render(); };
el("next").onclick = () => { i = Math.min(SCREENS.length - 1, i + 1); render(); };
document.onkeydown = ev => {
  if (ev.key === "ArrowRight" || ev.key === " " || ev.key === "PageDown") el("next").click();
  if (ev.key === "ArrowLeft" || ev.key === "PageUp") el("prev").click();
  if (ev.key === "Home") { i = 0; render(); }
  if (ev.key === "End") { i = SCREENS.length - 1; render(); }
};
function buildPrint() {
  el("printAll").innerHTML = SCREENS.map((s, n) =>
    '<div class="page"><div class="topline"><span class="wordmark">ATP</span>' +
    '<span class="divider-v"></span><span class="kicker">' + s.kicker.toUpperCase() + '</span>' +
    '<span class="count">' + (n + 1) + ' / ' + SCREENS.length + '</span></div>' +
    '<h1>' + s.title + '</h1><div class="rule"></div>' + s.body +
    '<div class="takeaway"><div class="h">THE LINE FOR THE ROOM</div><div class="b">' +
    s.takeaway + '</div></div></div>').join("");
}
window.onbeforeprint = buildPrint;
if (location.hash === "#print") buildPrint();
render();
</script>
</body>
</html>
"""


def render_html(screens, mode, generated_at):
    title = "The Throne Room, ATP September 17, 2026"
    if mode == "seeded":
        title += " (pre-seeded)"
    footer = f"ATP &middot; {'Pre-seeded' if mode == 'seeded' else 'Live'} &middot; {generated_at}"
    return (TEMPLATE
            .replace("__TITLE__", html.escape(title))
            .replace("__FOOTER__", footer)
            .replace("__SCREENS__", json.dumps(screens, ensure_ascii=False, indent=1)))


# --------------------------------------------------------------------------- payload loading

FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.S)


def extract_json(raw):
    """Pull a JSON object out of model output that may be fenced or have chatter around it."""
    raw = raw.strip()
    if not raw:
        raise ValidationError("model returned nothing at all")
    for candidate in ([m.group(1) for m in FENCE.finditer(raw)] + [raw]):
        candidate = candidate.strip()
        if not candidate:
            continue
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass
        start, end = candidate.find("{"), candidate.rfind("}")
        if start != -1 and end > start:
            try:
                return json.loads(candidate[start:end + 1])
            except json.JSONDecodeError:
                continue
    raise ValidationError("could not find valid JSON in the model output")


def main():
    ap = argparse.ArgumentParser(description="Build the Throne Room deck from a JSON payload.")
    ap.add_argument("--payload", required=True, help="JSON payload file, or - for stdin")
    ap.add_argument("--out", required=True, help="output .html path")
    ap.add_argument("--mode", choices=["live", "seeded"], default="live")
    ap.add_argument("--sources", required=True,
                    help="ground truth from disk, e.g. sky-city=transcript,swamp-planet=fallback,...")
    args = ap.parse_args()

    sources = {}
    for pair in args.sources.split(","):
        sid, _, kind = pair.strip().partition("=")
        if sid not in STATION_IDS or kind not in ("transcript", "fallback"):
            print(f"REJECTED: --sources entry {pair!r} is not <station-id>=transcript|fallback",
                  file=sys.stderr)
            return 2
        sources[sid] = kind
    if set(sources) != set(STATION_IDS):
        print(f"REJECTED: --sources must cover all five stations, got {sorted(sources)}",
              file=sys.stderr)
        return 2

    raw = sys.stdin.read() if args.payload == "-" else pathlib.Path(args.payload).read_text()
    out = pathlib.Path(args.out)

    try:
        data = validate(extract_json(raw), sources)
    except ValidationError as exc:
        print(f"REJECTED: {exc}", file=sys.stderr)
        if out.exists():
            print(f"REJECTED: {out} left untouched. The previous deck still stands.", file=sys.stderr)
        else:
            print(f"REJECTED: no deck at {out} to fall back to. Run seed.sh.", file=sys.stderr)
        return 2

    for warning in CLAMPED:
        print(f"CLAMPED: {warning}", file=sys.stderr)

    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    screens = build(data, args.mode, generated_at)

    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        out.with_suffix(out.suffix + ".prev").write_text(out.read_text())
    tmp = out.with_suffix(out.suffix + ".tmp")
    tmp.write_text(render_html(screens, args.mode, generated_at))
    tmp.replace(out)

    live = sum(1 for s in data["stations"] if s["source"] == "transcript")
    print(f"Deck written to {out}")
    print(f"  {len(screens)} screens, {live}/5 stations from a real transcript, mode={args.mode}")
    if live < 5:
        fb = [s["name"] for s in data["stations"] if s["source"] == "fallback"]
        print(f"  flagged as fallback on screen: {', '.join(fb)}")
    if CLAMPED:
        print(f"  {len(CLAMPED)} field(s) trimmed to fit the layout")
    return 0


if __name__ == "__main__":
    sys.exit(main())
