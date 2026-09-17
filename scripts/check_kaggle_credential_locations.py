"""Diagnose credential placement without printing credential values."""
import json
import os
from pathlib import Path
from dotenv import dotenv_values

root = Path(__file__).resolve().parents[1]
folders = [root, Path('/home/jingjing/AGI')]
rows = []
for folder in folders:
    path = folder/'.env'
    fields = dotenv_values(path, interpolate=False) if path.is_file() else {}
    rows.append({'folder': str(folder), 'env_exists': path.is_file(),
                 'env_fields_nonempty': {key: bool(value) for key, value in fields.items()},
                 'token_file_present': (folder/'.kaggle/access_token').is_file(),
                 'legacy_config_present': (folder/'.kaggle/kaggle.json').is_file()})
rows.append({'standard_kaggle_config': str(Path.home()/'.kaggle'),
             'token_file_present': (Path.home()/'.kaggle/access_token').is_file(),
             'legacy_config_present': (Path.home()/'.kaggle/kaggle.json').is_file()})
print(json.dumps(rows, indent=2))
