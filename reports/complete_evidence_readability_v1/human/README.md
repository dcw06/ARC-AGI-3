# Reviewer instructions

You are checking whether one text record can be read. Use only the input file. It is exactly what Opus
would receive.

**Do not open** `../sealed/`, `../frozen/source_frames.npz`, `../README.md`, the other reports, or any
picture of the game before both of your answer files are saved. Do not discuss with the other reviewer until then.

| | Read first | Read second |
|---|---|---|
| Reviewer 1 | `../frozen/input_A.txt` | `../frozen/input_B.txt` |
| Reviewer 2 | `../frozen/input_B.txt` | `../frozen/input_A.txt` |

1. Copy `answer_form.json` to `reviewer1_A.json` (your number and the input you are reading).
2. Read the first input. Fill in every answer. Write `"cannot determine"` where the text does not tell you.
   Note the minutes taken and anything that was hard or missing.
3. Save the file. Do not change it afterwards.
4. Repeat with the second input in a new file (`reviewer1_B.json`), marked `"read_order": "second"`.

Your first-read answers are the main result: by the second read you already know the answers. Pencil
and paper are fine. A computer program to decode the text is not, because Opus will not have one.

If you have read the Phase 1 reports you already know roughly what this example is about. Say so in
`what_was_hard_or_missing`; it does not disqualify you, but it is recorded.
