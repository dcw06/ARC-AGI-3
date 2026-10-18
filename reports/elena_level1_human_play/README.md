# Elena (Mac teammate) — Level 1 human-play logs and answers

Elena's assigned games are **ar25, su15, tr87, vc33 and wa30**. All five first levels are completed. Each game folder contains its human-play log, English answers to questions 1–7, an action summary and an extraction receipt.

| Game | Actions through first completion | Evidence | Questionnaire |
| --- | ---: | --- | --- |
| ar25 | 17 | [Log](ar25/level1.log.json) | [Answers 1–7](ar25/answers-1-7.txt) |
| su15 | 18 | [Log](su15/level1.log.json) | [Answers 1–7](su15/answers-1-7.txt) |
| tr87 | 42 | [Log](tr87/level1.log.json) | [Answers 1–7](tr87/answers-1-7.txt) |
| vc33 | 6 | [Log](vc33/level1.log.json) | [Answers 1–7](vc33/answers-1-7.txt) |
| wa30 | 191 | [Log](wa30/level1.log.json) | [Answers 1–7](wa30/answers-1-7.txt) |

The logs preserve the original human actions, unsuccessful attempts, returned frames and timestamps. Each ends with the first action changing `levels_completed` from 0 to 1. The completion action can return animation and the next board; no subsequent-level actions are included. AR25 uses an existing session from October 14, 2026; the other four sessions are from October 18, 2026. Coordinates use zero-based `(x,y) = (column,row)`.

Answers distinguish observations, inferred rules and untested mechanics. Question 7 discusses expectations as hypotheses where no contemporaneous note records a personal expectation. These are first-level observations, not claims about later levels or model performance.

`submission-manifest.json` records SHA-256 hashes for each log and answer file. Extraction receipts identify the original exports; those full-session source exports remain local. The historical source hashes refer to those original files, not the extracted logs.

[Download all five games](elena-five-games-level1-submission.zip).

The local game recorder and coordinate tools are in [human_play](../../human_play/README.md). This package adds Elena's completed human-play evidence and questionnaire responses.
