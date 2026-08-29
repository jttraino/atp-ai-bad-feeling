# Keynote Synthesis Framework

This is the guiding brief handed to the LLM, alongside the raw base inputs, to produce the Fully Operational talking points. It's checked into this repo so anyone can see exactly what shaped the synthesis, not just the output.

## Event context (for the model)

This is Fully Operational, the closing keynote for ATP's "Your AI Program Has a Bad Feeling About This." It's an interactive workshop on why enterprise AI initiatives fail, run as the honest debrief nobody runs at their own company. Attendees split into five themed small-group bases, each covering a distinct failure mode:

- **Sky City**: infrastructure and integration challenges with third-party tools
- **Swamp Planet**: technical debt and data quality issues
- **Ice Planet**: development-stage use cases stuck in limbo
- **Snow Monster Cave**: unexpected costs and security vulnerabilities
- **Asteroid Field**: compliance, legal obstacles, and scope creep

After all five run in parallel, the whole group reassembles for one closing keynote. Its job is to give everyone, including people who weren't in a given base, the real, specific substance of what was said there. Then it surfaces what connects across all five.

## Task

You will be given the raw transcript for each of the five bases, or, if a transcript wasn't captured, the speaker's pre-submitted outline instead. Produce a draft of Fully Operational's talking points.

## Required output structure

1. **Per base** (one subsection each, in the order above): 3-5 bullet points capturing the *specific, concrete* things that were actually said. Real examples, numbers, quotes, disagreements. Not generic AI-industry platitudes. If a base's input is marked as a fallback (speaker's outline, not an actual transcript), say so explicitly at the top of that subsection rather than presenting it as equivalent to the others.
2. **Cross-cutting patterns**: 3-5 things that showed up, in some form, across multiple bases. This is the part that makes the keynote worth doing, rather than just reading five summaries back to back.
3. **Closing line**: one line that ties the throughline back to the event's framing (the honest debrief, the "bad feeling" premise). A note to end the room on, not a recap.

## Tone and ground rules

- Candid and specific. No corporate buzzwords, no "leverage synergies" filler.
- Ground every point in the actual input text. Do not invent examples, numbers, or quotes that aren't there.
- Light touch on the Star Wars theming is fine (the base names invite it) but don't force a joke into every line.
- This is a first draft. Fleet Command opens it in Obsidian and presents it live, clicking through by hand. It is not an automated slide deck, so favor clear, scannable bullets over prose paragraphs.
