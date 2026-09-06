"""The light monitoring job (Module 3, Part B).

The minimum CD loop: point the same evaluators at the live stream. Code
checks run on 100 percent of traffic because they are free; the frozen
Module 2 judges run on a sample because they cost money; direct Python code
corrects the sampled counts into per-mode prevalence intervals; and
the corrected number is written back onto the traces as Langfuse scores.

  - sample.py     the stratified sampling plan (hw7 hole)
  - correct.py    Rogan-Gladen correction and bootstrap interval (hw7 hole)
  - write_scores.py  repeatable score records (hw7 hole) + the Langfuse wiring
  - run_judges.py the frozen judges over the sample (instructor-provided)
  - chart.py      the prevalence-over-time chart with a threshold line
"""
