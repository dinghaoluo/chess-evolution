'''
Created on 15 October 2026

read the winners’ original game archive and check the selected decisions

@author: Dinghao Luo
'''

#%% imports
import csv
import hashlib
import json
import struct
import subprocess
from pathlib import Path
from urllib.request import urlopen

import chess.pgn


#%% source archive
CACHE = Path('cache/sources')
CACHE.mkdir(parents=True, exist_ok=True)
URL = 'https://en.chessbase.com/portals/4/files/news/2005/csspalzacksgames.cbv'
archive = CACHE / 'zacks.cbv'
if not archive.exists():
    with urlopen(URL, timeout=60) as response:
        archive.write_bytes(response.read())
data = archive.read_bytes()
assert hashlib.sha256(data).hexdigest() == 'a06d648797519aa1276195935a5734de5a4db217553e18f3170044303dd9164f'

# the converter expects longer directory entries than this old container has
count, entry_size = struct.unpack_from('<HH', data, 2)
assert (count, entry_size) == (11, 149)
shift = count * (173 - entry_size)
rewrapped = bytearray(struct.pack('<HHHH', 8, count, 173, 3))
for i in range(count):
    entry = bytearray(data[8 + i * entry_size:8 + (i + 1) * entry_size])
    offset, packed, size = struct.unpack_from('<III', entry, 128)
    assert offset >= 8 + count * entry_size and offset + packed <= len(data)
    struct.pack_into('<I', entry, 128, offset + shift)
    rewrapped.extend(entry)
    rewrapped.extend(struct.pack('<IIQQ', offset + shift, 0, packed, size))
rewrapped.extend(data[8 + count * entry_size:])
converted = CACHE / 'zacks_rewrapped.cbv'
converted.write_bytes(rewrapped)
converter = 'cache/cbvault/bin/cbvault'
subprocess.run([converter, 'archive', 'extract', str(converted), str(CACHE / 'zacks'),
                '--threads', '1', '--json'], check=True, stdout=subprocess.DEVNULL)
export = CACHE / 'pal_css_2005.pgn'
subprocess.run([converter, 'pgn', str(CACHE / 'zacks/CSSPAL Freestyle Tournament'), str(export),
                '--threads', '1', '--json'], check=True, stdout=subprocess.DEVNULL)


#%% game scores and annotation locations
with export.open() as source:
    games = list(iter(lambda: chess.pgn.read_game(source), None))
assert len(games) == 27 and all(not game.errors for game in games)
rows = []
for ordinal, game in enumerate(games, 1):
    rows.append({
        'source_ordinal': ordinal, 'date': game.headers['Date'], 'round': game.headers['Round'],
        'white': game.headers['White'], 'black': game.headers['Black'], 'result': game.headers['Result'],
        'initial_fen': game.board().fen(),
        'moves_uci': ' '.join(move.uci() for move in game.mainline_moves()),
        'annotated_positions': sum(bool(node.comment) for node in game.mainline()),
    })
with Path('data/derived/pal_css_2005_games.csv').open('w', newline='') as destination:
    writer = csv.DictWriter(destination, fieldnames=list(rows[0]), lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows)
with Path('data/curated/pal_css_2005_decisions.csv').open() as source:
    for case in csv.DictReader(source):
        game = games[int(case['source_ordinal']) - 1]
        board = game.board()
        moves = list(game.mainline_moves())
        for move in moves[:int(case['ply']) - 1]:
            board.push(move)
        assert board.fen() == case['fen_before'], case['case_id']
        assert moves[int(case['ply']) - 1].uci() == case['move_uci']
        if case['reported_alternative_uci']:
            assert board.parse_uci(case['reported_alternative_uci']) in board.legal_moves
metadata = json.loads(Path('data/curated/pal_css_2005_sources.json').read_text())
assert metadata['archive_sha256'] == hashlib.sha256(data).hexdigest()
assert metadata['export_sha256'] == hashlib.sha256(export.read_bytes()).hexdigest()
print(f'{len(games)} games read')
