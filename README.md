# Your AI Program Has a Bad Feeling About This

Public archive for the ATP event **"Your AI Program Has a Bad Feeling About This"** — an interactive workshop on why enterprise AI initiatives fail, run as the honest, hands-on debrief nobody runs at your own company.

- **Date:** September 17, 2026, 6:00–8:00 PM
- **Location:** Social House Roswell, 1098 Green St, Roswell, GA 30075
- **Details / registration:** https://atpconnect.org/events/your-ai-program-has-a-bad-feeling-about-this/
- **Event leads:** Scott Harris (One Inc, ATP Finance Chair), Tom Laswell (DC BLOX, ATP Director of Technology), John Slaughter (Alliant Health, ATP Executive Advisory Board)
- **Coordinator:** John Trainor (Four Technologies, ATP Executive Advisory Board)

<p align="center"><img src="assets/repo-qr-code.png" alt="QR code linking to this repo" width="200"></p>

Scan the QR code above (also displayed at the event) to come back to this repo after the event for the station transcripts and closing keynote talking points.

## Format

Attendees split into five themed stations (~25 people each), each covering a distinct way enterprise AI programs go wrong:

| Station | Theme |
|---|---|
| [Cloud City](stations/cloud-city/) | Infrastructure and integration challenges with third-party tools |
| [Dagobah](stations/dagobah/) | Technical debt and data quality issues |
| [Hoth](stations/hoth/) | Development-stage use cases stuck in limbo |
| [The Wampa Cave](stations/the-wampa-cave/) | Unexpected costs and security vulnerabilities |
| [The Asteroid Field](stations/the-asteroid-field/) | Compliance, legal obstacles, and scope creep |

Each station runs its own talk/discussion, recorded and transcribed via an independent Teams meeting hosted and monitored by an event coordinator (rather than the station speakers). No one in any single station gets the full picture — that's the point of what comes next. Immediately afterward, the group reassembles for a closing keynote that has the high ground: the one vantage point that actually sees the patterns across all five at once, distilled into shared talking points — see [`keynote/`](keynote/).

This repo documents the full method, not just the output — including [how the closing keynote talking points were actually synthesized](tools/synthesize-keynote/) from the five station transcripts in the few minutes between sessions ending and the group reassembling.

## Contents

- [`speaker-instructions.md`](speaker-instructions.md) — what station speakers needed to prepare and run their session
- [`coordinator-checklist.md`](coordinator-checklist.md) — the event coordinator's runbook for hosting, recording, and monitoring all five stations, and running the closing synthesis
- `stations/` — transcript and notes per station, added after the event
- `keynote/` — the synthesized closing keynote talking points, added after the event
- [`tools/synthesize-keynote/`](tools/synthesize-keynote/) — the tool and guiding framework used to turn the five transcripts into the keynote draft

## Contributing

Pull requests are welcome — corrections to a transcript, additional context on a station's topic, or your own notes if you were in the room are all fair game. This is meant to be a living record of the event, not a frozen archive.
