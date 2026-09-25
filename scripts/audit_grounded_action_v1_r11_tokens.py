"""Audit R11 exact requests with the archived pinned tokenizer, without model calls."""
import json
from pathlib import Path
import tempfile
import zipfile

from scripts.audit_grounded_action_v1_tokens import run

ROOT = Path(__file__).resolve().parents[1]


def main():
    source = ROOT / 'evidence/phase4-transient-v1-tokenizer.zip'
    record = ROOT / 'reports/runs/phase4-grounded-action-v1-r11-local/run.json'
    output = ROOT / 'reports/perception_stage_b_r11_token_audit.json'
    with tempfile.TemporaryDirectory(prefix='stage-b-r11-tokenizer-') as folder:
        with zipfile.ZipFile(source) as archive:
            for name in archive.namelist():
                if Path(name).name != name:
                    raise ValueError('unsafe tokenizer archive path')
            archive.extractall(folder)
        result = run(record, Path(folder), output)
    if (len(result['exact_requests']) != 12 or
            not all(row['admissible'] for row in result['exact_requests'] + result['feedback_frame_stress']) or
            not all(row['fits'] for row in result['bounded_response_examples'])):
        raise ValueError('R11 token audit failed')
    print(json.dumps({'exact_requests': len(result['exact_requests']),
                      'maximum_prompt_tokens': max(row['prompt_tokens'] for row in result['exact_requests']),
                      'maximum_stress_tokens': max(row['prompt_tokens'] for row in result['feedback_frame_stress']),
                      'maximum_response_tokens_plus_end': max(row['tokens_plus_end'] for row in result['bounded_response_examples'])}))


if __name__ == '__main__':
    main()
