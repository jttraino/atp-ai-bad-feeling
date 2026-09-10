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

ALL=(seed happy mixed docx disaster late garbage badschema liar crash nothing noprior fullsize
     hedge-primary hedge-standby hedge-primary-bad hedge-both-bad hedge-disabled
     no-hedge-flag voices voices-partial voices-all-fail voices-launder)
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
  ( cd "$SCRATCH" && MODE=seeded CLAUDE_BIN="$STUBS/claude" STUB_MODE=good FAST_MODEL="" \
      ./tools/synthesize-keynote/synthesize.sh ) >"$SCRATCH/seed.log" 2>&1
}

run_synth() {
  local mode="${1:-live}" t0 t1
  t0=$(date +%s%N)
  if [[ "${REAL_MODEL:-0}" == "1" ]]; then
    ( cd "$SCRATCH" && MODE="$mode" CLAUDE_BIN=claude VOICES="${VOICES:-}" \
        ./tools/synthesize-keynote/synthesize.sh ${SYNTH_ARGS:-} ) >"$SCRATCH/synth.log" 2>&1
  else
    ( cd "$SCRATCH" && MODE="$mode" CLAUDE_BIN="$STUBS/claude" STUB_MODE="${STUB_MODE:-good}" \
        STUB_MODE_PRIMARY="${STUB_MODE_PRIMARY:-}" STUB_MODE_FAST="${STUB_MODE_FAST:-}" \
        STUB_DELAY_PRIMARY="${STUB_DELAY_PRIMARY:-0}" STUB_DELAY_FAST="${STUB_DELAY_FAST:-0}" \
        DEADLINE_S="${DEADLINE_S:-150}" GRACE_S="${GRACE_S:-60}" FAST_MODEL="${FAST_MODEL-haiku}" \
        STUB_VOICE_FAIL="${STUB_VOICE_FAIL:-}" STUB_VOICE_VAGUE="${STUB_VOICE_VAGUE:-}" VOICES="${VOICES:-}" \
        ./tools/synthesize-keynote/synthesize.sh ${SYNTH_ARGS:-} ) >"$SCRATCH/synth.log" 2>&1
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
# Pull a JS literal out of the deck by matching brackets rather than by regex. The
# values are multi-line JSON and one of them used to sit next to a // comment, which
# is exactly the kind of thing a lazy regex gets quietly wrong.
deck_json() { python3 - "$DECK" "$1" <<'DECKPY'
import sys, json
src, name = open(sys.argv[1]).read(), sys.argv[2]
i = src.index(f"const {name} = ") + len(f"const {name} = ")
open_c = src[i]; close_c = {"[": "]", "{": "}"}[open_c]
depth, j, instr, esc = 0, i, False, False
while j < len(src):
    c = src[j]
    if instr:
        if esc: esc = False
        elif c == "\\": esc = True
        elif c == '"': instr = False
    elif c == '"': instr = True
    elif c == open_c: depth += 1
    elif c == close_c:
        depth -= 1
        if depth == 0: break
    j += 1
print(json.dumps(json.loads(src[i:j + 1])))
DECKPY
}

deck_screens(){ deck_json DECKS | python3 -c "import json,sys; print(len(json.load(sys.stdin)['straight']))" 2>/dev/null || echo 0; }

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
  check "tells you the old deck still stands"   "grep -q 'untouched and presentable' '$SCRATCH/synth.log'"
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
  check "says there is nothing to fall back to" "grep -q 'no deck to fall back on' '$SCRATCH/synth.log'"
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

# ---- the hedge: two models in parallel, deliberately not a race -----------------

scen_hedge_primary() {  # primary is fine, standby is irrelevant
  new_scratch; seed_questions; establish_floor
  STUB_DELAY_FAST=4 DEADLINE_S=30 run_synth live
  check "exits 0"                               "[[ $RC -eq 0 ]]"
  check "primary won"                           "grep -q 'from the primary model' '$SCRATCH/synth.log'"
  check "standby never mentioned as the source" "! grep -q 'standby, because' '$SCRATCH/synth.log'"
  check "deck credits the primary"              "deck_says 'Written by the primary model'"
  if [[ $ELAPSED_MS -lt 4000 ]]; then ok "did not wait for the slower standby (${ELAPSED_MS}ms)"
  else bad "waited ${ELAPSED_MS}ms; it should not block on the standby"; fi
}

scen_hedge_standby() {  # primary blows the deadline, standby carries the room
  new_scratch; seed_questions; establish_floor
  STUB_DELAY_PRIMARY=30 DEADLINE_S=3 GRACE_S=10 run_synth live
  check "exits 0"                               "[[ $RC -eq 0 ]]"
  check "says the primary missed the deadline"  "grep -q 'missed the 3s deadline' '$SCRATCH/synth.log'"
  check "standby supplied the content"          "grep -q 'haiku standby' '$SCRATCH/synth.log'"
  check "deck admits it on the provenance line" "deck_says 'haiku standby'"
  check "still has real transcript detail"      "grep -Eqi '400,000|four hundred thousand' '$DECK'"
  if [[ $ELAPSED_MS -lt 15000 ]]; then ok "finished near the deadline, not the primary's 30s (${ELAPSED_MS}ms)"
  else bad "took ${ELAPSED_MS}ms; the deadline did not cut the primary off"; fi
}

scen_hedge_primary_bad() {  # primary returns fast but useless: don't sit out the deadline
  new_scratch; seed_questions; establish_floor
  STUB_MODE_PRIMARY=garbage STUB_MODE_FAST=good DEADLINE_S=60 run_synth live
  check "exits 0"                               "[[ $RC -eq 0 ]]"
  check "names the primary as unusable"         "grep -q 'Primary unusable' '$SCRATCH/synth.log'"
  check "standby supplied the content"          "grep -q 'haiku standby' '$SCRATCH/synth.log'"
  if [[ $ELAPSED_MS -lt 20000 ]]; then ok "switched immediately, did not wait out 60s (${ELAPSED_MS}ms)"
  else bad "waited ${ELAPSED_MS}ms for a deadline it had no reason to wait for"; fi
}

scen_hedge_both_bad() {  # both paths fail: the seeded deck is the whole point
  new_scratch; seed_questions; establish_floor
  local before; before=$(md5sum "$DECK" | cut -d' ' -f1)
  STUB_MODE=garbage DEADLINE_S=3 GRACE_S=3 run_synth live
  check "fails loudly"                          "[[ $RC -ne 0 ]]"
  check "reports both paths"                    "[[ \$(grep -c 'unusable' '$SCRATCH/synth.log') -ge 2 ]]"
  check "points at the deck already on disk"    "grep -q 'untouched and presentable' '$SCRATCH/synth.log'"
  check "and that deck is byte-identical"       "[[ \$(md5sum '$DECK' | cut -d' ' -f1) == '$before' ]]"
}

scen_hedge_disabled() {  # FAST_MODEL empty: single path, no hang waiting on a standby
  new_scratch; seed_questions; establish_floor
  local before; before=$(md5sum "$DECK" | cut -d' ' -f1)
  FAST_MODEL="" STUB_MODE=garbage DEADLINE_S=30 run_synth live
  check "fails loudly"                          "[[ $RC -ne 0 ]]"
  check "no standby was started"                "! grep -q 'running in parallel' '$SCRATCH/synth.log'"
  check "existing deck untouched"               "[[ \$(md5sum '$DECK' | cut -d' ' -f1) == '$before' ]]"
  if [[ $ELAPSED_MS -lt 20000 ]]; then ok "gave up promptly, no phantom standby wait (${ELAPSED_MS}ms)"
  else bad "hung ${ELAPSED_MS}ms waiting for a standby that was never started"; fi
}

# ---- optional extras: the hedge switch, and the character voices ---------------

deck_voices() { deck_json VOICES | python3 -c "import json,sys; print(' '.join(v[0] for v in json.load(sys.stdin)))" 2>/dev/null || echo ""; }

scen_no_hedge_flag() {  # --no-hedge on a run that succeeds: one model, no standby
  new_scratch; seed_questions; establish_floor
  SYNTH_ARGS="--no-hedge" run_synth live
  check "exits 0"                               "[[ $RC -eq 0 ]]"
  check "no standby was started"                "! grep -q 'running in parallel' '$SCRATCH/synth.log'"
  check "primary still produced the deck"       "grep -q 'from the primary model' '$SCRATCH/synth.log'"
  check "deck is complete"                      "[[ \$(deck_screens) -eq 8 ]]"
}

scen_voices() {  # the live toggle
  new_scratch; seed_questions; establish_floor
  SYNTH_ARGS="--voices=yoda,vader" run_synth live
  check "exits 0"                               "[[ $RC -eq 0 ]]"
  check "both voices survived"                  "[[ \"\$(deck_voices)\" == 'straight yoda vader' ]]"
  check "deck carries yoda's text"              "deck_says '[Yoda]'"
  check "deck carries vader's text"             "deck_says '[Darth Vader]'"
  check "straight text is still there too"      "grep -Eqi '400,000|four hundred thousand' '$DECK'"
  check "voice bar is rendered"                 "deck_says 'id=\"voiceButtons\"'"
  check "method screens excluded from voicing"  "deck_says 'UNVOICED'"
  check "straight deck was up before voices"    "grep -q 'Straight deck up' '$SCRATCH/synth.log'"
}

scen_voices_partial() {  # one voice fails: drop it, keep the rest, never lose the deck
  new_scratch; seed_questions; establish_floor
  STUB_VOICE_FAIL=darth SYNTH_ARGS="--voices=yoda,vader" run_synth live
  check "exits 0"                               "[[ $RC -eq 0 ]]"
  check "the bad voice was dropped"             "grep -q 'vader: unusable' '$SCRATCH/synth.log'"
  check "the good voice survived"               "[[ \"\$(deck_voices)\" == 'straight yoda' ]]"
  check "deck is still complete"                "[[ \$(deck_screens) -eq 8 ]]"
}

scen_voices_all_fail() {  # every voice fails: straight deck stands, exit still clean
  new_scratch; seed_questions; establish_floor
  STUB_VOICE_FAIL=yoda,darth SYNTH_ARGS="--voices=yoda,vader" run_synth live
  check "exits 0 anyway"                        "[[ $RC -eq 0 ]]"
  check "says no voice survived"                "grep -q 'No voice survived' '$SCRATCH/synth.log'"
  check "deck has only the straight voice"      "[[ \"\$(deck_voices)\" == 'straight' ]]"
  check "no voice bar to show"                  "[[ \$(deck_json VOICES | python3 -c 'import json,sys;print(len(json.load(sys.stdin)))') -eq 1 ]]"
  check "deck is still complete and real"       "grep -Eqi '400,000|four hundred thousand' '$DECK'"
}

scen_voices_launder() {  # a voice that quietly drops the numbers must be called out
  new_scratch; seed_questions; establish_floor
  STUB_VOICE_VAGUE=1 SYNTH_ARGS="--voices=yoda" run_synth live
  check "exits 0"                               "[[ $RC -eq 0 ]]"
  check "warns that figures went missing"       "grep -q 'WARNING voice yoda' '$SCRATCH/synth.log'"
  check "names a specific missing figure"       "grep -q '190,000' '$SCRATCH/synth.log'"
  check "voice is still offered, not dropped"   "[[ \"\$(deck_voices)\" == 'straight yoda' ]]"
  check "straight deck keeps its numbers"       "grep -Eqi '400,000|four hundred thousand' '$DECK'"
}

# ---------------------------------------------------------------- driver
echo
echo "Rehearsal: ${SCENARIOS[*]}"
[[ "${REAL_MODEL:-0}" == "1" ]] && echo "${c_y}Using the real claude CLI${c_0}"
echo

for SCEN in "${SCENARIOS[@]}"; do
  echo "  ${c_d}scenario:${c_0} $SCEN"
  ELAPSED_MS=0
  "scen_${SCEN//-/_}"
  echo "    ${c_d}synthesis wall time: ${ELAPSED_MS}ms${c_0}"
  if [[ $KEEP == 1 ]]; then echo "    ${c_d}scratch: $SCRATCH${c_0}"; else rm -rf "$SCRATCH"; fi
  echo
done

echo "  ${c_g}$pass passed${c_0}, $( ((fail)) && echo "${c_r}$fail failed${c_0}" || echo "0 failed" )"
if ((fail)); then printf '    %s\n' "${FAILURES[@]}"; exit 1; fi
