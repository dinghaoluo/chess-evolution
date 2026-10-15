'''
Created on 15 October 2026

hold the number of earlier reference games fixed across championship years

@author: Dinghao Luo
'''

#%% imports
import csv
import heapq
import itertools
import random
from collections import defaultdict
from pathlib import Path
from statistics import median

import numpy as np
from statsmodels.regression.linear_model import OLS


#%% inputs
DATA = Path('data')
CACHE = Path('.venv/master-reference')
# equal chance per game, regardless of its length
REFERENCE_GAMES = 1000
SAMPLES = 10
POOL_SIZE = REFERENCE_GAMES * SAMPLES
with (DATA / 'master_novelty.csv').open() as source:
    targets = list(csv.DictReader(source))
with (DATA / 'master_database_sources.csv').open() as source:
    batches = list(csv.DictReader(source))
assert all(int(row['sample_pool_per_year']) >= POOL_SIZE for row in batches)
with (DATA / 'master_positions.csv').open() as source:
    position_ids = {' '.join(row['fen'].split()[:4]): int(row['position_id'])
                    for row in csv.DictReader(source) if row['fen']}
positions = defaultdict(list)
selected = {row['game_id'] for row in targets}
with (DATA / 'games.csv').open() as source:
    for row in csv.DictReader(source):
        if row['game_id'] in selected:
            positions[row['game_id']].append(position_ids[' '.join(row['fen'].split()[:4])])


def sample_records(path: Path):
    with path.open() as source:
        for row in csv.DictReader(source):
            yield int(row['year']), int(row['priority']), path.stem, row['source_ordinal'], row['position_ids']


records = heapq.merge(*(sample_records(CACHE / (row['batch'] + '.samples.csv')) for row in batches))
pending = next(records, None)
pool = []
previous_games = []
# title copies were excluded; the audited games enter after their round
random_championship = random.Random(20261015)
results = []
last_year = 0


#%% uniform samples from each earlier-year union
for event_id, event_games in itertools.groupby(targets, key=lambda row: row['event_id']):
    for _, round_games in itertools.groupby(event_games, key=lambda row: int(row['round'].split('.')[0])):
        round_games = list(round_games)
        cutoff = min(int(row['date_cutoff']) // 10000 for row in round_games)
        assert cutoff >= last_year
        last_year = cutoff
        while pending is not None and pending[0] < cutoff:
            year, priority, batch, ordinal, ids = pending
            candidate = (-priority, batch, ordinal, ids)
            if len(pool) < POOL_SIZE:
                heapq.heappush(pool, candidate)
            elif priority < -pool[0][0]:
                heapq.heapreplace(pool, candidate)
            pending = next(records, None)
        # keep the same random ordering across years
        eligible = [(-priority, batch, ordinal, ids) for priority, batch, ordinal, ids in pool]
        eligible.extend(previous_games)
        sampled = heapq.nsmallest(POOL_SIZE, eligible)
        assert len(sampled) == POOL_SIZE
        for sample in range(SAMPLES):
            games = sampled[sample * REFERENCE_GAMES:(sample + 1) * REFERENCE_GAMES]
            known = {int(p) for _, _, _, ids in games for p in ids.split()}
            for game in round_games:
                states = positions[game['game_id']]
                first = next((ply for ply, state in enumerate(states, 1) if state not in known), None)
                results.append({'game_id': game['game_id'], 'year': game['year'], 'sample': sample,
                                'reference_games': REFERENCE_GAMES, 'plies': len(states),
                                'first_new_ply': first if first is not None else '',
                                'censored': int(first is None)})
        for game in round_games:
            previous_games.append((random_championship.getrandbits(64), 'championship', game['game_id'],
                                   ' '.join(str(p) for p in positions[game['game_id']])))


#%% annual medians and archive-sampling variation
summaries = []
annual = {}
for year in sorted({row['year'] for row in results}, key=int):
    values = []
    for sample in range(SAMPLES):
        games = [row for row in results if row['year'] == year and row['sample'] == sample]
        low = median(row['first_new_ply'] if row['first_new_ply'] else row['plies'] + 1 for row in games)
        high = median(row['first_new_ply'] if row['first_new_ply'] else np.inf for row in games)
        assert low == high, (year, sample)
        values.append(low)
        annual[year, sample] = low
    summaries.append({'year': year, 'reference_games': REFERENCE_GAMES, 'samples': SAMPLES,
                      'median_of_sample_medians': median(values),
                      'sample_median_p10': np.percentile(values, 10),
                      'sample_median_p90': np.percentile(values, 90)})

trends = []
for since in [1886, 1970]:
    years = sorted([int(row['year']) for row in summaries if int(row['year']) >= since])
    design = np.column_stack((np.ones(len(years)), (np.array(years) - np.mean(years)) / 100))
    for sample in ['median'] + list(range(SAMPLES)):
        values = ([next(row['median_of_sample_medians'] for row in summaries if int(row['year']) == year)
                   for year in years] if sample == 'median' else [annual[str(year), sample] for year in years])
        fit = OLS(values, design).fit(cov_type='HAC', cov_kwds={'maxlags': 3, 'use_correction': True}, use_t=True)
        low, high = fit.conf_int()[1]
        trends.append({'sample': sample, 'reference_games': REFERENCE_GAMES, 'start_year': min(years),
                       'end_year': max(years), 'years': len(years), 'hac_lag': 3,
                       'slope_plies_per_century': fit.params[1], 'ci95_low': low, 'ci95_high': high,
                       'hac_p': fit.pvalues[1]})


#%% outputs
for name, rows in [('master_novelty_sampled', results), ('master_novelty_sampling_years', summaries),
                   ('master_novelty_sampling_trends', trends)]:
    with (DATA / (name + '.csv')).open('w', newline='') as destination:
        writer = csv.DictWriter(destination, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
