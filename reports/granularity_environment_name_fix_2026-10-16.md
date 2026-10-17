# Backend version-lock distribution-name correction

The first real UnSAMv2+ seeded CPU smoke stopped before model loading because
the exact environment inventory recorded the wheel's name `pillow`, while the
required-package gate tested for the spelling `Pillow`.

The gate now uses canonical distribution names (case folding and normalization
of hyphens, underscores and periods) for required-package and alias checks.
Exact installed versions are still checked. Duplicate aliases and missing
required distributions are refused. Two focused regression tests pass,
including the lowercase, title-case and uppercase Pillow spellings.

The failed CPU attempt is preserved with no model request or inference. Its
process-group cleanup verified absence. No GPU job or Kaggle call occurred.
This code correction does not itself establish model-runtime compatibility.
