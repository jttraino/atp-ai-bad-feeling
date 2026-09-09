# Fleet Command Checklist, ATP Event, September 17, 2026 ABY

Fleet Command hosts and records every base's Teams meeting, monitors all five during the event, and runs the keynote synthesis in the window before the Throne Room, the closing keynote. This is that role's runbook.

## Before the event

- [ ] Schedule 5 independent Teams meetings, one per base, sometime before the event. No Team or channel structure needed, just standalone calendar invites.
- [ ] For each meeting, confirm it does not require lobby admission (this account doesn't default to it, but verify per meeting).
- [ ] Send each speaker their base's individual meeting link.
- [ ] **Book all five dry runs live during the prep meeting on Monday, September 14.** Waiting on speakers to reach out did not work: zero of five had booked by the 8th. Have your own calendar open in that meeting, get everyone to open theirs, and send the invites on the spot before anyone leaves. Slots run the 14th through the 16th.

## Dry run, mandatory, per speaker, 15 minutes

- [ ] Join the speaker's actual meeting link with them at the scheduled test time.
- [ ] Confirm they get in with no lobby or waiting room.
- [ ] **Confirm Teams noise suppression is set to Off, not Auto** (Settings > Devices > Noise suppression). This is the setting the whole capture depends on. Auto is tuned to isolate a single voice at a desk and will strip out the room discussion.
- [ ] Have them walk a few steps away from the laptop and talk at normal volume, the way an attendee in the room will. That, not their close-up voice, is the audio that has to survive. Since the speaker is the one asking questions, their own voice was never the thing at risk.
- [ ] Confirm the laptop is theirs, that they know its password, and that they can change their own settings. A donor laptop that nobody can unlock is the most likely single point of failure on the day.
- [ ] Confirm the laptop is plugged into power and won't sleep or lock mid-session.
- [ ] Ask whether they run their own recorder or transcription service, and encourage it if they do. Confirm two things. First, **it's a completely different device**, not a second app on the laptop already running Teams: same microphone, same spot, same power and sleep and lock failures, plus a real chance the two fight over microphone access and take out the primary. Second, that they can actually export and email the file to john@johntrainor.com within minutes of their session ending. A login wall, a manual export step, or an unpredictable processing queue makes it unusable as backup. Better to know that now than to be waiting on it during the synthesis window.
- [ ] Start recording and transcription. Confirm both actually capture correctly.
- [ ] Walk them through **ending** the meeting rather than leaving it, and why.
- [ ] Note any fixes needed (mic, connection, anything) and resolve before September 17. This is the same link and setup used on the day.

## Collecting questions, the backup plan

Each base runs as a guided discussion off a list of roughly eight questions. Tom Lasswell is drafting those lists, since the speakers asked him to rather than writing their own. The question list, with likely answers pre-filled against it, is the fallback that stands in for a base whose transcript fails.

- [ ] Collect each base's question list as soon as it exists, even in draft. Save it into `bases/<name>/questions.md` in this repo.
- [ ] Chase the speakers for their final, reviewed version by **Tuesday, September 15**. Wednesday is workable. Thursday morning is the outer edge, and still fine to absorb, since integrating a late list is cheap. An absent list is not.
- [ ] Pre-fill likely answers against each base's questions and keep them in `questions.md` alongside the questions themselves. This is the actual work that makes the fallback usable, and it has to be done before the day.
- [ ] Once lists start coming in, test `tools/synthesize-keynote/synthesize.sh` against them (as stand-in fallback content) to confirm the framework produces usable output. Tune `framework.md` now, not on the day.

## Day before / morning of

Fleet Command's table is the cockpit for the day. It needs a working hyperdrive (Wi-Fi) and a steady power core, or nobody's making the jump to lightspeed.

- [ ] Confirm venue Wi-Fi and power availability at Fleet Command's table (Social House Roswell). Bring a mobile hotspot too, but only as a backup. It is not the primary connection.
- [ ] Kit: laptop plus charger, hotspot plus charged battery pack, headphones, all 5 meeting links pinned or bookmarked.
- [ ] Open all 5 meetings and re-confirm no lobby is configured.
- [ ] Print the QR code (`assets/repo-qr-code.png`) as signage, large enough to scan from a few feet away, and place it prominently so attendees can find the repo after the event.

## Arrival and setup

- [ ] **Fleet Command on site at 5:00 PM.** Speakers are called for 5:15, which is the window for setting up their laptops, confirming noise suppression is off, and running a live test meeting on the actual venue Wi-Fi before the room fills.
- [ ] Assign the five **Astromechs** on arrival, one per base, and brief them (see below). These can be ATP volunteers drafted that evening. Confirm with Kyle, ATP's volunteer coordinator, that anyone assigned to Fleet Command is coordinated through him rather than reporting in two directions.
- [ ] **Padawan: William.** Fleet Command's runner for the evening, briefed on the full program and able to be pointed at any problem without further explanation. Registered through Kyle, working directly with Fleet Command.
- [ ] Tom Lasswell is day-of tech support and the backup on any laptop that misbehaves.
- [ ] Scott Harris is the timekeeper. Everything in the synthesis window below depends on the bases actually ending when they're called.

### Briefing the Astromechs

One per base. R2 rode in the socket watching the systems so the pilot could fly, which is exactly this job: the speaker runs the room, the Astromech watches the machine.

- [ ] Recording is running, and the **live transcript is visibly building** in Teams. This is the real tell that capture is working, and it's visible in the Teams UI without interrupting anything.
- [ ] Laptop is plugged in, awake, and unlocked. Power, sleep, and lock are the three failure modes.
- [ ] Network hasn't dropped.
- [ ] **If the speaker brought a second device, work the room with it.** The laptop is fixed in place and straining to hear; a handheld carried toward whoever is speaking captures exactly what the primary can't. This is an active job, not a passive one. Then make sure it gets emailed to john@johntrainor.com before anyone leaves.
- [ ] If anything looks wrong, get Tom or Fleet Command. Don't try to fix it mid-discussion.

## As each base kicks off

- [ ] Han shot first. So should you. Click **Start recording and transcription** the moment the room settles, then leave. It keeps running without you.
- [ ] Record audio only, not video. Nobody needs the video, and audio-only measurably speeds up transcript generation, which is the whole constraint in the synthesis window.
- [ ] Mark it on the tracker below.
- [ ] At some point mid-session, quietly spot-check audio (headphones) to confirm it's actually being captured.

| Base | Astromech assigned | Recording started | Audio spot-checked |
|---|---|---|---|
| Sky City | ☐ | ☐ | ☐ |
| Swamp Planet | ☐ | ☐ | ☐ |
| Ice Planet | ☐ | ☐ | ☐ |
| Snow Monster Cave | ☐ | ☐ | ☐ |
| Asteroid Field | ☐ | ☐ | ☐ |

## As each base wraps

- [ ] **Confirm the meeting was ended, not just left.** Ending the meeting is what triggers Teams to finalize the session and generate the transcript. A speaker who closes their laptop or hits Leave has not started that clock. As meeting owner, Fleet Command can end any of the five directly, so sweep all five as the sessions wrap rather than assuming.
- [ ] No Bothans required to smuggle this one in. The transcript already lives on Fleet Command's own machine. Export it and drop it into `bases/<name>/transcript.md` in this repo.
- [ ] Mark it on the tracker below.

| Base | Transcript captured | Notes (e.g. fallback needed) |
|---|---|---|
| Sky City | ☐ | |
| Swamp Planet | ☐ | |
| Ice Planet | ☐ | |
| Snow Monster Cave | ☐ | |
| Asteroid Field | ☐ | |

## In the gap before the Throne Room

**Measured worst case: about 8 minutes from last base ending to a presentable draft.** Never tell me the odds. Where that number comes from, tested repeatedly on real 45-minute meetings at the same time of day:

- 2.5 to 5 minutes for Teams to generate a single transcript once the meeting is ended. Five minutes was the worst observed, audio-only.
- The five bases won't end simultaneously. Assume a couple of minutes of stagger, which puts the last transcript landing around 7 minutes after the first base wraps.
- About 1 minute to run the synthesis and have a draft open.

That 8 minutes has to be absorbed by the run of show while the room moves back to the keynote area. **Adjust this section against the real run of show once Scott and Tom have it**, since it's the one number here that depends on somebody else's document.

- [ ] Run `./tools/synthesize-keynote/synthesize.sh`.
- [ ] Check its warnings for any base using its fallback question list instead of a real transcript, or missing entirely.
- [ ] Open `closing-keynote/talking-points-draft.md` in Obsidian. This is not an automated slide deck. Fleet Command presents it live, clicking through by hand, adapting on the fly rather than reading it verbatim.

## If something fails mid-session

"In my experience, there's no such thing as luck." That's why there are three independent layers under each base, not one:

- Recording or transcription didn't start, or stopped: rejoin and restart it. The meeting is still running. This is what the Astromechs are watching for.
- Teams fails entirely for a base: fall back to the speaker's second device, if they brought one, emailed to john@johntrainor.com as the session ends. Where the Astromech carried it around the room, this may actually be the better capture of the two.
- No usable audio at all: "I find your lack of transcript disturbing." But the synthesis script automatically falls back to that base's `questions.md`, the question list plus pre-filled likely answers, and flags it as such, so the base still appears in the keynote, clearly marked as not sourced from a transcript. An older code, sir, but it checks out.

## Crew manifest

- [ ] Keep [`crew-manifest.md`](crew-manifest.md) current. It's the single list of who holds which role, and its real job is making the unfilled rows obvious while there's still time to fill them.

## Approaches considered and rejected

Recorded here because the repo is meant to document the method, and because these are the first three things anyone else planning this will reach for.

- **Dedicated microphones, lapel or wireless, per base, feeding Teams.** Rejected. It means either buying gear or depending on five speakers to each own, understand, and correctly connect a mic, and on most laptops a decent mic means USB and driver roulette. The upside was real, but the format is a room discussion where the biggest win comes from disabling noise suppression, not from a better capsule near the speaker's mouth. Note the distinction from a speaker's own separate recorder, which is encouraged: the objection is to extra gear in the primary capture path, not to independent insurance sitting alongside it.
- **A phone joining the meeting as a roving handheld mic, passed around by a runner.** Rejected, and it was the most tempting one, because a passed handheld is what an audience instinctively understands. But it means two live audio sources per base, which means mute and unmute management during a discussion, crosstalk between the two feeds, and a transcript with overlapping speakers. It traded a capture problem for a coordination problem.
- **Speakers writing their own questions.** Not so much rejected as declined by the speakers, all of whom asked for the questions to be written for them. Worth naming because the plan assumed otherwise, and the whole fallback design had to change once the question lists became a central artifact rather than a speaker's private notes.

## After the event

- [ ] Commit and push the final transcripts and the keynote draft to this repo.
