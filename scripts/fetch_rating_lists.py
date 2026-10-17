'''
Created on 16 October 2026

retrieve January rating snapshots while retaining unavailable years

@author: Dinghao Luo
'''

#%% imports
import csv
import hashlib
import io
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import urlopen
from zipfile import ZipFile

from bs4 import BeautifulSoup


#%% sources
def fetch(year: int) -> dict:
    folder = Path('cache/research/ratings')
    folder.mkdir(exist_ok=True)
    row = {'year': year, 'date': f'{year}-01-01', 'url': '', 'file': '', 'sha256': '', 'bytes': '',
           'status': 'unavailable', 'source': 'olimpbase' if year <= 2001 else 'fide', 'limit': ''}
    if year in [1972, 1973, 1974]:
        row['limit'] = 'no January list linked by the historical summary; no substitution of another month'
        return row
    if year <= 2001:
        url = f'https://www.olimpbase.org/Elo/Elo{year}01e.html'
        filename = f'olimpbase-{year}.html'
    else:
        prefix = '' if year <= 2012 else 'standard_'
        url = f'https://ratings.fide.com/download/{prefix}jan{year % 100:02d}frl.zip'
        filename = f'fide-{year}.zip'
    row['url'] = url
    path = folder / filename
    existing = folder.parent / filename
    if not path.exists() and existing.exists():
        path.write_bytes(existing.read_bytes())
    try:
        if not path.exists():
            with urlopen(url, timeout=45) as response:
                raw = response.read()
            if year <= 2001:
                soup = BeautifulSoup(raw, 'html.parser')
                if soup.pre is None or str(year) not in soup.title.get_text():
                    raise ValueError('rating page lacks the expected dated player list')
            else:
                with ZipFile(io.BytesIO(raw)) as archive:
                    assert any(name.lower().endswith('.txt') for name in archive.namelist())
            path.write_bytes(raw)
        raw = path.read_bytes()
        row.update({'file': str(path), 'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw), 'status': 'available'})
        if year == 1971:
            row['limit'] = 'January 1971 is unofficial; excluded from the main official-list series'
    except (HTTPError, URLError, TimeoutError) as error:
        row['limit'] = type(error).__name__ + ': ' + str(error)
    return row


#%% main
def main() -> None:
    with ThreadPoolExecutor(max_workers=6) as pool:
        rows = list(pool.map(fetch, range(1971, 2027)))
    path = Path('data/curated/rating_sources.csv')
    with path.open('w', newline='') as destination:
        writer = csv.DictWriter(destination, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
    print(sum(row['status'] == 'available' for row in rows), 'January snapshots retrieved;',
          sum(row['status'] != 'available' for row in rows), 'visible gaps')


if __name__ == '__main__':
    main()
