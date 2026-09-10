#!/usr/bin/env bash
# Builds the Throne Room deck from whatever is currently sitting in stations/*/,
# and writes it to closing-keynote/presentation.html.
#
# For each station, in priority order, it uses:
#   1. transcript.md / transcript.txt   the real transcript, plain text
#   2. transcript.docx                  converted via pandoc, if pandoc is installed
#   3. questions.md                     the question list plus pre-filled likely answers,
#                                        used as a fallback if no transcript was captured
# A station with none of the above is a hard error: we do not ship a deck that
# silently drops a station.
#
# The model is asked for JSON, not for a deck. The JSON is validated against a
# schema before anything is rendered, and a run that fails validation leaves the
# existing deck exactly where it was.
#
# Env:
#   CLAUDE_BIN   model CLI to invoke (default: claude)
#   MODE         live | seeded  (default: live)
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
STATIONS_DIR="$REPO_ROOT/stations"
FRAMEWORK="$REPO_ROOT/tools/synthesize-keynote/framework.md"
BUILDER="$REPO_ROOT/tools/build-deck/build_deck.py"
OUT_FILE="$REPO_ROOT/closing-keynote/presentation.html"
CLAUDE_BIN="${CLAUDE_BIN:-claude}"
MODE="${MODE:-live}"

STATION_IDS=(sky-city swamp-planet ice-planet snow-monster-cave asteroid-field)

started=$(date +%s)
combined="$(mktemp)"; payload="$(mktemp)"
trap 'rm -f "$combined" "$payload"' EXIT

missing=(); fallback=(); live=(); declare -A SOURCE_OF

for name in "${STATION_IDS[@]}"; do
  dir="$STATIONS_DIR/$name"
  content=""; source_note=""

  if [[ -f "$dir/transcript.md" ]]; then
    content="$(cat "$dir/transcript.md")";  source_note="Source: transcript"
  elif [[ -f "$dir/transcript.txt" ]]; then
    content="$(cat "$dir/transcript.txt")"; source_note="Source: transcript"
  elif [[ -f "$dir/transcript.docx" ]] && command -v pandoc >/dev/null 2>&1; then
    content="$(pandoc "$dir/transcript.docx" -t plain --wrap=none)"
    source_note="Source: transcript (converted from .docx)"
  elif [[ -f "$dir/questions.md" ]]; then
    content="$(cat "$dir/questions.md")"
    source_note="Source: FALLBACK. Question list with pre-filled likely answers. No transcript was captured for this station and nobody in that room said these words."
    fallback+=("$name"); SOURCE_OF[$name]=fallback
  else
    missing+=("$name"); continue
  fi

  if [[ "$source_note" == Source:\ transcript* ]]; then live+=("$name"); SOURCE_OF[$name]=transcript; fi

  {
    echo "## Station: $name"
    echo "_${source_note}_"
    echo
    echo "$content"
    echo
  } >> "$combined"
done

if [[ ${#missing[@]} -gt 0 ]]; then
  echo "FATAL: no transcript and no question list for: ${missing[*]}" >&2
  echo "FATAL: refusing to build a deck that silently drops a station." >&2
  echo "FATAL: put a questions.md in stations/<name>/ and re-run. The existing deck is untouched." >&2
  exit 3
fi

if [[ ${#fallback[@]} -gt 0 ]]; then
  echo "Inputs: ${#live[@]}/5 from a transcript, falling back for: ${fallback[*]}" >&2
else
  echo "Inputs: ${#live[@]}/5 from a transcript, no fallbacks needed" >&2
fi

{
  cat "$FRAMEWORK"
  echo; echo "---"; echo
  echo "Raw station inputs follow below."
  echo
  cat "$combined"
} > "$payload"

echo "Calling model ($CLAUDE_BIN)..." >&2
model_started=$(date +%s)
# The prompt goes in on stdin, NOT as an argument. Linux caps a single argv string at
# 128KB (MAX_ARG_STRLEN, 32 pages) regardless of the much larger ARG_MAX, and five real
# 45-minute transcripts come to roughly 285KB. Passing it as "$(cat ...)" fails with
# "Argument list too long" only once the transcripts are full length, which is to say
# only on the night. Found by the fullsize rehearsal; see tests/README.md.
if ! "$CLAUDE_BIN" -p < "$payload" > "$payload.out" 2>"$payload.err"; then
  echo "FATAL: $CLAUDE_BIN exited nonzero. stderr:" >&2
  sed 's/^/  /' "$payload.err" >&2
  echo "FATAL: existing deck left untouched." >&2
  exit 4
fi
model_elapsed=$(( $(date +%s) - model_started ))
echo "Model returned in ${model_elapsed}s" >&2

# Ground truth, straight off the disk. The model is never asked which stations had a
# transcript, so it cannot get that wrong and cannot launder a fallback into a transcript.
sources=""
for name in "${STATION_IDS[@]}"; do sources+="${sources:+,}$name=${SOURCE_OF[$name]}"; done

python3 "$BUILDER" --payload "$payload.out" --out "$OUT_FILE" --mode "$MODE" --sources "$sources"
rc=$?
rm -f "$payload.out" "$payload.err"

elapsed=$(( $(date +%s) - started ))
if [[ $rc -ne 0 ]]; then
  echo "FAILED after ${elapsed}s. Present the deck that is already there." >&2
  exit $rc
fi

echo "Total ${elapsed}s. Open $OUT_FILE and present. Arrow keys or Next."
