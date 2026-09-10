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
#   CLAUDE_BIN    model CLI to invoke (default: claude)
#   MODE          live | seeded  (default: live)
#   PRIMARY_MODEL model for the good answer (default: the CLI's own default)
#   FAST_MODEL    standby model run in parallel (default: haiku; empty disables the hedge)
#   DEADLINE_S    how long the primary gets before we prefer the standby (default: 180)
#   GRACE_S       extra time to wait for the standby after that (default: 45)
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
STATIONS_DIR="$REPO_ROOT/stations"
FRAMEWORK="$REPO_ROOT/tools/synthesize-keynote/framework.md"
BUILDER="$REPO_ROOT/tools/build-deck/build_deck.py"
OUT_FILE="$REPO_ROOT/closing-keynote/presentation.html"
CLAUDE_BIN="${CLAUDE_BIN:-claude}"
MODE="${MODE:-live}"
PRIMARY_MODEL="${PRIMARY_MODEL-}"
FAST_MODEL="${FAST_MODEL-haiku}"
DEADLINE_S="${DEADLINE_S:-180}"
GRACE_S="${GRACE_S:-45}"

STATION_IDS=(sky-city swamp-planet ice-planet snow-monster-cave asteroid-field)

started=$(date +%s)
combined="$(mktemp)"; payload="$(mktemp)"
trap 'rm -f "$combined" "$payload" "$payload".*' EXIT

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

# Ground truth, straight off the disk. Computed here because the hedge below has to
# validate a candidate before it can choose between them.
sources=""
for name in "${STATION_IDS[@]}"; do sources+="${sources:+,}$name=${SOURCE_OF[$name]}"; done

# --------------------------------------------------------------------- the hedge
#
# Two requests in parallel, and deliberately NOT a race. The primary gets the whole
# deadline to itself; the standby is only used if the primary misses it or comes back
# unusable. A pure race would hand the room a weaker deck whenever the standby happened
# to finish fifteen seconds earlier, which is the opposite of what we want.
#
# They run at the same time rather than in sequence because a serial retry costs you
# the primary's entire deadline before the standby has even started. The measured
# spread on the primary is 69 to 164 seconds, so a serial fallback can put you past
# four minutes. In parallel, the worst case is about the deadline.
#
# What it buys, in order of how likely you are to need it:
#   1. Tail latency. Two calls go slow independently.
#   2. A second, independent attempt at valid output if the primary returns nonsense.
#   3. Nothing whatsoever if the venue network is down or the account is rate limited.
#      Both paths share those. That is what the seeded deck is for.

spawn() {  # spawn <label> <model>; writes .out, .err and .rc alongside $payload
  local label="$1" model="$2"
  (
    # The prompt goes in on stdin, NOT as an argument. Linux caps a single argv string
    # at 128KB (MAX_ARG_STRLEN, 32 pages) regardless of the much larger ARG_MAX, and
    # five real 45-minute transcripts come to roughly 285KB. Passing it as "$(cat ...)"
    # fails with "Argument list too long" only once the transcripts are full length,
    # which is to say only on the night. Found by the fullsize rehearsal.
    if [[ -n "$model" ]]; then
      "$CLAUDE_BIN" --model "$model" -p < "$payload" > "$payload.$label.out" 2>"$payload.$label.err"
    else
      "$CLAUDE_BIN" -p < "$payload" > "$payload.$label.out" 2>"$payload.$label.err"
    fi
    echo $? > "$payload.$label.rc"
  ) >/dev/null 2>&1 &
  # The subshell's stdout must be redirected, not just its inner commands'. It inherits
  # the command-substitution pipe from $(spawn ...), and that pipe stays open until the
  # last holder exits, so without this the "background" job blocks the caller until it
  # finishes and the two hedged calls run strictly in sequence. Which is exactly what
  # the hedge exists to avoid, and it looks like it works right up until you time it.
  echo $!
}

usable() {  # finished, exited clean, and passes the schema
  local label="$1"
  [[ -f "$payload.$label.rc" ]] || return 1
  [[ "$(cat "$payload.$label.rc")" == "0" ]] || return 1
  python3 "$BUILDER" --check --payload "$payload.$label.out" --out "$OUT_FILE" \
      --sources "$sources" >/dev/null 2>"$payload.$label.val"
}

model_started=$(date +%s)
primary_pid=$(spawn primary "$PRIMARY_MODEL")
echo "Calling ${PRIMARY_MODEL:-default model}, deadline ${DEADLINE_S}s..." >&2
fast_pid=""
if [[ -n "$FAST_MODEL" ]]; then
  fast_pid=$(spawn fast "$FAST_MODEL")
  echo "Standby $FAST_MODEL running in parallel." >&2
fi

winner=""; engine=""; primary_state=pending; fast_state=pending
deadline=$(( model_started + DEADLINE_S ))
hard_stop=$(( deadline + GRACE_S ))

while :; do
  now=$(date +%s)

  if [[ $primary_state == pending && -f "$payload.primary.rc" ]]; then
    if usable primary; then
      winner="$payload.primary.out"; engine="${PRIMARY_MODEL:-the primary model}"; break
    fi
    primary_state=failed
    echo "Primary unusable after $(( now - model_started ))s: $(head -1 "$payload.primary.val" 2>/dev/null)" >&2
    if [[ -z "$fast_pid" ]]; then break; fi
    echo "Waiting on the $FAST_MODEL standby." >&2
  fi

  if [[ -n "$fast_pid" && $fast_state == pending && -f "$payload.fast.rc" ]]; then
    if usable fast; then fast_state=ready; else
      fast_state=failed
      echo "Standby unusable: $(head -1 "$payload.fast.val" 2>/dev/null)" >&2
    fi
  fi

  if [[ $fast_state == ready && ( $primary_state == failed || $now -ge $deadline ) ]]; then
    if [[ $primary_state == pending ]]; then
      echo "Primary missed the ${DEADLINE_S}s deadline. Going with the standby." >&2
    fi
    winner="$payload.fast.out"
    engine="the $FAST_MODEL standby, because the primary did not deliver in time"
    break
  fi

  if [[ $primary_state == failed && $fast_state == failed ]]; then break; fi
  if [[ $now -ge $hard_stop ]]; then
    echo "Nothing usable within $(( DEADLINE_S + GRACE_S ))s." >&2; break
  fi
  sleep 1
done

for pid in $primary_pid $fast_pid; do kill "$pid" 2>/dev/null || true; done
wait 2>/dev/null || true
model_elapsed=$(( $(date +%s) - model_started ))

if [[ -z "$winner" ]]; then
  echo "FATAL: no usable output after ${model_elapsed}s." >&2
  for label in primary fast; do
    if [[ -s "$payload.$label.err" ]]; then echo "  $label stderr:" >&2; sed 's/^/    /' "$payload.$label.err" >&2; fi
    if [[ -s "$payload.$label.val" ]]; then echo "  $label validation:" >&2; sed 's/^/    /' "$payload.$label.val" >&2; fi
  done
  if [[ -f "$OUT_FILE" ]]; then
    echo "FATAL: the deck already on disk is untouched and presentable. Present that." >&2
  else
    echo "FATAL: and there is no deck to fall back on. Run seed.sh." >&2
  fi
  exit 4
fi

echo "Usable output in ${model_elapsed}s from $engine" >&2

python3 "$BUILDER" --payload "$winner" --out "$OUT_FILE" --mode "$MODE" \
    --sources "$sources" --engine "$engine"
rc=$?
rm -f "$payload".*

elapsed=$(( $(date +%s) - started ))
if [[ $rc -ne 0 ]]; then
  echo "FAILED after ${elapsed}s. Present the deck that is already there." >&2
  exit $rc
fi

echo "Total ${elapsed}s. Open $OUT_FILE and present. Arrow keys or Next."
