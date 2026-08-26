# Keynote Synthesis Framework

This is the guiding brief handed to the LLM, alongside the raw station inputs, to produce the closing keynote talking points. It's checked into this repo so anyone can see exactly what shaped the synthesis — not just the output.

## Event context (for the model)

This is the closing keynote for ATP's "Your AI Program Has a Bad Feeling About This" — an interactive workshop on why enterprise AI initiatives fail, run as the honest debrief nobody runs at their own company. Attendees split into five themed small-group stations, each covering a distinct failure mode:

- **Cloud City** — infrastructure and integration challenges with third-party tools
- **Dagobah** — technical debt and data quality issues
- **Hoth** — development-stage use cases stuck in limbo
- **The Wampa Cave** — unexpected costs and security vulnerabilities
- **The Asteroid Field** — compliance, legal obstacles, and scope creep

After all five run in parallel, the whole group reassembles for one closing keynote. Its job is to give everyone — including people who weren't in a given station — the real, specific substance of what was said there, then surface what connects across all five.

## Task

You will be given the raw transcript (or, if a transcript wasn't captured, the speaker's pre-submitted outline) for each of the five stations. Produce a draft of closing keynote talking points.

## Required output structure

1. **Per station** (one subsection each, in the order above): 3-5 bullet points capturing the *specific, concrete* things that were actually said — real examples, numbers, quotes, disagreements — not generic AI-industry platitudes. If a station's input is marked as a fallback (speaker's outline, not an actual transcript), say so explicitly at the top of that subsection rather than presenting it as equivalent to the others.
2. **Cross-cutting patterns**: 3-5 things that showed up, in some form, across multiple stations — this is the part that makes the keynote worth doing rather than just reading five summaries back to back.
3. **Closing line**: one line that ties the throughline back to the event's framing (the honest debrief, the "bad feeling" premise) — a note to end the room on, not a recap.

## Tone and ground rules

- Candid and specific. No corporate buzzwords, no "leverage synergies" filler.
- Ground every point in the actual input text. Do not invent examples, numbers, or quotes that aren't there.
- Light touch on the Star Wars theming is fine (the station names invite it) but don't force a joke into every line.
- This is a first draft for the person delivering the keynote to skim and adapt on the fly — favor clear, scannable bullets over prose paragraphs.
