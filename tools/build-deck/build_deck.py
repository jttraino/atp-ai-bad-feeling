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
import subprocess
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
VOICE_LABELS = {"straight": "Straight", "solo": "Han Solo", "threepio": "C-3PO",
                "yoda": "Yoda", "vader": "Vader"}

# Screens written by us, not by the model. They stay in one voice: they are the
# credibility of the whole deck, and a joke is a bad place to keep your evidence.
UNVOICED = ("method", "reliability")

LIMITS = {"lede": 500, "takeaway": 280, "t": 150, "d": 560, "closing_line": 360}

CLAMPED = []


class ValidationError(Exception):
    pass


# This repo doesn't use em dashes, and models reach for them constantly. Fixing that
# in code rather than in the prompt: it has exactly one correct answer, so it isn't
# the model's job, and a rule the prompt has to keep winning is a rule that eventually
# loses. A dash between two numbers is a range; anywhere else it's a comma.
DASHES = re.compile(r"\s*[\u2014\u2013]\s*")


def _dedash(value):
    def repl(m):
        i = m.start()
        before = value[:i].rstrip()[-1:] if i else ""
        after = value[m.end():].lstrip()[:1]
        return " to " if before.isdigit() and after.isdigit() else ", "
    return DASHES.sub(repl, value)


# --------------------------------------------------------------------------- validate

def _text(value, field, limit_key, required=True):
    if value is None or (isinstance(value, str) and not value.strip()):
        if required:
            raise ValidationError(f"{field}: missing or empty")
        return ""
    if not isinstance(value, str):
        raise ValidationError(f"{field}: expected a string, got {type(value).__name__}")
    value = " ".join(value.split())
    value = _dedash(value)
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

NUMBERS = re.compile(r"\d(?:[\d,.]*\d)?")


def all_text(data):
    out = [data["closing_line"]]
    for st in data["stations"]:
        out += [st["lede"], st["takeaway"]]
        out += [p["t"] for p in st["points"]] + [p["d"] for p in st["points"]]
    out += [p["t"] for p in data["patterns"]] + [p["d"] for p in data["patterns"]]
    return " ".join(out)


def numbers_lost(straight, voiced):
    """Figures present in the straight deck that the voice pass dropped.

    The voice brief says every number survives, and that is the only reason the joke
    is allowed near the findings at all. Reported rather than fatal, because a voice
    may legitimately spell a figure out in words, which this cannot see. Worth looking
    at before you present it."""
    before = set(NUMBERS.findall(all_text(straight)))
    after = set(NUMBERS.findall(all_text(voiced)))
    return sorted(n for n in before - after if len(n.replace(",", "").replace(".", "")) >= 2)


def fields(data):
    out = [data["closing_line"]]
    for st in data["stations"]:
        out += [st["lede"], st["takeaway"]]
        for p in st["points"]:
            out += [p["t"], p["d"]]
    for p in data["patterns"]:
        out += [p["t"], p["d"]]
    return out


def voice_divergence(straight, voiced):
    """Share of fields the voice pass actually rewrote.

    A voice that comes back almost identical to the straight deck is a failure the
    schema cannot see: it validates perfectly and is simply pointless on stage. This
    is the cheap automatic version of noticing that by eye, which is how it was found
    the first time. Low scores mean the direction was too timid, not that the deck
    is broken, so it warns rather than rejects."""
    a, b = fields(straight), fields(voiced)
    if len(a) != len(b) or not a:
        return 1.0
    return sum(1 for x, y in zip(a, b) if x.strip() != y.strip()) / len(a)


# Counted, not policed. The brief asks for at most one reference per screen because
# two on a slide is where the room stops hearing the finding and starts waiting for
# the next gag. A model will drift past that, and drift is invisible while you are
# reading any single slide and obvious across a whole deck.
REFERENCES = [
    "bad feeling", "older code", "tell me the odds", "how the force works",
    "lack of", "droids you", "do or do not", "there is no try", "no try",
    "it's a trap", "garbage will do", "high ground", "i am your father",
    "the force is strong", "these are not the droids", "great, kid",
]


def reference_report(data):
    """(per-screen overuse, total count). Advisory only."""
    over, total = [], 0
    for st in data["stations"] + [{"id": "patterns", "lede": "", "takeaway": data["closing_line"],
                                   "points": data["patterns"]}]:
        blob = " ".join([st.get("lede", ""), st.get("takeaway", "")]
                        + [p["t"] for p in st["points"]] + [p["d"] for p in st["points"]]).lower()
        n = sum(blob.count(r) for r in REFERENCES)
        total += n
        if n > 1:
            over.append((st["id"], n))
    return over, total


def e(s):
    return html.escape(s, quote=False)


def points_html(points):
    items = "".join(
        '<li><span class="n">{n:02d}</span><span><span class="t">{t}</span>'
        '<br><span class="d">{d}</span></span></li>'.format(n=i + 1, t=e(p["t"]), d=e(p["d"]))
        for i, p in enumerate(points))
    return f'<ol class="points">{items}</ol>'


DEFAULT_FOLLOW_URL = ("https://jttraino.github.io/atp-ai-bad-feeling/"
                      "closing-keynote/presentation.html")


def qr_svg(url):
    """A minimal inline SVG QR for one URL, via qrencode.

    Inline and offline on purpose: the venue's wifi is not something to bet the
    keynote on, and a QR that needs the network to render is a QR that fails in
    exactly the room it was made for. Returns "" if qrencode is missing, and the
    deck falls back to showing the link as text."""
    try:
        out = subprocess.run(["qrencode", "-t", "SVG", "-m", "1", "-s", "4", "-l", "M",
                              "--svg-path", "-o", "-", url],
                             capture_output=True, check=True).stdout.decode()
    except (OSError, subprocess.CalledProcessError):
        return ""
    box = re.search(r'viewBox="([^"]+)"', out)
    path = re.search(r'<path[^>]*?d="([^"]+)"', out)
    xform = re.search(r'<path[^>]*?transform="([^"]+)"', out)
    if not (box and path):
        return ""
    # qrencode draws the modules as STROKED one-unit horizontal segments, not as filled
    # shapes, and it offsets them with a transform. Re-emit it with fill and no stroke
    # and every segment has zero area, so you get a correctly sized, perfectly blank
    # square. Keep the stroke and keep the transform.
    t = f' transform="{xform.group(1)}"' if xform else ""
    return (f'<svg class="followqr" viewBox="{box.group(1)}" xmlns="http://www.w3.org/2000/svg" '
            f'shape-rendering="crispEdges" role="img" aria-label="QR code to this screen">'
            f'<rect width="100%" height="100%" fill="#fff"/>'
            f'<path{t} d="{path.group(1)}" stroke="#000" stroke-width="1" fill="none"/></svg>')


def qr_data_uri():
    if not QR_PATH.exists():
        return ""
    return "data:image/png;base64," + base64.b64encode(QR_PATH.read_bytes()).decode()


def method_screens(mode, generated_at, counts, engine=""):
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
    if engine:
        provenance += f" Written by {engine}."

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
                    {"t": "Two models ran at once, and it was not a race",
                     "d": "A fast standby answered the same question in parallel. The good model got the "
                          "whole deadline to itself and the standby was only used if it missed. Measured "
                          "on the night's transcripts: 81 seconds against 167. A race would have handed "
                          "you the weaker deck most times it ran."},
                    {"t": "There was always a deck",
                     "d": "A version of this file was built days ago from the question lists alone. Three "
                          "rungs down from here, and every one of them presentable: the good model, the "
                          "standby on the real transcripts, then that. Nothing could leave us with nothing."},
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


def build(data, mode, generated_at, engine=""):
    live = sum(1 for s in data["stations"] if s["source"] == "transcript")
    qr = qr_data_uri()
    qr_block = f'<img class="qr" alt="QR code to {REPO_URL}" src="{qr}">' if qr else ""

    screens = method_screens(mode, generated_at, (live, 5 - live), engine)
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
    /* Everything sizes off --fs so presentation mode is one number, not a restyle.
       --s is nudged live with + and - because the only way to know what reads from
       the back of a particular room is to stand in it. */
    --base-fs: 15px;
    --s: 1;
    --fs: calc(var(--base-fs) * var(--s));
    --maxw: 940px;
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
    font-size: var(--fs); line-height: 1.5;
  }
  /* Presentation mode is one number. Everything sizes off --fs, so doubling --s
     doubles the whole deck rather than restyling it screen by screen. */
  :root.presenting { --s: 2; --maxw: 1760px; }
  :root.presenting .shell { padding: 12px 16px 20px; }
  :root.presenting .stage { padding: 20px 26px 18px; }
  :root.presenting ol.points li { margin-bottom: calc(var(--fs) * 0.55); }
  :root.presenting .lede { margin-bottom: calc(var(--fs) * 0.7); }
  :root.presenting .rule { margin: 10px 0 16px; }
  :root.presenting .takeaway { margin-top: calc(var(--fs) * 0.7); }
  /* Headline big, detail a step down. On a projector the headline is what carries the
     room and the detail is what the phone is for. */
  /* The projector shows headlines. The phone shows the detail.

     This is not a compromise, it is the measurement: five headlines each followed by
     two lines of detail needs 1458px of a 993px screen at readable type, so something
     has to go, and it should be the thing nobody reads off a wall in a bar. Headlines
     plus the takeaway is a slide. Headlines plus 400 characters of detail is a document
     being projected at people. Press D to reveal the detail on any screen. */
  :root.presenting ol.points .d { display: none; }
  :root.presenting.details ol.points .d { display: block; font-size: calc(var(--fs) * .72); }
  :root.presenting ol.points .t { font-size: calc(var(--fs) * 1.05); }
  :root.presenting ol.points li { margin-bottom: calc(var(--fs) * 0.42); }
  :root.presenting .follow { margin-top: 8px; padding-top: 8px; }
  :root.presenting .follow .t { font-size: calc(var(--fs) * .55); }
  /* Big enough to scan from the back of the room, which is the only size that counts.
     A QR only the front two rows can reach is decoration. */
  :root.presenting .followqr { width: calc(var(--fs) * 4.6); }
  :root.presenting .follow .t { font-size: calc(var(--fs) * .62); }
  .shell { max-width: var(--maxw); margin: 0 auto; padding: 28px 24px 64px; }
  .stage { background: var(--bg); border: 1px solid var(--line); border-radius: 6px; padding: 34px 38px 30px; }

  .rail { display: flex; gap: 4px; margin-bottom: 22px; }
  .rail span { flex: 1; height: 3px; background: #dfe4e6; cursor: pointer; }
  .rail span.done { background: #b9c1c4; }
  .rail span.now { background: var(--brand); }

  .topline { display: flex; align-items: center; gap: 10px; margin-bottom: 6px; }
  .wordmark { color: var(--brand); font-weight: 800; letter-spacing: .18em; font-size: calc(var(--fs) * .8); }
  .divider-v { width: 1px; height: 12px; background: var(--line); }
  .kicker { font-size: calc(var(--fs) * .8); letter-spacing: .08em; color: var(--ink-3); text-transform: uppercase; }
  .count { margin-left: auto; font-size: calc(var(--fs) * .8); color: var(--ink-3); font-variant-numeric: tabular-nums; }

  h1 { font-size: calc(var(--fs) * 1.6); line-height: 1.25; margin: 4px 0 0; font-weight: 650; }
  .rule { width: 48px; height: 2px; background: var(--brand); margin: 12px 0 24px; }
  p { margin: 0 0 12px; }
  .lede { font-size: calc(var(--fs) * 1.07); margin-bottom: 20px; }

  ol.points { list-style: none; margin: 0; padding: 0; }
  ol.points li { display: flex; gap: 14px; margin-bottom: 15px; }
  ol.points .n { color: var(--brand); font-weight: 700; font-variant-numeric: tabular-nums; min-width: calc(var(--fs) * 1.35); }
  ol.points .t { font-weight: 600; }
  ol.points .d { color: var(--ink-2); }

  .pill { display: inline-block; font-size: calc(var(--fs) * .7); letter-spacing: .07em; font-weight: 700;
          color: var(--brand); border: 1px solid var(--brand); border-radius: 3px;
          padding: 1px 6px; vertical-align: 2px; margin-left: 4px; }
  .pill.warn { color: var(--warn); border-color: var(--warn); }

  .flag { border: 1px solid var(--warn); border-left-width: 3px; background: #fdf6ee;
          color: var(--ink-2); padding: 11px 14px; border-radius: 4px; margin-bottom: 18px; font-size: calc(var(--fs) * .93); }
  .flag b { color: var(--warn); }

  .callout { border: 1px solid var(--line); border-left: 3px solid var(--brand); background: var(--fill);
             padding: 12px 14px; border-radius: 4px; margin-top: 20px; }
  .callout .h { font-weight: 650; margin-bottom: 4px; }
  .callout .b { color: var(--ink-2); }
  .qr { display: block; width: 132px; height: 132px; margin: 12px 0 2px; image-rendering: pixelated; }

  .takeaway { border-left: 3px solid var(--brand); background: var(--fill); padding: 10px 14px; margin-top: 24px; }
  .takeaway .h { font-size: calc(var(--fs) * .77); letter-spacing: .08em; color: var(--ink-3); font-weight: 700; margin-bottom: 3px; }
  .takeaway .b { font-weight: 600; }

  .nav { display: flex; align-items: center; gap: 8px; margin-top: 22px; }
  button { font: inherit; font-size: calc(var(--fs) * .87); padding: 6px 14px; border-radius: 4px; border: 1px solid var(--line); background: #fff; cursor: pointer; }
  button.primary { background: var(--ink); color: #fff; border-color: var(--ink); }
  button:disabled { opacity: .4; cursor: default; }
  .nav .right { margin-left: auto; font-size: calc(var(--fs) * .8); color: var(--ink-3); }

  .voices { display: flex; align-items: center; gap: 6px; margin-top: 14px;
            padding-top: 14px; border-top: 1px solid var(--line); }
  .voices .lab { font-size: calc(var(--fs) * .77); letter-spacing: .08em; color: var(--ink-3); font-weight: 700; margin-right: 4px; }
  .voices button { font-size: calc(var(--fs) * .8); padding: 4px 10px; }
  .voices button.on { background: var(--brand); color: #fff; border-color: var(--brand); }
  .follow { display: flex; align-items: center; gap: 12px; margin-top: 12px;
            padding-top: 12px; border-top: 1px solid var(--line); }
  .followqr { width: 62px; aspect-ratio: 1 / 1; flex: none; display: block; }
  .follow .t { font-size: calc(var(--fs) * .8); color: var(--ink-3); line-height: 1.45; }
  .follow .t b { color: var(--ink-2); }
  .follow .u { font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
               font-size: calc(var(--fs) * .72); color: var(--ink-3); word-break: break-all; }

  .voices .hint { margin-left: auto; font-size: calc(var(--fs) * .77); color: var(--ink-3); }

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
    <div class="follow" id="follow" hidden>
      <span id="followQr"></span>
      <span class="t"><b>Follow along on your phone.</b> This screen, with the full detail
        that will not fit on a projector.<br><span class="u" id="followUrl"></span></span>
    </div>
    <div class="voices" id="voices" hidden>
      <span class="lab">VOICE</span>
      <span id="voiceButtons"></span>
      <span class="hint" id="voiceHint"></span>
    </div>
  </div>
  <div id="printAll"></div>
</div>
<script>
// VOICES is [[key, label], ...] in display order.
// UNVOICED lists the screen ids that never change voice: they are ours, not the model's.
const DECKS = __DECKS__;
const VOICES = __VOICES__;
const UNVOICED = __UNVOICED__;
const QRS = __QRS__;            // screen id -> inline SVG, one per screen, not per voice
const FOLLOW_URL = __FOLLOW_URL__;
let i = 0;
let voice = "straight";
const el = id => document.getElementById(id);
const screens = () => DECKS[voice] || DECKS.straight;

const store = (k, v) => { try { localStorage.setItem(k, v); } catch (e) {} };
const load = (k, d) => { try { const v = localStorage.getItem(k); return v === null ? d : v; } catch (e) { return d; } };

let scale = parseFloat(load("atp-scale", "")) || 0;
let presenting = load("atp-presenting", "0") === "1";

function applyMode() {
  document.documentElement.classList.toggle("presenting", presenting);
  // A saved nudge only means anything for the mode it was set in.
  document.documentElement.style.setProperty("--s", scale || (presenting ? 2 : 1));
  store("atp-presenting", presenting ? "1" : "0");
  autofit();
}

// Shrink until the screen fits the screen. A projector cannot scroll, and the takeaway
// is the last thing on every slide, so anything that overflows takes the line for the
// room with it. Skipped the moment the presenter nudges the size by hand: at that point
// they are standing in the room and know better than this does.
function autofit() {
  if (!presenting || scale) return;
  const root = document.documentElement;
  let s = 2;
  root.style.setProperty("--s", s);
  while (s > 1.15 && root.scrollHeight > window.innerHeight) {
    s = Math.round((s - 0.05) * 100) / 100;
    root.style.setProperty("--s", s);
  }
}
function nudge(delta) {
  const cur = parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--s")) || 1;
  scale = Math.min(5, Math.max(0.6, Math.round((cur + delta) * 20) / 20));
  store("atp-scale", scale);
  applyMode();
}

function setVoice(v) {
  if (!DECKS[v]) return;
  voice = v;
  document.querySelectorAll("#voiceButtons button").forEach(b =>
    b.classList.toggle("on", b.dataset.voice === v));
  render();
}

function render() {
  const SCREENS = screens();
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

  if (FOLLOW_URL) {
    el("follow").hidden = false;
    el("followQr").innerHTML = QRS[s.id] || "";
    el("followUrl").textContent = FOLLOW_URL + "#" + s.id;
  }
  // The address bar always points at the screen on show, so the presenter's own URL
  // is shareable mid-talk and a scanned deep link lands on the right slide.
  try { history.replaceState(null, "", "#" + s.id); } catch (e) {}
  autofit();

  el("prev").disabled = i === 0;
  el("next").disabled = i === SCREENS.length - 1;
  el("voiceHint").textContent =
    UNVOICED.indexOf(s.id) !== -1 ? "this screen is ours, so it stays straight"
                                  : "keys 1-" + VOICES.length + ", V to cycle, P to project, D for detail";
  window.scrollTo(0, 0);
}
el("prev").onclick = () => { i = Math.max(0, i - 1); render(); };
el("next").onclick = () => { i = Math.min(screens().length - 1, i + 1); render(); };

if (VOICES.length > 1) {
  el("voices").hidden = false;
  el("voiceButtons").innerHTML = VOICES.map(([k, label]) =>
    '<button data-voice="' + k + '">' + label + '</button>').join(" ");
  document.querySelectorAll("#voiceButtons button").forEach(b =>
    b.onclick = () => setVoice(b.dataset.voice));
}

document.onkeydown = ev => {
  if (ev.key.toLowerCase() === "p") { presenting = !presenting; scale = 0; applyMode(); return; }
  if (ev.key.toLowerCase() === "d") {
    document.documentElement.classList.toggle("details");
    scale = 0; applyMode(); return;
  }
  if (ev.key === "+" || ev.key === "=") { nudge(0.1); return; }
  if (ev.key === "-" || ev.key === "_") { nudge(-0.1); return; }
  if (ev.key === "ArrowRight" || ev.key === " " || ev.key === "PageDown") el("next").click();
  if (ev.key === "ArrowLeft" || ev.key === "PageUp") el("prev").click();
  if (ev.key === "Home") { i = 0; render(); }
  if (ev.key === "End") { i = screens().length - 1; render(); }
  // Voice switching is meant to happen live, mid-sentence, without losing your place.
  if (VOICES.length > 1) {
    if (ev.key.toLowerCase() === "v") {
      const n = VOICES.findIndex(v => v[0] === voice);
      setVoice(VOICES[(n + 1) % VOICES.length][0]);
    }
    const d = parseInt(ev.key, 10);
    if (d >= 1 && d <= VOICES.length) setVoice(VOICES[d - 1][0]);
  }
};
function buildPrint() {
  const SCREENS = screens();
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

// Deep link: land on the screen the QR pointed at.
function fromHash() {
  const id = decodeURIComponent(location.hash.replace(/^#/, ""));
  const n = screens().findIndex(s => s.id === id);
  if (n >= 0) i = n;
}
fromHash();
window.addEventListener("hashchange", () => { fromHash(); render(); });
window.addEventListener("resize", autofit);

applyMode();
render();
</script>
</body>
</html>
"""


def render_html(decks, order, mode, generated_at, follow_url=""):
    title = "The Throne Room, ATP September 17, 2026"
    if mode == "seeded":
        title += " (pre-seeded)"
    footer = f"ATP &middot; {'Pre-seeded' if mode == 'seeded' else 'Live'} &middot; {generated_at}"
    voices = [[k, VOICE_LABELS.get(k, k.title())] for k in order]
    qrs = {}
    if follow_url:
        for scr in decks["straight"]:
            qrs[scr["id"]] = qr_svg(f"{follow_url}#{scr['id']}")
    return (TEMPLATE
            .replace("__TITLE__", html.escape(title))
            .replace("__FOOTER__", footer)
            .replace("__DECKS__", json.dumps(decks, ensure_ascii=False, indent=1))
            .replace("__VOICES__", json.dumps(voices, ensure_ascii=False))
            .replace("__UNVOICED__", json.dumps(list(UNVOICED)))
            .replace("__QRS__", json.dumps(qrs, ensure_ascii=False))
            .replace("__FOLLOW_URL__", json.dumps(follow_url)))


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
    ap.add_argument("--voice", action="append", default=[], metavar="NAME=PATH",
                    help="a character-voice payload; repeatable. Same schema, same validation.")
    ap.add_argument("--follow-url", default=DEFAULT_FOLLOW_URL,
                    help="base URL of the published deck; each screen shows a QR to its own "
                         "anchor so the room can follow along. Empty string disables it.")
    ap.add_argument("--check", action="store_true",
                    help="validate the payload and exit; write nothing")
    ap.add_argument("--engine", default="",
                    help="what produced this payload, shown in the deck's provenance note")
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
        if args.check:
            return 2
        if out.exists():
            print(f"REJECTED: {out} left untouched. The previous deck still stands.", file=sys.stderr)
        else:
            print(f"REJECTED: no deck at {out} to fall back to. Run seed.sh.", file=sys.stderr)
        return 2

    if args.check:
        return 0

    over, total = reference_report(data)
    if over:
        detail = ", ".join(f"{sid} ({n})" for sid, n in over)
        print(f"NOTE: more than one Star Wars reference on a screen: {detail}. "
              f"{total} in the deck overall. The brief asks for at most one per screen; "
              f"cut the weaker one before presenting.", file=sys.stderr)

    for warning in CLAMPED:
        print(f"CLAMPED: {warning}", file=sys.stderr)

    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    decks = {"straight": build(data, args.mode, generated_at, args.engine)}
    order = ["straight"]

    # A voice is just another payload. It goes through the identical validator, and a
    # voice that fails is dropped rather than taking the deck down with it: the straight
    # version is the deck, and the voices are a party trick layered on top of it.
    for spec in args.voice:
        name, _, path = spec.partition("=")
        name = name.strip().lower()
        if not name or not path:
            print(f"REJECTED: --voice {spec!r} is not NAME=PATH", file=sys.stderr)
            return 2
        try:
            vdata = validate(extract_json(pathlib.Path(path).read_text()), sources)
        except (ValidationError, OSError) as exc:
            print(f"DROPPED voice {name}: {exc}", file=sys.stderr)
            continue
        div = voice_divergence(data, vdata)
        if div < 0.6:
            print(f"WARNING voice {name}: only {div:.0%} of fields were actually rewritten. "
                  f"This reads as the straight deck with a few words moved, which is not "
                  f"worth a button. Strengthen voices/{name}.md and re-run.", file=sys.stderr)
        lost = numbers_lost(data, vdata)
        if lost:
            print(f"WARNING voice {name}: these figures are in the straight deck but not "
                  f"in this voice: {', '.join(lost)}. Check the slides before presenting it.",
                  file=sys.stderr)
        decks[name] = build(vdata, args.mode, generated_at, args.engine)
        order.append(name)

    screens = decks["straight"]

    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        out.with_suffix(out.suffix + ".prev").write_text(out.read_text())
    tmp = out.with_suffix(out.suffix + ".tmp")
    tmp.write_text(render_html(decks, order, args.mode, generated_at, args.follow_url))
    tmp.replace(out)

    live = sum(1 for s in data["stations"] if s["source"] == "transcript")
    print(f"Deck written to {out}")
    print(f"  {len(screens)} screens, {live}/5 stations from a real transcript, mode={args.mode}")
    if live < 5:
        fb = [s["name"] for s in data["stations"] if s["source"] == "fallback"]
        print(f"  flagged as fallback on screen: {', '.join(fb)}")
    if CLAMPED:
        print(f"  {len(CLAMPED)} field(s) trimmed to fit the layout")
    if len(order) > 1:
        print(f"  voices: {', '.join(order[1:])} (press 1-{len(order)} or V while presenting)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
