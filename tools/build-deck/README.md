# Deck Builder

Turns a validated JSON payload into `closeout-keynote/presentation.html`: one self-contained file, no network, no dependencies, arrow keys or Next to move, and a QR code back to this repo.

```bash
python3 tools/build-deck/build_deck.py \
  --payload payload.json \
  --out closeout-keynote/presentation.html \
  --sources sky-city=transcript,swamp-planet=fallback,... \
  --mode live
```

You don't normally run this directly. [`tools/synthesize-keynote/synthesize.sh`](../synthesize-keynote/) calls it.

## The split, and why it is the whole point

The model is asked for content and nothing else: a lede, three to five points, and a takeaway per station, plus the cross-cutting patterns. Everything else about the deck is generated here, in code:

- the order of the screens, and which screens exist at all
- the two method screens explaining how the event was run
- which stations are marked as running on a fallback
- branding, navigation, the QR code, the print stylesheet

The reason is not tidiness. Anything the model produces has to be checked by a human under time pressure, and the fastest way to reduce that burden is to shrink what the model is allowed to decide. A model that cannot choose the slide order cannot get the slide order wrong.

## Validation, hard and soft

**Hard, rejects the whole run:** output that isn't JSON, a missing or duplicated station, an id that isn't one of the five, a station with fewer than 3 or more than 5 points, a missing lede or takeaway. These mean the model misunderstood the task, and the rest of its output should not be trusted either.

**Soft, trimmed and reported:** text over the length caps. These protect the slide layout, not the truth. Throwing away a run at 7:50pm because a sentence was 26 characters long is a worse outcome than a trimmed sentence, and that exact thing happened in rehearsal before this was split out.

On a hard rejection the existing deck is left byte-for-byte untouched and the failure says so. The previous deck always stands.

## Provenance is not the model's to report

`--sources` is ground truth, established by the caller from what is actually on disk. Whatever the model says about which stations had a transcript is read, compared, and discarded, with a note to stderr if it disagreed.

This closes a real hole found in rehearsal: a model that relabelled a fallback as a transcript made the on-screen "not from a transcript" warning disappear, which is precisely the failure the warning exists to prevent. The fix is not a better prompt. It is not asking the question.

## Station themes

Each station screen gets a complete palette, not an accent: page background, card, ink, secondary and muted text, rules, and the warning colours.

| Station | Look |
|---|---|
| Sky City | Bespin above the clouds. Warm sunset gradient, cream card, dark ink. |
| Swamp Planet | Dagobah under the canopy. Dark, deep green. |
| Ice Planet | Hoth in daylight. Pale blue-white, white card. |
| Snow Monster Cave | Inside the cave. Near-black with red. |
| Asteroid Field | Deep space, with rocks. Near-black with slate blue. |
| The three method screens | Default light. Those screens are ours. |

Backgrounds are CSS gradients rather than images, so the file stays self-contained and renders with no network. Themes are applied by setting CSS variables per screen, so the layout never knows which station it is on.

**Every text colour is measured against its own surface at build time and the build fails below its floor**: 7:1 for body ink, because that is the slide and the back of the room is a long way away, 4.5:1 for secondary, muted and accent text, 4:1 for warnings. Dark themes are not a legibility problem when the contrast is checked; unchecked ones are.

That check has now caught two failures that predate any theming: the original brand blue at 3.98:1 in the point numerals, and the original muted grey at 3.80:1 in the kicker and page count.

The QR keeps a white panel on every theme, because a QR needs a light quiet zone to scan. Verified by rendering it on the darkest card and scanning it back.

## Output

Every run writes the previous deck to `presentation.html.prev` first, then writes to a temp file and moves it into place, so there is no window where the file on disk is half-written.
