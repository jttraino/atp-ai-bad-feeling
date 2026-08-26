# Keynote Synthesis Tool

This is the actual tool used to turn the five base transcripts into Fully Operational's talking points, in near real time between the bases ending and the group reassembling. It's checked in here so the whole process, not just the resulting content, is visible.

## How it fits into the event flow

1. All five bases run in parallel, each recorded and transcribed via a Fleet-Command-hosted Teams meeting (see [`../../speaker-instructions.md`](../../speaker-instructions.md)).
2. As each session wraps, its exported transcript is dropped into `bases/<name>/transcript.md` (or `.txt`/`.docx`) in this repo.
3. Run `./synthesize.sh` from anywhere. It reads whatever's currently in `bases/*/`, combines it with the guiding brief in [`framework.md`](framework.md), and calls the `claude` CLI to produce a first-draft `keynote/talking-points-draft.md`.
4. Fleet Command opens that draft in Obsidian and presents Fully Operational live, clicking through the markdown by hand. It's not an automated slide deck, it's a head start on the five minutes it would otherwise take to build one from a blank page.

## Usage

```bash
./synthesize.sh
```

Requires the `claude` CLI installed and logged in. If `pandoc` is installed, `.docx` transcripts are also accepted. Otherwise export or paste the transcript as plain text into `transcript.md`.

## Fallback behavior

If a base's transcript wasn't captured for any reason, the script falls back to that speaker's pre-submitted outline (`outline.md`) instead, and the output explicitly flags that base as using a fallback rather than presenting it as equivalent to a real transcript. A base with neither a transcript nor an outline is reported as missing so it isn't silently dropped from the keynote.

## Why this is public

The point of this repo is not just to archive what was said at each base. It's to show how the entire event, from speaker logistics to the closing synthesis, was actually put together, so anyone running a similar event can see, and reuse, the method.
