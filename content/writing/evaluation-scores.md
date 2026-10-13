---
title: What an evaluation score really tells you
date: 2026-10-06
topic: Evaluation
cover: waves
summary: A single number hides a lot of decisions. Some notes on what goes into one, and what to ask before trusting it.
sample: true
---

This is sample text, here to show how a post will look and read. The opening paragraph sets up the question the post answers, in two or three plain sentences, before the first heading.

Body text is set a little larger than the rest of the site and kept to a narrow column, because long lines are tiring to read. Links look [like this](#), and a phrase can carry **a little emphasis** where it helps.^[A note holds a clarification or a source without interrupting the sentence. Clicking the number opens and closes it.]

## Start with the question

Each section opens with a heading like the one above. On a wide screen the headings also appear in a contents list beside the text, which follows along as you read.

A second paragraph gives a sense of rhythm. Short paragraphs, each making one point, read far more easily on a screen than a wall of text.^[Notes are numbered automatically, in the order they appear.]

> A pull quote lifts the one sentence you most want a reader to remember.

After a quote, the text carries on as before. Lists are available for the moments when a few items really are parallel:

- The first item, kept to a single line where possible.
- The second item, which can run a little longer when the idea needs more room to be clear.
- The third item.

## Showing code

Inline code such as `max_attempts` sits within a sentence. Longer examples get their own block, with a button to copy them:

```python title="retry.py"
def with_retries(call, max_attempts=3):
    """Retry a flaky call a few times before giving up."""
    for attempt in range(1, max_attempts + 1):
        try:
            return call()
        except TransientError as error:
            if attempt == max_attempts:
                raise
            print(f"Attempt {attempt} failed: {error}")
```

The paragraph after a code block explains what the reader just saw, rather than leaving the code to speak for itself.

## Tables and charts

A table suits a handful of exact values that a reader will want to compare across a row.

::: table Sample data. Numbers line up on the right so they can be compared at a glance.
| Option   | Median | Slowest 1% | Trade-off                  |
| -------- | -----: | ---------: | -------------------------- |
| Option A | 120 ms |     480 ms | Simple, but slow under load |
| Option B |  95 ms |     310 ms | Needs a warm cache          |
| Option C |  70 ms |     190 ms | More moving parts           |
:::

A chart is better when the shape matters more than any one number. Charts draw themselves in as they scroll into view, and hovering shows the exact values.

::: chart A line chart, for change over time.
{
  "type": "line",
  "title": "Response time through the day",
  "subtitle": "Milliseconds, sample data",
  "unit": "ms",
  "xLabel": "Time",
  "x": ["00:00", "02:00", "04:00", "06:00", "08:00", "10:00", "12:00", "14:00", "16:00", "18:00", "20:00", "22:00"],
  "series": [
    {"name": "Before", "values": [112, 108, 104, 118, 141, 156, 163, 158, 149, 152, 137, 121]},
    {"name": "After", "values": [84, 81, 79, 86, 97, 104, 109, 106, 101, 103, 95, 88]}
  ]
}
:::

::: chart A column chart, for comparing a few categories.
{
  "type": "bar",
  "title": "Where the time goes",
  "subtitle": "Milliseconds per stage, sample data",
  "unit": "ms",
  "xLabel": "Stage",
  "x": ["Parse", "Route", "Retrieve", "Generate", "Format"],
  "series": [{"name": "Time", "values": [8, 14, 46, 118, 12]}]
}
:::

## Diagrams and asides

A diagram shows how the parts of a system connect. It uses the same colours as the rest of the page and adapts to light and dark.

::: diagram A sample diagram. The dashes move in the direction the request travels.
<svg viewBox="0 0 600 200" role="img" aria-label="A request goes to a router, which sends it to either a cache or a model, and both return a response.">
  <defs>
    <marker id="arrow" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0 L8 4 L0 8 Z"/></marker>
  </defs>
  <path class="edge" marker-end="url(#arrow)" d="M130 100 H176"/>
  <path class="edge" marker-end="url(#arrow)" d="M290 92 C 316 92, 314 48, 336 48"/>
  <path class="edge" marker-end="url(#arrow)" d="M290 108 C 316 108, 314 152, 336 152"/>
  <path class="edge" marker-end="url(#arrow)" d="M450 48 C 470 48, 460 88, 476 88"/>
  <path class="edge" marker-end="url(#arrow)" d="M450 152 C 470 152, 460 112, 476 112"/>
  <rect class="box" x="20" y="78" width="110" height="44" rx="12"/>
  <text x="75" y="100" text-anchor="middle" dominant-baseline="central">Request</text>
  <rect class="box box--accent" x="180" y="78" width="110" height="44" rx="12"/>
  <text x="235" y="100" text-anchor="middle" dominant-baseline="central">Router</text>
  <rect class="box" x="340" y="26" width="110" height="44" rx="12"/>
  <text x="395" y="42" text-anchor="middle" dominant-baseline="central">Cache</text>
  <text class="sub" x="395" y="57" text-anchor="middle" dominant-baseline="central">fast path</text>
  <rect class="box" x="340" y="130" width="110" height="44" rx="12"/>
  <text x="395" y="146" text-anchor="middle" dominant-baseline="central">Model</text>
  <text class="sub" x="395" y="161" text-anchor="middle" dominant-baseline="central">slow path</text>
  <rect class="box" x="480" y="78" width="100" height="44" rx="12"/>
  <text x="530" y="100" text-anchor="middle" dominant-baseline="central">Response</text>
</svg>
:::

::: aside
**An aside.** A boxed note is for context that is useful but would interrupt the main line of thought, such as a definition or a caveat.
:::

## Closing

The last section brings the post back to the question it opened with and says plainly what the answer was.

It ends without a summary of everything above. A reader who got this far already knows what the post said.
