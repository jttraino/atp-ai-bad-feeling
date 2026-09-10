# Keynote Synthesis

The tool that turns the five station transcripts into the Throne Room deck, in the few minutes between the stations ending and the group reassembling. Checked in here so the whole process, not just the resulting content, is visible.

```bash
tools/synthesize-keynote/seed.sh          # days before: build the floor from question lists
tools/synthesize-keynote/synthesize.sh    # on the night: rebuild from whatever has arrived
```

Both write `closing-keynote/presentation.html`. Both are safe to re-run as often as you like.

## How it fits into the event

1. **Days before.** Question lists land in `stations/<name>/questions.md`, each with pre-filled likely answers. `seed.sh` builds a complete, presentable deck from them, with every station marked as a fallback. From this point on there is always a deck. Nothing that happens on the night can leave Fleet Command in front of the room with nothing.
2. **On the night.** As each station wraps, its transcript is filed by [`tools/intake-transcript/`](../intake-transcript/) into `stations/<name>/transcript.md`.
3. **In the gap.** `synthesize.sh` reads whatever is currently there, prefers a real transcript over a question list per station, asks the model for structured content, validates it, and rebuilds the deck.
4. **Presenting.** Open the HTML in a browser. Arrow keys or Next. Fleet Command drives it live and adapts; it is not read verbatim.

Per station, in priority order: `transcript.md` / `transcript.txt`, then `transcript.docx` via pandoc, then `questions.md` as the flagged fallback. A station with none of those is a hard error, because a deck that silently drops a station is worse than no deck.

## What the model is and isn't asked for

It gets the transcripts and the brief in [`framework.md`](framework.md), and it returns **JSON, not a deck**. No HTML, no formatting, no slide order, and specifically not which stations had a real transcript, because that is already known from disk. The deck is assembled from that JSON by [`tools/build-deck/`](../build-deck/), which rejects anything that doesn't fit the schema and leaves the existing deck in place when it does.

The prompt is piped on **stdin**, not passed as an argument. Five real 45-minute transcripts come to about 285KB, and Linux caps a single argv string at 128KB, so the obvious `-p "$(cat ...)"` works in every small test and fails only when the transcripts are full length. Which is to say, only on the night. See [`tests/README.md`](../../tests/README.md).

## Timing

Measured, not estimated, against five full-length transcripts with the real CLI:

| Step | Measured |
|---|---|
| Teams generating one transcript after a meeting is **ended** | 2.5 to 5 min |
| Five staggered endings, last transcript in hand | ~7 min |
| Primary model call | **69 s to 167 s** |
| Standby model call (haiku), same 290KB prompt, alone | **81 s** |
| Standby model call, running concurrently with the primary | **~138 s** |
| Validation and deck build | < 1 s |

Call it ten minutes end to end, worst case.

The model call is the part worth understanding. Real runs came in at 69, 81, 102, 105 and 167 seconds, and **the slowest was on the smallest input**. Latency varies more than twofold run to run and is not driven by transcript length, so plan against the slow end and not the median. Re-measure any time with `REAL_MODEL=1 tests/rehearse.sh fullsize`.

## The hedge: two models, in parallel, not a race

Two requests go out at once. The primary gets the whole deadline to itself; the standby is only used if the primary misses it or comes back unusable.

```
PRIMARY_MODEL=""       the CLI default
FAST_MODEL=haiku       empty string disables the hedge entirely
DEADLINE_S=180         how long the primary gets
GRACE_S=45             extra time to wait for the standby after that
```

**Why not a race.** Taking whichever finishes first means presenting the weaker deck any time the standby happens to land a few seconds earlier, which on these measurements is most of the time. Quality is the thing we are protecting; the deadline is the thing we are insuring against.

**Why not a sequential retry.** A serial fallback burns the primary's entire deadline before the standby even starts. At the measured numbers that is 180 seconds gone, then 81 more. Running them together caps the worst case at roughly the deadline.

**What it actually buys**, in order of how likely you are to need it:

1. **Tail latency.** Two calls go slow independently, so it takes two bad draws to hurt you.
2. **A second attempt at valid output** if the primary returns something the schema rejects.
3. **Nothing at all** if the venue network is down or the account is rate limited. Both paths share those. That is what the seeded deck is for, and it is why the hedge does not replace it.

**It is not free.** Haiku answered the same prompt in 81 seconds alone and about 138 seconds while the primary was running beside it. Two concurrent calls slow each other down, so the standby is insurance against a bad draw, not a fast lane you can count on to beat the deadline by itself. `GRACE_S` exists precisely because the standby can land after the deadline it was meant to cover, and in the live test it did.

**The deck says which one wrote it.** If the standby carried the room, the provenance line on the method screen says so. Same principle as the fallback banners: the failure to fear is not a worse answer, it is a worse answer that looks identical to a better one.

This gives three rungs, each one presentable on its own: the primary model, the standby on the same real transcripts, and the seeded deck built from question lists days earlier.

## Requires

The `claude` CLI, logged in. `pandoc` for `.docx` transcripts. Python 3 for the builder and validator.
