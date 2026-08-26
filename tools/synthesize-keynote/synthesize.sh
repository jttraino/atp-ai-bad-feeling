#!/usr/bin/env bash
# Builds a draft of the closing keynote talking points from whatever is
# currently sitting in stations/*/, and writes it to keynote/talking-points-draft.md.
#
# For each station, in priority order, it uses:
#   1. transcript.md or transcript.txt   — the real Teams transcript, pasted in as plain text
#   2. transcript.docx                    — converted via pandoc, if pandoc is installed
#   3. outline.md                         — the speaker's pre-submitted outline, used as a
#                                            fallback if no transcript was captured
# A station with none of the above is reported as missing entirely.
#
# Requires the `claude` CLI to be available and logged in.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
STATIONS_DIR="$REPO_ROOT/stations"
FRAMEWORK="$REPO_ROOT/tools/synthesize-keynote/framework.md"
OUT_DIR="$REPO_ROOT/keynote"
OUT_FILE="$OUT_DIR/talking-points-draft.md"

mkdir -p "$OUT_DIR"

combined="$(mktemp)"
missing=()
fallback=()

for dir in "$STATIONS_DIR"/*/; do
  name="$(basename "$dir")"
  content=""
  source_note=""

  if [[ -f "$dir/transcript.md" ]]; then
    content="$(cat "$dir/transcript.md")"
    source_note="Source: transcript"
  elif [[ -f "$dir/transcript.txt" ]]; then
    content="$(cat "$dir/transcript.txt")"
    source_note="Source: transcript"
  elif [[ -f "$dir/transcript.docx" ]] && command -v pandoc >/dev/null 2>&1; then
    content="$(pandoc "$dir/transcript.docx" -t plain)"
    source_note="Source: transcript (converted from .docx)"
  elif [[ -f "$dir/outline.md" ]]; then
    content="$(cat "$dir/outline.md")"
    source_note="Source: FALLBACK — speaker's pre-submitted outline, no transcript was captured for this station"
    fallback+=("$name")
  else
    missing+=("$name")
    continue
  fi

  {
    echo "## Station: $name"
    echo "_${source_note}_"
    echo
    echo "$content"
    echo
  } >> "$combined"
done

if [[ ${#missing[@]} -gt 0 ]]; then
  echo "WARNING: no transcript, docx, or outline found for: ${missing[*]}" >&2
fi
if [[ ${#fallback[@]} -gt 0 ]]; then
  echo "NOTE: using speaker outline fallback (no transcript) for: ${fallback[*]}" >&2
fi

prompt_file="$(mktemp)"
{
  cat "$FRAMEWORK"
  echo
  echo "---"
  echo
  echo "Raw station inputs follow below."
  echo
  cat "$combined"
} > "$prompt_file"

claude -p "$(cat "$prompt_file")" > "$OUT_FILE"

echo "Draft written to $OUT_FILE"
[[ ${#missing[@]} -gt 0 ]] && echo "Missing entirely (no input at all, not even an outline): ${missing[*]}"
