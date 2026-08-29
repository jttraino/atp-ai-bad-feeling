# Your AI Program Has a Bad Feeling About This

Public archive for the ATP event "Your AI Program Has a Bad Feeling About This." It's an interactive workshop on why enterprise AI initiatives fail, run as the honest, hands-on debrief nobody runs at their own company.

- **Date:** September 17, 2026 ABY, 6:00 to 8:00 PM
- **Location:** Social House Roswell, 1098 Green St, Roswell, GA 30075
- **Details / registration:** https://atpconnect.org/events/your-ai-program-has-a-bad-feeling-about-this/
- **Jedi Council:** Scott Harris (One Inc, ATP Finance Chair), Tom Laswell (DC BLOX, ATP Director of Technology), John Slaughter (Alliant Health, ATP Executive Advisory Board)
- **Fleet Command:** John Trainor (Four Technologies, ATP Executive Advisory Board)

<p align="center"><img src="assets/repo-qr-code.png" alt="QR code linking to this repo" width="200"></p>

Scan the QR code above to come back to this repo after the event. It's also displayed at the event itself, where you'll find the base transcripts and the closing keynote talking points.

## Format

Attendees split into five themed bases (about 25 people each), each covering a distinct way enterprise AI programs go wrong:

| Base | Theme |
|---|---|
| [Sky City](bases/sky-city/) | Infrastructure and integration challenges with third-party tools |
| [Swamp Planet](bases/swamp-planet/) | Technical debt and data quality issues |
| [Ice Planet](bases/ice-planet/) | Development-stage use cases stuck in limbo |
| [Snow Monster Cave](bases/snow-monster-cave/) | Unexpected costs and security vulnerabilities |
| [Asteroid Field](bases/asteroid-field/) | Compliance, legal obstacles, and scope creep |

Each base runs its own talk. Fleet Command hosts, records, and transcribes it via an independent Teams meeting, not the speaker. No one in any single base gets the full picture. That's the point of what comes next.

Immediately afterward, the group reassembles for **Fully Operational**, the closing keynote. It has the high ground: the one vantage point that actually sees the patterns across all five bases at once, distilled into shared talking points. See [`keynote/`](keynote/).

This repo documents the full method, not just the output. That includes [how Fully Operational's talking points were actually synthesized](tools/synthesize-keynote/) from the five base transcripts, in the few minutes between sessions ending and the group reassembling.

## Contents

- [`speaker-instructions.md`](speaker-instructions.md): what base speakers needed to prepare and run their session
- [`coordinator-checklist.md`](coordinator-checklist.md): Fleet Command's runbook for hosting, recording, and monitoring all five bases, and running the closing synthesis
- `bases/`: transcript and notes per base, added after the event
- `keynote/`: Fully Operational, the synthesized closing keynote talking points, added after the event
- [`tools/synthesize-keynote/`](tools/synthesize-keynote/): the tool and guiding framework used to turn the five transcripts into the keynote draft

## Contributing

Pull requests are welcome. Corrections to a transcript, additional context on a base's topic, or your own notes if you were in the room are all fair game. This is meant to be a living record of the event, not a frozen archive.
