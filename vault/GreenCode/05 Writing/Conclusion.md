---
title: Conclusion
created: 2026-10-22
project: GreenCode
type: report-section
tags: [writing, conclusion]
---

# Conclusion / Summary of the project idea

## Brief
"Just give a conclusion of the idea, don't speak about timelines"; one sentence ("My project asks whether…") rephrased on request.

## Final text
**Conclusion**

GreenCode starts from a simple discomfort: large language models will happily rewrite Python and SQL "for efficiency", and almost nothing in the usual workflow checks whether the result is correct, faster, or any greener. The literature confirms the worry. Model-generated code is usually right but rarely energy-efficient, and a quicker run does not always mean a smaller footprint. My project asks whether a modest, deterministic intervention changes that: give the model a precise, static-analysis finding instead of a vague instruction, then refuse to believe anything it returns until it has been tested, benchmarked and measured.

The system is the instrument for that question rather than the point of it. It detects known inefficiencies with a fixed rule catalogue, asks a locally hosted model for an optimisation under two controlled conditions, rejects incorrect candidates in a sandbox, and records timing, energy and CO₂e for every survivor, labelling each figure as measured or estimated. Four hypotheses, on correctness, speed, energy and the gap between time and energy, give the experiment something to support or refute, and failed optimisations count as evidence rather than embarrassment.

Whatever the results show, the contribution is a way of holding AI-generated code to account: not "the model said so", but "here is what it did, here is what we measured, and here is how sure we are".

(≈215 words)

**Final rephrasing of the "My project asks whether…" sentence (turn 113, replacing the sentence in paragraph 1 above):**

My project asks whether a small, deterministic change to the process makes a measurable difference: tell the model exactly what is inefficient, using a static-analysis finding rather than a general request to optimise, and then treat whatever it produces as a hypothesis to be tested, benchmarked and measured before it is accepted.

(So the final paragraph 1 reads: "GreenCode starts from a simple discomfort: large language models will happily rewrite Python and SQL "for efficiency", and almost nothing in the usual workflow checks whether the result is correct, faster, or any greener. The literature confirms the worry. Model-generated code is usually right but rarely energy-efficient, and a quicker run does not always mean a smaller footprint. My project asks whether a small, deterministic change to the process makes a measurable difference: tell the model exactly what is inefficient, using a static-analysis finding rather than a general request to optimise, and then treat whatever it produces as a hypothesis to be tested, benchmarked and measured before it is accepted.")
