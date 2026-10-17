'''
Created on 16 October 2026

retrieve the frozen game archives without redistributing their annotations

@author: Dinghao Luo
'''

#%% imports
import hashlib
import json
from pathlib import Path
from urllib.request import urlopen


#%% main
def main() -> None:
    folder = Path('cache/sources')
    folder.mkdir(parents=True, exist_ok=True)
    for source in json.loads(Path('data/curated/source_files.json').read_text()):
        path = folder / source['file']
        if not path.exists():
            raw = urlopen(source['url'], timeout=60).read()
            assert hashlib.sha256(raw).hexdigest() == source['sha256'], source['file']
            path.write_bytes(raw)
        assert hashlib.sha256(path.read_bytes()).hexdigest() == source['sha256'], source['file']


if __name__ == '__main__':
    main()
