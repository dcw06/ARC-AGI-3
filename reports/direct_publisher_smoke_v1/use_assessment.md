# Direct consumption assessment draft

Status: reviewer proposal, not permission or a redistribution decision. Scope: consuming the existing publisher dataset `driessmit1/arc3-vllm-h100-wheelhouse-v3`, requested version 1, with the trusted 174-wheel inventory in the intake package. This draft does not authorize GPU compute.

## Deployment facts required for review

The deployment facts supplied in conversation are retained locally and excluded from this public draft. The consuming account, actual recipients and roles, access controls, publication intent, applicable vendor agreements and output/payload handling must be provided privately to the reviewer and bound to the final use assessment. This draft asserts no particular deployment facts or reviewer outcome.

The proposed act is mounting the existing publisher dataset and installing its unmodified wheels into a fresh temporary environment using our trusted hash-pinned lock. Creating or uploading an independently hosted wheelhouse is outside this proposal. Actual output/export/retention behavior still needs to be recorded before final package review.

## Rights to assess separately

The retained [CUTLASS 4.5.0 EULA](../wheelhouse_evidence/sources/cutlass-v4.5.0-EULA.txt) has an installation/use grant in section 1.1(a), separate from the Python-source distribution grant in section 1.1(d). Sections 2.2 and 3 address making material available to others and authorized users. Therefore the existing failure to identify a binary redistribution grant does not, by itself, answer whether this account's direct installation and use is permitted. The reviewer must assess the actual received copy, applicability/acceptance of that EULA, the intended use and teammate access. This is a question to resolve, not a conclusion that the publisher or consumer is cleared. The original [CUTLASS binary evidence pack](../wheelhouse_evidence/cutlass_binaries.md) remains unchanged.

Similarly, the [CUDA Toolkit 12.8.1 EULA](https://docs.nvidia.com/cuda/archive/12.8.1/eula/index.html) separates installation/use from distribution in section 1.1.1, and addresses authorized-user access in section 1.1.3. These clauses support reviewing the actual proposed acts separately. They do not automatically cover every NVIDIA package or establish that collaborators are authorized users under the actual accepting account. Exact governing texts, supplements and any applicable separate component terms still need confirmation. See the retained [NVIDIA deployment evidence](../wheelhouse_evidence/nvidia_deployment_assessment.md) for the cuDNN text discrepancy, cuSPARSELt release-text gap and component-specific questions.

Public access, matching hashes and a dataset licence label do not prove the publisher's rights or resolve the consumer's obligations. Review the legitimacy and licence coverage of the received copies; a consumer-use permission assessment must not be substituted for approval of the publisher's distribution or our own repackaging. Confirm where standard terms require acceptance and how that is satisfied for the account holder and other users.

For the other wheel components, classify actual obligations by their triggering act (installation/use, copying, modification, sharing or redistribution). Preserve bundled notices through installation. Reassess source/NOTICE delivery duties if installed binaries, archives, images or wheel files are exported/shared. Do not automatically mark all 52 original condition gaps as irrelevant, or carry them over unchanged. No original worksheet entry is modified by this draft.

## Reviewer questions still open

- Is the account holder accepting individually or for an entity, and what is each teammate's relationship to that licence holder? If each user relies on independent acceptance, does that cover the shared hosted access model?
- Does private invite-only Kaggle access satisfy the applicable terms for these exact components, including copying and authorized-user access?
- Are the governing texts and accepted distribution/source provenance established for the actual copies, including CUTLASS's compiled payloads and the NVIDIA subcomponents?
- Will wheel files, installed payloads, logs, archives, notebook outputs or images be retained, exported or shared, and with whom?
- Which obligations apply to those acts, and what evidence demonstrates their satisfaction?

The reviewer outcome must bind the answered facts, exact dataset/version and trusted inventory. Future publication or an expanded recipient group requires reassessment; it is not covered by a private-use outcome. Final source review and exact compute authorization remain separate gates.
