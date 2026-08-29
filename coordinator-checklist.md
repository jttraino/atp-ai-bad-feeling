# Fleet Command Checklist, ATP Event, September 17, 2026 ABY

Fleet Command hosts and records every base's Teams meeting, monitors all five during the event, and runs the keynote synthesis in the window before Fully Operational, the closing keynote. This is that role's runbook.

## Before the event

- [ ] Schedule 5 independent Teams meetings, one per base, sometime before the event. No Team or channel structure needed, just standalone calendar invites.
- [ ] For each meeting, confirm it does not require lobby admission (this account doesn't default to it, but verify per meeting).
- [ ] Send each speaker their base's individual meeting link.
- [ ] Arrange a dry-run time with each speaker. This comes from them reaching out, but chase anyone who hasn't with time to spare before the event.

## Dry run, mandatory, per speaker, ideally a week or more out

- [ ] Join the speaker's actual meeting link with them at the scheduled test time.
- [ ] Confirm they get in with no lobby or waiting room.
- [ ] Confirm their audio (built-in mic or personal mic) is clear.
- [ ] Confirm their laptop is plugged into power and won't go to sleep mid-session.
- [ ] If they're running a backup recorder on the same computer as Teams, confirm it doesn't conflict with Teams (microphone access, especially).
- [ ] Start recording and transcription. Confirm both actually capture correctly.
- [ ] Note any fixes needed (mic, connection, anything) and resolve before September 17. This is the same link and setup used on the day.

## Collecting speaker notes, the backup plan

- [ ] Collect each speaker's talk outline or abstract as soon as they have anything, even a rough draft. Save it into `bases/<name>/outline.md` in this repo. Hard deadline: day before the event. Push for it earlier since it's what makes the fallback plan actually work if a recording fails.
- [ ] Once outlines start coming in, test `tools/synthesize-keynote/synthesize.sh` against them (as stand-in fallback content) to confirm the framework produces usable output. Tune `framework.md` now, not on the day.

## Day before / morning of

Fleet Command's table is the cockpit for the day. It needs a working hyperdrive (Wi-Fi) and a steady power core, or nobody's making the jump to lightspeed.

- [ ] Confirm venue Wi-Fi and power availability at Fleet Command's table (Social House Roswell). Bring a mobile hotspot too, but only as a backup. It is not the primary connection.
- [ ] Kit: laptop plus charger, hotspot plus charged battery pack, headphones, all 5 meeting links pinned or bookmarked.
- [ ] Open all 5 meetings and re-confirm no lobby is configured.
- [ ] Print the QR code (`assets/repo-qr-code.png`) as signage, large enough to scan from a few feet away, and place it prominently so attendees can find the repo after the event.

## As each base kicks off

- [ ] Han shot first. So should you. Click **Start recording and transcription** the moment the room settles, then leave. It keeps running without you.
- [ ] Mark it on the tracker below.
- [ ] At some point mid-session, quietly spot-check audio (headphones) to confirm it's actually being captured.

| Base | Recording started | Audio spot-checked |
|---|---|---|
| Sky City | ☐ | ☐ |
| Swamp Planet | ☐ | ☐ |
| Ice Planet | ☐ | ☐ |
| Snow Monster Cave | ☐ | ☐ |
| Asteroid Field | ☐ | ☐ |

## As each base wraps

- [ ] Confirm the meeting ended. Recording stops automatically once everyone's left.
- [ ] No Bothans required to smuggle this one in. The transcript already lives on Fleet Command's own machine. Export it and drop it into `bases/<name>/transcript.md` in this repo.
- [ ] Mark it on the tracker below.

| Base | Transcript captured | Notes (e.g. fallback needed) |
|---|---|---|
| Sky City | ☐ | |
| Swamp Planet | ☐ | |
| Ice Planet | ☐ | |
| Snow Monster Cave | ☐ | |
| Asteroid Field | ☐ | |

## In the gap before Fully Operational

**SLA: 5 minutes, or 12 parsecs, whichever comes first.** Never tell me the odds. This is the tightest part of the day by design, and the whole point of preparing everything above.

- [ ] Run `./tools/synthesize-keynote/synthesize.sh`.
- [ ] Check its warnings for any base using a fallback outline instead of a real transcript, or missing entirely.
- [ ] Open `keynote/talking-points-draft.md` in Obsidian. This is not an automated slide deck. Fleet Command presents it live, clicking through by hand, adapting on the fly rather than reading it verbatim.

## If something fails mid-session

"In my experience, there's no such thing as luck." That's why there are three independent layers under each base, not one:

- Recording or transcription didn't start, or stopped: rejoin and restart it. The meeting is still running.
- Teams fails entirely for a base: fall back to the speaker's backup recording (per [`speaker-instructions.md`](speaker-instructions.md)) as the audio source.
- No usable audio at all: "I find your lack of transcript disturbing." But the synthesis script automatically falls back to that speaker's pre-submitted `outline.md` and flags it as such, so the base still appears in the keynote, just clearly marked as not sourced from a transcript.

## After the event

- [ ] Commit and push the final transcripts and the keynote draft to this repo.
