# Suggestions for all 174 redistribution decisions

Advisory material for the reviewer. No approvals, decisions imports, builds, uploads or GPU runs are performed.

The [companion CSV](wheelhouse_redistribution_suggestions_r4.csv) gives every exact r4 artifact a suggested review path and next action, alongside its original conditions, unresolved questions and evidence.

| Review group | Rows |
|---|---:|
| NVIDIA deployment assessment | 13 |
| CUTLASS viability | 2 |
| Explained metadata discrepancy | 3 |
| Licence identity and component review | 2 |
| Native-library assessment | 3 |
| Open Apache NOTICE evidence | 20 |
| Known NOTICE packaging | 8 |
| Source availability | 5 |
| CUDA Python own licence | 2 |
| Repository-only NOTICE | 1 |
| Routine per-artifact review | 115 |

Recommended order: settle CUTLASS bundle viability and owner deployment facts first; review the shared NVIDIA memo next. Routine rows, known notices, metadata discrepancies and source-access work can proceed independently.

Use approved_with_conditions when material conditions remain, and document satisfaction only when evidence exists. Routine notice obligations can be recorded in required_notices; the reviewer chooses whether additional conditions are needed. Planned future work is not proof of fulfilment.

Keep every decision separate and tied to issued r4 evidence. Shared memos can be cited by multiple rows. Do not manufacture reviewer names, dates, reconfirmations or condition-satisfaction records.

An inconclusive NOTICE result means the evidence is incomplete, not that redistribution is forbidden. Apache section 4(d) concerns notices included in the Work; the reviewer must determine the actual distributed components. Unknown third-party notices cannot be replaced by a generic NOTICE.

Source archive checksums are useful audit evidence, not a universal licence requirement. For copyleft-covered libraries, source must correspond to the shipped components; copying a generic upstream link is insufficient evidence of that correspondence.

If a required dependency is restricted or excluded, the current bundle stays blocked. A replacement needs an explicit new runtime/dependency set and fresh closure and installation validation. Private Kaggle visibility is a deployment fact, not permission by itself.

Primary licence references:

- [CUTLASS Software License Agreement](https://docs.nvidia.com/cutlass/latest/media/docs/pythonDSL/license.html)
- [CUDA 12.8.1 EULA](https://docs.nvidia.com/cuda/archive/12.8.1/eula/index.html)
- [Apache License 2.0, section 4](https://www.apache.org/licenses/LICENSE-2.0)
- [MPL 2.0, section 3](https://www.mozilla.org/en-US/MPL/2.0/)
- [FFmpeg LGPL compliance guidance](https://ffmpeg.org/legal.html)
- [FreeType licence choices](https://freetype.org/license.html)

Basis: [issued worksheet r4](wheelhouse_redistribution_decision_worksheet_r4.csv), SHA-256 2f08e622892f597aa2447e76b42005f0e67beb8e5243dc3377b449d17b409bc5. [Coverage record](wheelhouse_redistribution_suggestions_r4.json).
