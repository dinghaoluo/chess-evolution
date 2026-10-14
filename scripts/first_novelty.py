'''
Created on 4 August 2026

compute first novelty ply in each game

@author: Dinghao Luo
'''

#%% imports
import csv
import itertools
from pathlib import Path


#%% paths
GAMES = Path('data/games.csv')
OUT = Path('data/novelty.csv')


#%% main
seen = set()
results = []

with open(GAMES) as f:
    games = [list(plies) for _, plies in itertools.groupby(csv.DictReader(f), key=lambda r: r['game_id'])]

games.sort(key=lambda g: g[0]['date'])

for plies in games:
    first = plies[0]
    novelty_ply = None
    keys = []
    for row in plies:
        # first 4 FEN fields: piece placement, side, castling, ep square
        # (ignore move counters so transpositions collapse)
        k = ' '.join(row['fen'].split()[:4])
        keys.append(k)
        if novelty_ply is None and k not in seen:
            novelty_ply = int(row['ply'])

    results.append({
        'game_id': first['game_id'],
        'date': first['date'],
        'white': first['white'],
        'black': first['black'],
        'event': first['event'],
        'first_novelty_ply': novelty_ply or '',
    })
    seen.update(keys)


#%% write
COLS = ['game_id', 'date', 'white', 'black', 'event', 'first_novelty_ply']

with open(OUT, 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=COLS)
    writer.writeheader()
    writer.writerows(results)
