#!/usr/bin/env bash
# Rehearses the night, end to end, in a scratch copy of the repo.
#
# Every scenario runs the real tools against real files: intake from a mock
# Downloads folder, synthesis, schema validation, deck build. Nothing is mocked
# except the model itself, and the model stub is swapped to rehearse its failures
# too. Timings are measured, not estimated.
#
# Usage:
#   tests/rehearse.sh                 run every scenario
#   tests/rehearse.sh happy mixed     run named scenarios
#   tests/rehearse.sh --keep happy    keep the scratch dir and print its path
#   REAL_MODEL=1 tests/rehearse.sh happy    use the actual claude CLI
set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FIX="$REPO/tests/fixtures"
STUBS="$REPO/tests/stubs"
KEEP=0
[[ "${1:-}" == "--keep" ]] && { KEEP=1; shift; }

ALL=(seed happy mixed docx disaster late garbage badschema liar crash nothing noprior fullsize)
SCENARIOS=("${@:-}")
[[ -z "${SCENARIOS[0]:-}" ]] && SCENARIOS=("${ALL[@]}")

pass=0; fail=0; FAILURES=()

c_g=$'\033[32m'; c_r=$'\033[31m'; c_y=$'\033[33m'; c_d=$'\033[2m'; c_0=$'\033[0m'
[[ -t 1 ]] || { c_g=""; c_r=""; c_y=""; c_d=""; c_0=""; }

ok()   { pass=$((pass+1)); echo "    ${c_g}PASS${c_0}  $1"; }
bad()  { fail=$((fail+1)); FAILURES+=("$SCEN: $1"); echo "    ${c_r}FAIL${c_0}  $1"; }
check(){ if eval "$2"; then ok "$1"; else bad "$1"; fi; }

# ---------------------------------------------------------------- scratch setup
new_scratch() {
  SCRATCH="$(mktemp -d)"
  cp -r "$REPO"/{stations,tools,assets} "$SCRATCH/"
  mkdir -p "$SCRATCH/closing-keynote" "$SCRATCH/Downloads"
  rm -f "$SCRATCH"/stations/*/questions.md "$SCRATCH"/stations/*/transcript.*
  DECK="$SCRATCH/closing-keynote/presentation.html"
}

seed_questions() {  # the pre-event artifact: question lists in place
  for f in "$FIX"/questions/*.md; do
    cp "$f" "$SCRATCH/stations/$(basename "${f%.md}")/questions.md"
  done
}

arrive() {  # arrive <station-name-fragment> <ext>   drop a file into mock Downloads
  local frag="$1" ext="${2:-txt}"
  local src; src="$(ls "$FIX"/arrivals/*"$frag"*."$ext" 2>/dev/null | head -1)"
  [[ -n "$src" ]] || { echo "    ${c_r}fixture missing: $frag.$ext${c_0}"; return 1; }
  cp "$src" "$SCRATCH/Downloads/"
}

# The floor: what seed.sh built days before the event. Always the stub, because in
# the real timeline this already happened and is not what we are timing tonight.
establish_floor() {
  ( cd "$SCRATCH" && MODE=seeded CLAUDE_BIN="$STUBS/claude" STUB_MODE=good \
      ./tools/synthesize-keynote/synthesize.sh ) >"$SCRATCH/seed.log" 2>&1
}

run_synth() {
  local mode="${1:-live}" t0 t1
  t0=$(date +%s%N)
  if [[ "${REAL_MODEL:-0}" == "1" ]]; then
    ( cd "$SCRATCH" && MODE="$mode" CLAUDE_BIN=claude \
        ./tools/synthesize-keynote/synthesize.sh ) >"$SCRATCH/synth.log" 2>&1
  else
    ( cd "$SCRATCH" && MODE="$mode" CLAUDE_BIN="$STUBS/claude" STUB_MODE="${STUB_MODE:-good}" \
        ./tools/synthesize-keynote/synthesize.sh ) >"$SCRATCH/synth.log" 2>&1
  fi
  RC=$?
  t1=$(date +%s%N)
  ELAPSED_MS=$(( (t1 - t0) / 1000000 ))
  return $RC
}

deck_says()   { grep -qF "$1" "$DECK" 2>/dev/null; }

# How many distinctive facts from the transcripts survived into the deck. The framework
# demands specific numbers and named examples, and this is the only assertion that
# actually tests whether it got them. Written as alternations because a model will
# legitimately render "400,000" as "four hundred thousand" if the room said it that way.
FACTS=(
  '400,000|four hundred thousand'
  '94|ninety.four'
  '190,000|hundred and ninety thousand'
  '11,000|eleven thousand'
  '310|three hundred and ten'
  '600 pastes|six hundred pastes|600 a month'
  'eleven .*zero|zero in production'
  'nine months|month six'
)
specificity() {
  local n=0
  for re in "${FACTS[@]}"; do grep -Eqi "$re" "$DECK" 2>/dev/null && n=$((n+1)); done
  echo $n
}
deck_screens(){ python3 - "$DECK" <<'PY'
import re,sys,json
m=re.search(r"const SCREENS = (\[.*?\]);\n", open(sys.argv[1]).read(), re.S)
print(len(json.loads(m.group(1))) if m else 0)
PY
}

# ---------------------------------------------------------------- scenarios

scen_seed() {  # days before: build the floor from question lists alone
  new_scratch; seed_questions
  STUB_MODE=good run_synth seeded
  check "seed run exits 0"                      "[[ $RC -eq 0 ]]"
  check "deck exists before the event"          "[[ -f '$DECK' ]]"
  check "all 5 stations flagged as fallback"    "[[ \$(grep -c 'FALLBACK' '$DECK') -ge 5 ]]"
  check "deck says it was built pre-event"      "deck_says 'before the stations ran'"
  check "title marks it pre-seeded"             "deck_says 'pre-seeded'"
  check "QR code embedded"                      "deck_says 'data:image/png;base64,'"
  check "8 screens: 2 method, 5 stations, 1 patterns" "[[ \$(deck_screens) -eq 8 ]]"
}

scen_happy() {  # the night, everything works
  new_scratch; seed_questions; establish_floor
  for s in "Sky City" "Swamp Planet" "Ice Planet" "Snow Monster Cave" "Asteroid Field"; do arrive "$s" txt; done
  ( cd "$SCRATCH" && ./tools/intake-transcript/intake.sh "$SCRATCH/Downloads" ) >"$SCRATCH/intake.log" 2>&1
  check "intake filed all 5"                    "[[ \$(grep -c ' + ' '$SCRATCH/intake.log') -eq 5 ]]"
  check "no station left on fallback"           "! grep -q 'FALLBACK to questions' '$SCRATCH/intake.log'"
  run_synth live
  check "synthesis exits 0"                     "[[ $RC -eq 0 ]]"
  check "5/5 from transcript"                   "grep -q '5/5 stations from a real transcript' '$SCRATCH/synth.log'"
  check "no FALLBACK banner in deck"            "! deck_says 'Not from a transcript'"
  local spec; spec=$(specificity)
  if [[ $spec -ge 5 ]]; then ok "specific facts survived to the deck ($spec/8)"
  else bad "only $spec/8 distinctive facts reached the deck; the synthesis went generic"; fi
  check "provenance says built in the room"     "deck_says 'in the room, minutes ago'"
}

scen_mixed() {  # 3 Teams transcripts, 1 emailed backup, 1 total loss
  new_scratch; seed_questions; establish_floor
  arrive "Sky City" docx; arrive "Swamp Planet" docx; arrive "Ice Planet" docx
  arrive "Snow Monster Cave" txt          # the sponsor's own recorder, emailed in
  # Asteroid Field: nothing arrives at all
  ( cd "$SCRATCH" && ./tools/intake-transcript/intake.sh "$SCRATCH/Downloads" ) >"$SCRATCH/intake.log" 2>&1
  check "intake reports asteroid on fallback"   "grep -q 'asteroid-field *FALLBACK' '$SCRATCH/intake.log'"
  run_synth live
  check "synthesis exits 0"                     "[[ $RC -eq 0 ]]"
  check "4/5 from transcript"                   "grep -q '4/5 stations from a real transcript' '$SCRATCH/synth.log'"
  check "asteroid flagged on screen"            "deck_says 'Not from a transcript'"
  check "only one station flagged"              "[[ \$(grep -c 'Not from a transcript' '$DECK') -eq 1 ]]"
  check "the 4 good ones carried real detail"   "grep -Eqi '190,000|hundred and ninety thousand' '$DECK'"
}

scen_docx() {  # the Teams export path specifically
  new_scratch; seed_questions; establish_floor
  for s in "Sky City" "Swamp Planet" "Ice Planet" "Snow Monster Cave" "Asteroid Field"; do arrive "$s" docx; done
  ( cd "$SCRATCH" && ./tools/intake-transcript/intake.sh "$SCRATCH/Downloads" ) >"$SCRATCH/intake.log" 2>&1
  check "docx converted to text on intake"      "[[ -f '$SCRATCH/stations/sky-city/transcript.md' ]]"
  check "no raw .docx left in stations"         "! ls '$SCRATCH'/stations/*/transcript.docx >/dev/null 2>&1"
  check "converted text is not empty"           "[[ \$(wc -c <'$SCRATCH/stations/sky-city/transcript.md') -gt 2000 ]]"
  run_synth live
  check "synthesis exits 0"                     "[[ $RC -eq 0 ]]"
  check "5/5 from transcript"                   "grep -q '5/5 stations from a real transcript' '$SCRATCH/synth.log'"
}

scen_disaster() {  # every recording failed
  new_scratch; seed_questions; establish_floor
  run_synth live
  check "still exits 0"                         "[[ $RC -eq 0 ]]"
  check "0/5 from transcript"                   "grep -q '0/5 stations from a real transcript' '$SCRATCH/synth.log'"
  check "all 5 flagged on screen"               "[[ \$(grep -c 'Not from a transcript' '$DECK') -eq 5 ]]"
  check "there is still a deck to present"      "[[ -s '$DECK' ]]"
}

scen_late() {  # a transcript arrives after the deck was already built
  new_scratch; seed_questions; establish_floor
  arrive "Sky City" txt; arrive "Swamp Planet" txt
  ( cd "$SCRATCH" && ./tools/intake-transcript/intake.sh "$SCRATCH/Downloads" ) >/dev/null 2>&1
  run_synth live
  check "first pass 2/5"                        "grep -q '2/5 stations from a real transcript' '$SCRATCH/synth.log'"
  local first; first=$(grep -c 'Not from a transcript' "$DECK")
  arrive "Ice Planet" txt
  ( cd "$SCRATCH" && ./tools/intake-transcript/intake.sh "$SCRATCH/Downloads" ) >"$SCRATCH/intake2.log" 2>&1
  check "intake does not re-file what is filed" "grep -q 'already has a transcript' '$SCRATCH/intake2.log'"
  run_synth live
  check "second pass 3/5"                       "grep -q '3/5 stations from a real transcript' '$SCRATCH/synth.log'"
  check "fewer fallbacks than before"           "[[ \$(grep -c 'Not from a transcript' '$DECK') -lt $first ]]"
  check "previous deck kept as .prev"           "[[ -f '$DECK.prev' ]]"
}

scen_garbage() {  # the model returns prose instead of JSON
  new_scratch; seed_questions
  STUB_MODE=good run_synth seeded          # establish a good deck first
  local before; before=$(md5sum "$DECK" | cut -d' ' -f1)
  STUB_MODE=garbage run_synth live
  check "run fails loudly"                      "[[ $RC -ne 0 ]]"
  check "says REJECTED"                         "grep -q 'REJECTED' '$SCRATCH/synth.log'"
  check "existing deck is byte-identical"       "[[ \$(md5sum '$DECK' | cut -d' ' -f1) == '$before' ]]"
  check "tells you the old deck still stands"   "grep -q 'previous deck still stands' '$SCRATCH/synth.log'"
}

scen_badschema() {  # well-formed JSON that breaks the rules
  new_scratch; seed_questions
  STUB_MODE=good run_synth seeded
  local before; before=$(md5sum "$DECK" | cut -d' ' -f1)
  STUB_MODE=badschema run_synth live
  check "run fails loudly"                      "[[ $RC -ne 0 ]]"
  check "names the missing station"             "grep -q 'missing asteroid-field' '$SCRATCH/synth.log'"
  check "existing deck untouched"               "[[ \$(md5sum '$DECK' | cut -d' ' -f1) == '$before' ]]"
}

scen_liar() {  # the dangerous one: model relabels a fallback as a transcript
  new_scratch; seed_questions; establish_floor
  arrive "Sky City" txt
  ( cd "$SCRATCH" && ./tools/intake-transcript/intake.sh "$SCRATCH/Downloads" ) >/dev/null 2>&1
  STUB_MODE=liar run_synth live
  check "run completes"                         "[[ $RC -eq 0 ]]"
  check "model's false claim is noticed"        "grep -q 'Ignoring the model' '$SCRATCH/synth.log'"
  check "deck counts 1/5, not the model's 5/5"  "grep -q '1/5 stations from a real transcript' '$SCRATCH/synth.log'"
  check "the 4 real fallbacks are still flagged" "[[ \$(grep -c 'Not from a transcript' '$DECK') -eq 4 ]]"
  check "the one real transcript is not flagged" "grep -Eqi '400,000|four hundred thousand' '$DECK'"
}

scen_crash() {  # the CLI itself dies
  new_scratch; seed_questions
  STUB_MODE=good run_synth seeded
  local before; before=$(md5sum "$DECK" | cut -d' ' -f1)
  STUB_MODE=fail run_synth live
  check "run fails loudly"                      "[[ $RC -ne 0 ]]"
  check "surfaces the CLI stderr"               "grep -q 'rate_limit_error' '$SCRATCH/synth.log'"
  check "existing deck untouched"               "[[ \$(md5sum '$DECK' | cut -d' ' -f1) == '$before' ]]"
}

scen_nothing() {  # no questions.md either: the one case we refuse to paper over
  new_scratch
  run_synth live
  check "refuses to run"                        "[[ $RC -eq 3 ]]"
  check "names every station it cannot cover"   "grep -q 'sky-city' '$SCRATCH/synth.log'"
  check "explains why it refused"               "grep -q 'silently drops a station' '$SCRATCH/synth.log'"
  check "no deck was written"                   "[[ ! -f '$DECK' ]]"
}

scen_noprior() {  # a bad model run with no seeded deck behind it: the case seed.sh exists to prevent
  new_scratch; seed_questions
  STUB_MODE=garbage run_synth live
  check "run fails loudly"                      "[[ $RC -ne 0 ]]"
  check "says there is nothing to fall back to" "grep -q 'no deck at' '$SCRATCH/synth.log'"
  check "tells you to run seed.sh"              "grep -q 'Run seed.sh' '$SCRATCH/synth.log'"
  check "and there is indeed no deck"           "[[ ! -f '$DECK' ]]"
}

scen_fullsize() {  # timing against transcripts the length a real 45-minute station produces
  new_scratch; seed_questions; establish_floor
  python3 "$REPO/tests/inflate.py" "$FIX/arrivals" "$SCRATCH/Downloads" 8500
  ( cd "$SCRATCH" && ./tools/intake-transcript/intake.sh "$SCRATCH/Downloads" ) >"$SCRATCH/intake.log" 2>&1
  local words; words=$(cat "$SCRATCH"/stations/*/transcript.md | wc -w)
  echo "    ${c_d}input: ${words} words across 5 stations${c_0}"
  run_synth live
  check "synthesis exits 0"                     "[[ $RC -eq 0 ]]"
  check "5/5 from transcript"                   "grep -q '5/5 stations from a real transcript' '$SCRATCH/synth.log'"
  # Measured, not guessed. Four real-model runs came in at 69s, 102s, 105s and 164s,
  # and the 164s was on the SMALL fixtures: latency varies more than 2x run to run and
  # is not driven by input size. So the run of show gets a 3 minute slice, not the
  # median. If this fails, the run of show needs to know before the event, not during it.
  local synth_budget=$(( 180 * 1000 ))
  if [[ $ELAPSED_MS -lt $synth_budget ]]; then
    ok "synthesis inside its 3-minute slice of the run of show (${ELAPSED_MS}ms)"
  else
    bad "synthesis took ${ELAPSED_MS}ms, over the 3 minutes the run of show allows"
  fi
}

# ---------------------------------------------------------------- driver
echo
echo "Rehearsal: ${SCENARIOS[*]}"
[[ "${REAL_MODEL:-0}" == "1" ]] && echo "${c_y}Using the real claude CLI${c_0}"
echo

for SCEN in "${SCENARIOS[@]}"; do
  echo "  ${c_d}scenario:${c_0} $SCEN"
  ELAPSED_MS=0
  "scen_$SCEN"
  echo "    ${c_d}synthesis wall time: ${ELAPSED_MS}ms${c_0}"
  if [[ $KEEP == 1 ]]; then echo "    ${c_d}scratch: $SCRATCH${c_0}"; else rm -rf "$SCRATCH"; fi
  echo
done

echo "  ${c_g}$pass passed${c_0}, $( ((fail)) && echo "${c_r}$fail failed${c_0}" || echo "0 failed" )"
if ((fail)); then printf '    %s\n' "${FAILURES[@]}"; exit 1; fi
