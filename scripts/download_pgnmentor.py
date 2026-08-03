'''
Created on 2 August 2026

download world championship pgns from pgnmentor.com

@author: Dinghao Luo
'''

import re
import time
import urllib.request
from pathlib import Path

BASE = 'https://www.pgnmentor.com'
OUT = Path('data/raw/pgnmentor')
UA = {'User-Agent': 'Mozilla/5.0'}
PATTERN = re.compile(r'events/((?:WorldChamp|FideChamp|PCAChamp)[^"]*\.pgn)')
fetch = lambda path: urllib.request.urlopen(urllib.request.Request(f'{BASE}/{path}', headers=UA)).read()

# we have to scrape the file index for every WCC-lineage pgn, since pgnmentor has no api
names = sorted(set(PATTERN.findall(fetch('files.html').decode())))

OUT.mkdir(parents=True, exist_ok=True)
for name in names:
    p = OUT / name
    if p.exists():
        continue
    p.write_bytes(fetch(f'events/{name}'))
    print(name)
    time.sleep(1)
