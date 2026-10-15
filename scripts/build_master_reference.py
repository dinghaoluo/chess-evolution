'''
Created on 15 October 2026

index dated Lumbra batches against the championship positions

@author: Dinghao Luo
'''

#%% imports
import csv
import hashlib
import itertools
import json
import shutil
import subprocess
from datetime import date
from pathlib import Path
from urllib.request import Request, urlopen

import chess


#%% targets
DATA = Path('data')
CACHE = Path('.venv/master-reference')
INDEXER = Path('.venv/master-index-build/release/master-index')
PAGE = 'https://lumbrasgigabase.com/en/download-the-scid-database-en/'
BATCHES = ['0001-1899', '1900-1949', '1950-1969', '1970-1989', '1990-1999',
           '2000-2004', '2005-2009', '2010-2014', '2015-2019', '2020-2024']
CACHE.mkdir(exist_ok=True, parents=True)
with (DATA / 'novelty.csv').open() as source:
    accepted = {row['game_id']: row for row in csv.DictReader(source)}
# track moves too: a new move order can reach a familiar position
positions = set()
edges = set()
games = []
with (DATA / 'games.csv').open() as source:
    for game_id, records in itertools.groupby(csv.DictReader(source), key=lambda row: row['game_id']):
        records = list(records)
        if game_id in accepted:
            positions.update(' '.join(row['fen'].split()[:4]) for row in records)
            previous = ' '.join(chess.STARTING_FEN.split()[:4])
            for row in records:
                edges.add((previous, row['move_uci']))
                previous = ' '.join(row['fen'].split()[:4])
            games.append({'game_id': game_id, 'moves_uci': ' '.join(row['move_uci'] for row in records),
                          'white': accepted[game_id]['white'], 'black': accepted[game_id]['black']})
with (DATA / 'master_positions.csv').open('w', newline='') as destination:
    writer = csv.writer(destination, lineterminator='\n')
    writer.writerow(['position_id', 'fen', 'previous_fen', 'move_uci'])
    writer.writerows((i, fen + ' 0 1', '', '') for i, fen in enumerate(sorted(positions), 1))
    writer.writerows((i, '', fen + ' 0 1', move) for i, (fen, move) in enumerate(sorted(edges), len(positions) + 1))
target_hash = hashlib.sha256((DATA / 'master_positions.csv').read_bytes()).hexdigest()
target_games = CACHE / 'target_games.csv'
with target_games.open('w', newline='') as destination:
    writer = csv.DictWriter(destination, fieldnames=['game_id', 'moves_uci', 'white', 'black'], lineterminator='\n')
    writer.writeheader()
    writer.writerows(games)
games_hash = hashlib.sha256(target_games.read_bytes()).hexdigest()
indexer_hash = hashlib.sha256(INDEXER.read_bytes()).hexdigest()


#%% download and index one batch at a time
manifest = []
with (DATA / 'master_database_sources.csv').open() as source:
    frozen_sources = {row['batch']: row for row in csv.DictReader(source)}
for period in BATCHES:
    batch = 'otb-' + period
    prefix = CACHE / batch
    record_path = prefix.with_suffix('.source.json')
    if record_path.exists():
        record = json.loads(record_path.read_text())
        assert record['target_sha256'] == target_hash
        assert record['target_games_sha256'] == games_hash
        assert record['indexer_sha256'] == indexer_hash, 'remove stale batch source records before rebuilding'
    else:
        archive = CACHE / (batch + '.7z')
        if not archive.exists():
            with urlopen(Request(frozen_sources[batch]['download_url'], headers={'User-Agent': 'chess-research/1.0'}), timeout=120) as response:
                with archive.open('wb') as destination:
                    shutil.copyfileobj(response, destination)
        digest = hashlib.file_digest(archive.open('rb'), 'sha256').hexdigest()
        assert digest == frozen_sources[batch]['archive_sha256'], 'exclusion ordinals require the frozen source archive'
        members = subprocess.check_output(['bsdtar', '-tf', str(archive)], text=True).splitlines()
        pgns = [name for name in members if name.endswith('.pgn')]
        assert len(pgns) == 1, members
        unpack = subprocess.Popen(['bsdtar', '-xOf', str(archive), pgns[0]], stdout=subprocess.PIPE)
        indexed = subprocess.Popen([str(INDEXER), str(DATA / 'master_positions.csv'), str(target_games),
                                    str(prefix)],
                                   stdin=unpack.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        unpack.stdout.close()
        output, errors = indexed.communicate()
        assert indexed.returncode == 0, errors
        assert unpack.wait() == 0
        record = {
            'batch': batch, 'download_url': frozen_sources[batch]['download_url'],
            'source_page': PAGE, 'retrieved_at': date.today().isoformat(),
            'archive_sha256': digest, 'archive_bytes': archive.stat().st_size,
            'pgn_member': pgns[0], 'target_sha256': target_hash,
            'target_games_sha256': games_hash, 'indexer_sha256': indexer_hash,
            'licence': 'CC BY-NC 4.0', 'attribution': 'Lumbra Gigabase, Michael Jansen',
            **json.loads(output),
        }
        record_path.write_text(json.dumps(record, indent=2) + '\n')
        archive.unlink()
    manifest.append(record)
    print(batch, record['games'], 'games;', record['rejected_games'], 'rejected', flush=True)

with (DATA / 'master_database_sources.csv').open('w', newline='') as destination:
    writer = csv.DictWriter(destination, fieldnames=list(manifest[0]), lineterminator='\n')
    writer.writeheader()
    writer.writerows(manifest)


#%% outputs
for suffix, name in [('years', 'master_database_coverage'), ('errors', 'master_database_rejections'),
                     ('matches', 'master_game_matches'), ('excluded', 'master_reference_exclusions')]:
    with (DATA / (name + '.csv')).open('w', newline='') as destination:
        writer = None
        for period in BATCHES:
            batch = 'otb-' + period
            with (CACHE / (batch + '.' + suffix + '.csv')).open() as source:
                reader = csv.DictReader(source)
                if writer is None:
                    writer = csv.DictWriter(destination, fieldnames=['batch'] + reader.fieldnames, lineterminator='\n')
                    writer.writeheader()
                writer.writerows({'batch': batch, **row} for row in reader
                                 if suffix != 'errors' or not row['reason'].startswith('excluded '))
