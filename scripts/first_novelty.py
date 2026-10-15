'''
Created on 4 August 2026

find the first position absent from earlier championship games

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
REPEATS = 100


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
        # move counters are irrelevant to opening precedent
        positions = [' '.join(row['fen'].split()[:4]) for row in rows]
        games.append((classification, positions))
assert len(games) == len(accepted)
games.sort(key=lambda game: (
    int(events[game[0]['event_id']]['order']), int(game[0]['round'].split('.')[0])
))


#%% novelty
def first_novelty(positions: list[str], reference: set[str]) -> int | None:
    return next((ply for ply, position in enumerate(positions, 1) if position not in reference), None)


history = []
seen = set()
results = []
sensitivity = []

for event_id, event_games in itertools.groupby(games, key=lambda game: game[0]['event_id']):
    event_reference = seen.copy()
    for _, round_games in itertools.groupby(event_games, key=lambda game: int(game[0]['round'].split('.')[0])):
        round_games = list(round_games)
        references = []
        if len(history) >= REFERENCE_GAMES:
            for seed in range(REPEATS):
                sample = random.Random(seed).sample(history, REFERENCE_GAMES)
                references.append(set().union(*sample))
        for game, positions in round_games:
            novelty = first_novelty(positions, seen)
            event_novelty = first_novelty(positions, event_reference)
            first_return = next((
                ply for ply, position in enumerate(positions, 1)
                if novelty is not None and ply > novelty and position in seen
            ), '')
            row = {
                'game_id': game['game_id'],
                'event_id': event_id,
                'round': game['round'],
                'year': events[event_id]['year'],
                'date': game['date'],
                'white': game['white'],
                'black': game['black'],
                'plies': len(positions),
                'reference_games': len(history),
                'first_novelty_ply': novelty if novelty is not None else '',
                'censored': int(novelty is None),
                'first_return_ply': first_return,
                'earlier_event_novelty_ply': event_novelty if event_novelty is not None else '',
            }
            results.append(row)
            for seed, reference in enumerate(references):
                sampled_novelty = first_novelty(positions, reference)
                sensitivity.append({
                    'game_id': game['game_id'],
                    'event_id': event_id,
                    'year': events[event_id]['year'],
                    'plies': len(positions),
                    'reference_games': REFERENCE_GAMES,
                    'first_novelty_ply': sampled_novelty if sampled_novelty is not None else '',
                    'censored': int(sampled_novelty is None),
                    'seed': seed,
                })
        # same-round games have no ordering, so add them together
        for _, positions in round_games:
            history.append(set(positions))
            seen.update(positions)


#%% write
for name, rows in [('novelty.csv', results), ('novelty_sensitivity.csv', sensitivity)]:
    with (DATA / name).open('w', newline='') as destination:
        writer = csv.DictWriter(destination, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
print(f'{len(results)} main-line classical games; {len(sensitivity)} fixed-archive comparisons')
