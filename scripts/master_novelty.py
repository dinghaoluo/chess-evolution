'''
Created on 15 October 2026

measure championship departures from dated historical games

@author: Dinghao Luo
'''

#%% imports
import csv
import itertools
from collections import defaultdict
from pathlib import Path
from statistics import median

import numpy as np
import chess
from statsmodels.regression.linear_model import OLS


#%% inputs
DATA = Path('data')
CACHE = Path('.venv/master-reference')
with (DATA / 'master_positions.csv').open() as source:
    definitions = list(csv.DictReader(source))
position_ids = {' '.join(row['fen'].split()[:4]): int(row['position_id']) for row in definitions if row['fen']}
edge_ids = {(' '.join(row['previous_fen'].split()[:4]), row['move_uci']): int(row['position_id'])
            for row in definitions if row['previous_fen']}
with (DATA / 'novelty.csv').open() as source:
    targets = {row['game_id']: row for row in csv.DictReader(source)}
with (DATA / 'events.csv').open() as source:
    events = {row['event_id']: row for row in csv.DictReader(source)}
with (DATA / 'game_date_audit.csv').open() as source:
    dates = {row['game_id']: row for row in csv.DictReader(source)}
positions = {}
edges = {}
with (DATA / 'games.csv').open() as source:
    for game_id, records in itertools.groupby(csv.DictReader(source), key=lambda row: row['game_id']):
        if game_id not in targets:
            continue
        records = list(records)
        fens = [' '.join(row['fen'].split()[:4]) for row in records]
        positions[game_id] = [position_ids[fen] for fen in fens]
        previous = [' '.join(chess.STARTING_FEN.split()[:4])] + fens[:-1]
        edges[game_id] = [edge_ids[fen, row['move_uci']] for fen, row in zip(previous, records)]

history = defaultdict(list)
coverage = []
with (DATA / 'master_database_sources.csv').open() as source:
    sources = list(csv.DictReader(source))
for batch in sources:
    with (CACHE / (batch['batch'] + '.positions.csv')).open() as source:
        for row in csv.DictReader(source):
            history[int(row['position_id'])].append({'batch': batch['batch'], **row})
    with (CACHE / (batch['batch'] + '.years.csv')).open() as source:
        coverage.extend({'batch': batch['batch'], **row} for row in csv.DictReader(source))


#%% chronological references
earliest = {p: min(int(row['earliest_date_end']) for row in rows) for p, rows in history.items()}
rated_earliest = {p: min(int(row['both_2200_date_end']) for row in rows if row['both_2200_date_end'])
                  for p, rows in history.items() if any(row['both_2200_date_end'] for row in rows)}
ordered = sorted(targets, key=lambda g: (int(events[targets[g]['event_id']]['order']),
                                       int(targets[g]['round'].split('.')[0])))
results = []
previous_rounds = set()
previous_games = []
for event_id, event_games in itertools.groupby(ordered, key=lambda g: targets[g]['event_id']):
    for _, round_games in itertools.groupby(event_games, key=lambda g: int(targets[g]['round'].split('.')[0])):
        round_games = list(round_games)
        for game_id in round_games:
            game = targets[game_id]
            # reference dates must end before this game's date interval starts
            start = int(dates[game_id]['date_lower_bound'])
            year_start = start // 10000 * 10000 + 101
            known = {p for p in positions[game_id] if earliest.get(p, 99999999) < start} | previous_rounds
            year_known = {p for p in positions[game_id] if earliest.get(p, 99999999) < year_start} | previous_rounds
            recent_known = {p for p in positions[game_id] if any(
                start // 10000 - 20 <= int(row['year']) and int(row['earliest_date_end']) < start
                for row in history.get(p, []))}
            for earlier in previous_games:
                if int(dates[earlier]['date_lower_bound']) // 10000 >= start // 10000 - 20:
                    recent_known.update(positions[earlier])
            rated_known = {p for p in positions[game_id] if rated_earliest.get(p, 99999999) < start} | previous_rounds
            output = {'game_id': game_id, 'event_id': event_id, 'year': game['year'], 'date': dates[game_id]['analysis_date'],
                      'source_date': game['date'],
                      'date_cutoff': start, 'round': game['round'], 'white': game['white'], 'black': game['black'],
                      'plies': len(positions[game_id])}
            for name, reference in [('dated', known), ('prior_year', year_known),
                                    ('prior_20_years', recent_known), ('both_2200', rated_known)]:
                first = next((ply for ply, p in enumerate(positions[game_id], 1) if p not in reference), None)
                returns = [ply for ply, p in enumerate(positions[game_id], 1)
                           if first is not None and ply > first and p in reference]
                output[name + '_first_new_ply'] = first if first else ''
                output[name + '_first_return_ply'] = returns[0] if returns else ''
                # endgame transpositions should not count as returns to opening precedent
                known_opening = [ply for ply, p in enumerate(positions[game_id][:40], 1) if p in reference]
                last_known = max(known_opening, default=0)
                output[name + '_sustained_ply40'] = last_known + 1 if last_known < min(40, len(positions[game_id])) else ''
            for name, cutoff, index in [('dated_move', start, earliest), ('prior_year_move', year_start, earliest),
                                        ('both_2200_move', start, rated_earliest)]:
                reference = {p for p in edges[game_id] if index.get(p, 99999999) < cutoff} | previous_rounds
                first = next((ply for ply, p in enumerate(edges[game_id], 1) if p not in reference), None)
                output[name + '_first_new_ply'] = first if first else ''
            output['external_reference_games_prior_year'] = sum(int(row['games']) for row in coverage if int(row['year']) < year_start // 10000)
            results.append(output)
        for game_id in round_games:
            previous_rounds.update(positions[game_id])
            previous_rounds.update(edges[game_id])
            previous_games.append(game_id)


#%% annual medians and censoring bounds
summaries = []
for year in sorted({row['year'] for row in results}, key=int):
    games = [row for row in results if row['year'] == year]
    row = {'year': year, 'games': len(games)}
    for field in [key for key in results[0] if key.endswith('_first_new_ply') or key.endswith('_sustained_ply40')]:
        # a game with no departure still gives a lower bound
        limit = lambda game: min(40, game['plies']) if 'sustained' in field else game['plies']
        lower = median(game[field] if game[field] else limit(game) + 1 for game in games)
        upper = median(game[field] if game[field] else np.inf for game in games)
        row[field + '_median'] = lower if lower == upper else ''
        row[field + '_median_lower'] = lower
        row[field + '_median_upper'] = upper
        row[field + '_censored'] = sum(not game[field] for game in games)
    field = 'prior_year_first_new_ply'
    for label, quantile in [('q25', 0.25), ('q75', 0.75)]:
        lower = np.quantile([game[field] if game[field] else game['plies'] + 1 for game in games], quantile)
        upper = np.quantile([game[field] if game[field] else np.inf for game in games], quantile)
        row[field + '_' + label] = lower if lower == upper else ''
    summaries.append(row)

trends = []
for field in [key for key in summaries[0] if key.endswith('_median_lower') or key.endswith('_median_upper')]:
    for since in [1886, 1970]:
        rows = [row for row in summaries if int(row['year']) >= since and np.isfinite(row[field])]
        years = np.array([int(row['year']) for row in rows])
        design = np.column_stack((np.ones(len(rows)), (years - years.mean()) / 100))
        for lag in [0, 1, 3, 5]:
            fit = OLS([row[field] for row in rows], design).fit(cov_type='HAC',
                      cov_kwds={'maxlags': lag, 'use_correction': True}, use_t=True)
            low, high = fit.conf_int()[1]
            trends.append({'measure': field, 'start_year': int(years.min()), 'end_year': int(years.max()),
                           'years': len(rows), 'slope_plies_per_century': fit.params[1], 'hac_lag': lag,
                           'ci95_low': low, 'ci95_high': high, 'hac_p': fit.pvalues[1]})


#%% witnesses and outputs
witnesses = []
for p in sorted(history):
    first = min(history[p], key=lambda row: int(row['earliest_date_end']))
    witnesses.append({**first, 'both_2200_first_seen': rated_earliest.get(p, '')})
for name, rows in [('master_novelty', results), ('master_novelty_years', summaries),
                   ('master_novelty_trends', trends), ('master_position_first_seen', witnesses),
                   ('master_database_coverage', coverage)]:
    with (DATA / (name + '.csv')).open('w', newline='') as destination:
        writer = csv.DictWriter(destination, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
print(len(results), 'championship games;', len(witnesses), 'position witnesses')
