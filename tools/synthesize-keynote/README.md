# Keynote Synthesis Tool

This is the actual tool used to turn the five station transcripts into the closing keynote talking points, in near real time between the stations ending and the group reassembling. It's checked in here so the whole process — not just the resulting content — is visible.

## How it fits into the event flow

1. All five stations run in parallel, each recorded and transcribed via a coordinator-hosted Teams meeting (see [`../../speaker-instructions.md`](../../speaker-instructions.md)).
2. As each session wraps, its exported transcript is dropped into `stations/<name>/transcript.md` (or `.txt`/`.docx`) in this repo.
3. Run `./synthesize.sh` from anywhere — it reads whatever's currently in `stations/*/`, combines it with the guiding brief in [`framework.md`](framework.md), and calls the `claude` CLI to produce a first-draft `keynote/talking-points-draft.md`.
4. The keynote speaker skims and adapts that draft live, rather than starting from a blank page with five minutes to go.

## Usage

```bash
./synthesize.sh
```

Requires the `claude` CLI installed and logged in. If `pandoc` is installed, `.docx` transcripts are also accepted; otherwise export/paste the transcript as plain text into `transcript.md`.

## Fallback behavior

If a station's transcript wasn't captured for any reason, the script falls back to that speaker's pre-submitted outline (`outline.md`) instead, and the output explicitly flags that station as using a fallback rather than presenting it as equivalent to a real transcript. A station with neither a transcript nor an outline is reported as missing so it isn't silently dropped from the keynote.

## Why this is public

The point of this repo is not just to archive what was said at each station, but to show how the entire event — from speaker logistics to the closing synthesis — was actually put together, so anyone running a similar event can see (and reuse) the method.
