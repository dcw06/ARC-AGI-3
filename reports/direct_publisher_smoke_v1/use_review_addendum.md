# Direct installation/use review addendum

Prepared October 6, 2026. Reviewer proposal only; no permission decision, source approval, compute authorization or redistribution decision is supplied by this document. Deployment facts and account evidence remain in the local private operational package.

The runtime candidate consumes the existing publisher dataset rather than creating another wheelhouse. Its trusted package/version pins and 174 wheel hashes remain unchanged. Installation uses an unmodified temporary environment; the runner removes that environment and embedded sources and retains bounded smoke-test evidence. The actual recipient and export scope must be selected and reviewed before use is cleared.

## Grants and the act being reviewed

| Component | Installation/use evidence | Separate questions |
|---|---|---|
| CUTLASS DSL 4.5.0.dev0 and its base libraries | Retained v4.5.0 EULA section 1.1(a) grants installation/use; section 1.1(d) separately addresses Python-source distribution. | Establish the governing terms and acceptance for the actual copies, including compiled payloads. Section 2.2 restricts making software available to others; section 3 addresses authorized users. No binary redistribution permission is inferred. |
| CUDA Toolkit 12.8.1 components | Archived EULA section 1.1.1(1) addresses installation/use; section 1.1.1(3) and 1.1.2 address distribution. | Confirm the exact governing texts and supplements, recipient scope, acceptance and hosting model. The distribution list does not alone answer the installation/use question. |
| cuDNN 9.10.2 | Release-specific SLA, License/Grant item 1, addresses installation/use. | The retained bundled/release-text discrepancy remains, particularly the treatment of third-party components. Resolve it for these exact copies. |
| cuSPARSELt 0.7.1 | Current NVIDIA licence page, section 1.1 item 1, addresses installation/use. | This is current documentation, not established release-specific evidence for 0.7.1. Do not label that historical-text gap resolved. |
| NVSHMEM 3.4.5 | Retained product evidence identifies its own supplement; the CUDA assessment cannot replace it. | Apply the actual NVSHMEM terms and supplement to the reviewed use. |
| MPL components, including libzmq | Mozilla's MPL FAQ Q5 distinguishes use from distribution obligations; Q17 distinguishes delivering software copies from providing server functionality. | Actual copying/sharing/export behavior matters. Do not assume independent collaborators constitute one organization or that a private visibility setting establishes a distribution exemption. |
| Other permissive and copyleft components | Existing per-wheel evidence and notices remain the review inputs. | Reassess obligations by the actual act. No blanket clearance for all remaining rows, and no automatic transfer of all 67 R2 redistribution findings to direct use. |

Primary sources: [CUTLASS licence](https://docs.nvidia.com/cutlass/latest/media/docs/pythonDSL/license.html), [retained CUTLASS release text](../wheelhouse_evidence/sources/cutlass-v4.5.0-EULA.txt), [CUDA 12.8.1 EULA](https://docs.nvidia.com/cuda/archive/12.8.1/eula/index.html), [cuDNN 9.10.2 SLA](https://docs.nvidia.com/deeplearning/cudnn/backend/v9.10.2/reference/eula.html), [current cuSPARSELt SLA](https://docs.nvidia.com/cuda/cusparselt/license.html), [Mozilla MPL FAQ](https://www.mozilla.org/en-US/MPL/2.0/FAQ/). Current web pages supplement the retained release evidence; they do not establish that newer text governs older wheels.

## Recipient scope

CUDA section 1.1.3 and the cuDNN Authorized Users clause refer to employees/contractors of an entity and, separately, users enrolled or employed by an academic institution when that institution is the licensee. CUTLASS section 3 has a similar distinction. Student enrollment alone does not establish that an individual's independent collaborators qualify through an institutional licence. That is an assessment implication of the clauses, not a finding that independently licensed collaborators can never use the software.

An account-only smoke test with no collaborator SDK access is a narrower option to submit for review. It is not selected, permitted or enforced by this document. Independently accepted licences, sharing only non-payload results, and institutional use are distinct possible models and must not be conflated. Any existing notebook collaborator permissions must be checked rather than assumed absent.

## Evidence needed for the outcome

The private assessment must state the actual licence holder, recipients and their roles, account/notebook access controls, publication intent, applicable agreements, acceptance and copy provenance, output/payload handling, and the exact retained licence evidence. A reviewer outcome must cover the exact dataset/version, trusted wheel inventory and lock, and privately bound review snapshot, with every outstanding condition resolved.

Only scoped source and compute approvals following that outcome can authorize the live path. Authentication, a successful CPU byte check, a filled account binding, or an installation/use grant in one component's terms cannot substitute for those approvals. Original redistribution worksheets, authoritative decisions and R2 bundle findings remain unchanged.
