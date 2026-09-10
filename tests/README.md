# Rehearsal Harness

This is how we ran reps on the night before the night. Every scenario runs the real tools against real files in a scratch copy of the repo: intake from a mock Downloads folder, synthesis, schema validation, deck build. Nothing is mocked except the model, and the model stub is swapped between modes so its failures get rehearsed too.

```bash
tests/rehearse.sh                    # every scenario, against the model stub, ~2 seconds
tests/rehearse.sh happy mixed        # named scenarios
tests/rehearse.sh --keep disaster    # keep the scratch dir and print its path
REAL_MODEL=1 tests/rehearse.sh fullsize    # the real claude CLI, real-length transcripts
```

## The scenarios

| Scenario | What night it is |
|---|---|
| `seed` | Days before. Question lists exist, no transcripts. Builds the floor. |
| `happy` | All five recordings worked. |
| `mixed` | Three Teams exports, one emailed backup from a sponsor's own device, one total loss. |
| `docx` | All five arrive as Teams `.docx` exports and have to be converted. |
| `disaster` | Every recording failed. Five fallbacks, and there is still a deck. |
| `late` | A transcript lands after a deck was already built. Re-run must improve, not clobber. |
| `garbage` | The model returns an apology instead of JSON. |
| `badschema` | Well-formed JSON that drops a station. |
| `liar` | The model relabels a fallback as a real transcript. |
| `crash` | The CLI exits nonzero, rate limited. |
| `nothing` | No transcript and no question list. The one case we refuse to paper over. |
| `noprior` | A bad model run with no seeded deck behind it. The case `seed.sh` exists to prevent. |
| `fullsize` | Transcripts inflated to the ~8,500 words a real 45-minute station produces, and timed. |

## What the reps actually found

Every one of these was a real defect found by running the thing, not by reading it.

**The prompt was passed as a shell argument, which breaks at exactly the wrong moment.** `claude -p "$(cat prompt)"` works fine on a 3KB test transcript. Linux caps a single argv string at 128KB (`MAX_ARG_STRLEN`, 32 pages, independent of the much larger `ARG_MAX`), and five real 45-minute transcripts come to about 285KB. So the tool worked in every small test and would have died with `Argument list too long` on the night, with a room full of people waiting. Found by `fullsize`. Fixed by piping the prompt on stdin.

**The model could launder a fallback into a real transcript.** The deck took each station's `source` from the model's own output, so a model that claimed a fallback was a transcript got believed, and the on-screen "not from a transcript" warning silently disappeared. Found by `liar`. Fixed by not asking: the source is established from what is on disk and injected into the builder, and anything the model says about it is discarded. The general rule is that you should never ask a model to report a fact you already know.

**A 26-character overrun threw away an entire run.** The real model returned a takeaway 226 characters long against a 200-character cap, and the whole synthesis was rejected two minutes before it was needed. Found by `REAL_MODEL=1 happy`. Fixed by splitting validation in two: structural problems (missing station, unknown id, wrong number of points, not JSON) are hard rejections because they mean the model misunderstood the task; length caps are cosmetic, so overlong text is trimmed on a word boundary and reported.

**Synthesis takes between 69 and 164 seconds, and the coordinator checklist said 60.** Four real-model runs came in at 69, 102, 105 and 164 seconds. The important part is not the median, it is that **the slowest run was on the smallest input**: latency varies more than twofold for reasons that have nothing to do with how much we ask it to read, so it cannot be shortened by trimming transcripts. The run of show now gets a three-minute slice rather than a one-minute one, which moves the end-to-end worst case from roughly 8 minutes to roughly 10. Had we measured once and written that number down, we would have planned against 105 seconds and been wrong by a minute on the night.

**A 600-word test transcript flatters everything.** The fixtures are written to be readable. Real stations produce something like 8,500 words each. `tests/inflate.py` pads the fixtures to that length so the timing rep measures the real thing; without it, two of the four findings above stay hidden.

## Layout

```
tests/
  rehearse.sh              the scenarios
  inflate.py               grows fixtures to real 45-minute length
  fixtures/questions/      the five question lists with pre-filled likely answers
  fixtures/arrivals/       mock Teams exports, .txt and .docx, named as Teams names them
  stubs/claude             stands in for the CLI on PATH
  stubs/model_stub.py      deterministic model, STUB_MODE selects good/fenced/garbage/badschema/liar/fail
```

The fixtures are invented. The people, companies, and numbers in them are not real, and they exist so the pipeline has something of the right shape and size to chew on.
