# Coordinator Checklist — ATP Event, Sept 17, 2026

The coordinator hosts and records every station's Teams meeting, monitors all five during the event, and runs the keynote synthesis in the window between sessions ending and the closing keynote. This is that person's runbook.

## Weeks out

- [ ] Schedule 5 independent Teams meetings, one per station, at the correct times — no Team/channel structure needed, just standalone calendar invites.
- [ ] For each meeting, confirm it does not require lobby admission (this coordinator's account doesn't default to it, but verify per meeting).
- [ ] Send each speaker their station's individual meeting link.
- [ ] Arrange a dry-run time with each speaker — this comes from them reaching out, but chase anyone who hasn't by ~10 days out.

## Dry run — mandatory, per speaker, ideally a week or more out

- [ ] Join the speaker's actual meeting link with them at the scheduled test time.
- [ ] Confirm they get in with no lobby/waiting room.
- [ ] Confirm their audio (built-in mic or personal mic) is clear.
- [ ] Start recording + transcription; confirm both actually capture correctly.
- [ ] Note any fixes needed (mic, connection, anything) and resolve before Sept 17 — this is the same link/setup used on the day.

## Collecting speaker notes (the backup plan)

- [ ] Collect each speaker's talk outline/abstract as soon as they have anything, even a rough draft; save into `stations/<name>/outline.md` in this repo. **Hard deadline: day before the event** — but push for it earlier, since it's what makes the fallback plan actually work if a recording fails.
- [ ] Once outlines start coming in, test `tools/synthesize-keynote/synthesize.sh` against them (as stand-in fallback content) to confirm the framework produces usable output — tune `framework.md` now, not on the day.

## Day before / morning of

The coordinator table is the cockpit for the day — it needs a working hyperdrive (Wi-Fi) and a steady power core, or nobody's making the jump to lightspeed.

- [ ] Confirm venue Wi-Fi and power availability at the coordinator table (Social House Roswell) — bring a mobile hotspot as backup regardless.
- [ ] Coordinator kit: laptop + charger, hotspot + charged battery pack, headphones, all 5 meeting links pinned/bookmarked.
- [ ] Open all 5 meetings and re-confirm no lobby is configured.
- [ ] Print the QR code (`assets/repo-qr-code.png`) as signage — large enough to scan from a few feet away — and place it prominently so attendees can find the repo after the event.

## As each station kicks off

- [ ] Han shot first — so should you: click **Start recording and transcription** the moment the room settles, then leave — it keeps running without you.
- [ ] Mark it on the tracker below.
- [ ] At some point mid-session, quietly spot-check audio (headphones) to confirm it's actually being captured.

| Station | Recording started | Audio spot-checked |
|---|---|---|
| Cloud City | ☐ | ☐ |
| Dagobah | ☐ | ☐ |
| Hoth | ☐ | ☐ |
| The Wampa Cave | ☐ | ☐ |
| The Asteroid Field | ☐ | ☐ |

## As each station wraps

- [ ] Confirm the meeting ended (recording stops automatically once everyone's left).
- [ ] Export the transcript and drop it into `stations/<name>/transcript.md` in this repo.
- [ ] Mark it on the tracker below.

| Station | Transcript captured | Notes (e.g. fallback needed) |
|---|---|---|
| Cloud City | ☐ | |
| Dagobah | ☐ | |
| Hoth | ☐ | |
| The Wampa Cave | ☐ | |
| The Asteroid Field | ☐ | |

## In the gap before the closing keynote

**SLA: 5 minutes, or 12 parsecs — whichever comes first.** Never tell me the odds; this is the tightest part of the day by design, and the whole point of preparing everything above.

- [ ] Run `./tools/synthesize-keynote/synthesize.sh`.
- [ ] Check its warnings — any station using a fallback outline instead of a real transcript, or missing entirely.
- [ ] Skim `keynote/talking-points-draft.md`; adapt live rather than reading it verbatim.

## If something fails mid-session

- Recording/transcription didn't start or stopped: rejoin, restart it — the meeting is still running.
- Teams fails entirely for a station: fall back to the speaker's phone voice memo (per [`speaker-instructions.md`](speaker-instructions.md)) as the audio source.
- No usable audio at all: "I find your lack of transcript disturbing" — but the synthesis script automatically falls back to that speaker's pre-submitted `outline.md` and flags it as such, so the station still appears in the keynote, just clearly marked as not sourced from a transcript.

## After the event

- [ ] Commit and push the final transcripts and the keynote draft to this repo.
