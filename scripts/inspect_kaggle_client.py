"""Read installed client implementation relevant to preflight and single upload."""
from pathlib import Path
import site

for base in site.getsitepackages():
    root = Path(base)
    for package in ('kaggle', 'kagglesdk'):
        for path in (root/package).rglob('*.py'):
            lines = path.read_text(errors='replace').splitlines()
            selected = [(i, line) for i, line in enumerate(lines)
                        if ('def ' in line and any(word in line.lower() for word in
                            ('quota_view(', 'build_kaggle_client(', 'send_request(', '_send_request(', 'authenticate(')))]
            for i, line in selected:
                print(str(path)+':'+str(i+1)+': '+line.strip())
                print('\n'.join(lines[i:i+75]))
