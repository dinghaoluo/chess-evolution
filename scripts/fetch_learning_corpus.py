'''
Created on 16 October 2026

retrieve the learning-pilot batches and compare their archived fingerprints

@author: Dinghao Luo
'''

#%% imports
import csv
import hashlib
import json
import shutil
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup


#%% downloads
def retrieve(row: dict) -> dict:
    path = Path('cache/learning') / (row['batch'] + '.7z')
    if not path.exists():
        temporary = path.with_suffix('.part')
        with urlopen(Request(row['download_url'], headers={'User-Agent': 'chess-research/1.0'}), timeout=120) as source:
            with temporary.open('wb') as destination:
                shutil.copyfileobj(source, destination)
        temporary.rename(path)
    with path.open('rb') as source:
        digest = hashlib.file_digest(source, 'sha256').hexdigest()
    result = {key: row[key] for key in ['batch', 'download_url', 'source_page', 'pgn_member', 'licence', 'attribution']}
    result.update({'file': str(path), 'retrieved_at': '2026-10-16', 'archived_sha256': row['archive_sha256'],
                   'sha256': digest, 'bytes': path.stat().st_size,
                   'status': 'archived_hash_match' if digest == row['archive_sha256'] else 'changed_download'})
    record_path = Path('data/curated') / (row['batch'] + '.source.json')
    record_path.write_text(json.dumps(result, indent=2) + '\n')
    print(row['batch'], result['status'], flush=True)
    return result


#%% main
def main() -> None:
    folder = Path('cache/learning')
    folder.mkdir(exist_ok=True)
    page_url = 'https://lumbrasgigabase.com/en/download-the-scid-database-en/'
    with urlopen(Request(page_url, headers={'User-Agent': 'chess-research/1.0'}), timeout=60) as response:
        page = response.read()
    page_path = folder / 'licence-page.html'
    page_path.write_bytes(page)
    soup = BeautifulSoup(page, 'html.parser')
    text = soup.get_text(' ', strip=True)
    assert 'Michael Jansen' in text and 'CC BY-NC 4.0' in text
    assert any('creativecommons.org/licenses/by-nc/4.0' in link.get('href', '') for link in soup.find_all('a'))
    archived = Path('data/local/restored/data/master_database_sources.csv')
    with archived.open() as source:
        rows = [row for row in csv.DictReader(source) if row['batch'] in
                ['otb-1970-1989', 'otb-1990-1999', 'otb-2000-2004', 'otb-2005-2009', 'otb-2015-2019', 'otb-2020-2024']]
    assert len(rows) == 6
    with ThreadPoolExecutor(max_workers=2) as pool:
        records = list(pool.map(retrieve, rows))
    output = Path('data/curated/learning_corpus_sources.json')
    output.write_text(json.dumps({'licence': 'CC BY-NC 4.0', 'licence_url': 'https://creativecommons.org/licenses/by-nc/4.0/',
                      'attribution': "Lumbra’s Gigabase, Michael Jansen, https://lumbrasgigabase.com/; source games selected and evaluated for non-commercial research",
                      'inputs_sha256': {str(archived): hashlib.sha256(archived.read_bytes()).hexdigest(),
                                        str(page_path): hashlib.sha256(page).hexdigest()},
                      'sources': records,
                      'limits': ['Changed downloads have new fingerprints; archived exclusion ordinals cannot be applied to them.',
                                 'The OTB source label does not verify classical time control or unassisted play for each game.',
                                 'Main-database licence is CC BY-NC 4.0; the separately labelled Lichess collection has a different licence.']},
                     indent=2, ensure_ascii=False) + '\n')


if __name__ == '__main__':
    main()
