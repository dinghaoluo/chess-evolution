'''
Created on 4 August 2026

compute position novelty against earlier reviewed championship events

@author: Dinghao Luo
'''

#%% imports
import csv
import itertools
import random
from pathlib import Path


#%% paths
DATA = Path('data')
REFERENCE_GAMES = 100
REPEATS = 20


#%% load
with (DATA / 'events.csv').open() as source:
    events = {row['event_id']: row for row in csv.DictReader(source)}
with (DATA / 'game_classifications.csv').open() as source:
    accepted = {
        row['game_id']: row for row in csv.DictReader(source)
        if row['accepted_for_analysis'] == '1' and row['game_class'] == 'classical'
        and events[row['event_id']]['lineage'] != 'split_fide'
    }

games = []
with (DATA / 'games.csv').open() as source:
    for game_id, plies in itertools.groupby(csv.DictReader(source), key=lambda row: row['game_id']):
        rows = list(plies)
        if game_id not in accepted:
            continue
        classification = accepted[game_id]
        # ignore counters so different move orders can reach the same position
        positions = [' '.join(row['fen'].split()[:4]) for row in rows]
        games.append((classification, positions))
assert len(games) == len(accepted)
games.sort(key=lambda game: int(events[game[0]['event_id']]['order']))


#%% novelty
def first_novelty(positions: list[str], reference: set[str]) -> int | None:
    return next((ply for ply, position in enumerate(positions, 1) if position not in reference), None)


history = []
seen = set()
results = []
sensitivity = []

for event_id, event_games in itertools.groupby(games, key=lambda game: game[0]['event_id']):
    event_games = list(event_games)
    references = []
    if len(history) >= REFERENCE_GAMES:
        for seed in range(REPEATS):
            sample = random.Random(seed).sample(history, REFERENCE_GAMES)
            references.append(set().union(*sample))
    for game, positions in event_games:
        novelty = first_novelty(positions, seen)
        row = {
            'game_id': game['game_id'],
            'event_id': event_id,
            'year': events[event_id]['year'],
            'date': game['date'],
            'white': game['white'],
            'black': game['black'],
            'plies': len(positions),
            'reference_games': len(history),
            'first_novelty_ply': novelty if novelty is not None else '',
            'censored': int(novelty is None),
        }
        results.append(row)
        for seed, reference in enumerate(references):
            sampled_novelty = first_novelty(positions, reference)
            sensitivity.append({
                **row,
                'reference_games': REFERENCE_GAMES,
                'first_novelty_ply': sampled_novelty if sampled_novelty is not None else '',
                'censored': int(sampled_novelty is None),
                'seed': seed,
            })
    # update between events because many game dates are incomplete
    for _, positions in event_games:
        history.append(set(positions))
        seen.update(positions)


#%% write
for name, rows in [('novelty.csv', results), ('novelty_sensitivity.csv', sensitivity)]:
    with (DATA / name).open('w', newline='') as destination:
        writer = csv.DictWriter(destination, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
print(f'{len(results)} main-line classical games; {len(sensitivity)} fixed-archive comparisons')
