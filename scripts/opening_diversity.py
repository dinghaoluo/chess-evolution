'''
Created on 15 October 2026

compare opening positions after holding the number of championship games fixed

@author: Dinghao Luo
'''

#%% imports
import csv
from collections import Counter, defaultdict
from math import comb
from pathlib import Path

import numpy as np

from novelty_trend_tests import calendar_trend


#%% main
def main() -> None:
    data = Path('data')
    with (data / 'novelty.csv').open() as source:
        accepted = {row['game_id']: row for row in csv.DictReader(source)}
    positions = defaultdict(list)
    with (data / 'games.csv').open() as source:
        for row in csv.DictReader(source):
            if row['game_id'] in accepted and int(row['ply']) in [8, 12, 16, 20, 24]:
                year = int(accepted[row['game_id']]['year'])
                positions[year, int(row['ply'])].append(' '.join(row['fen'].split()[:4]))
    rows = []
    for (year, ply), fens in sorted(positions.items()):
        total = len(fens)
        counts = Counter(fens)
        # exact expected distinct positions in eight games, without replacement
        expected = sum(1 - (comb(total - count, 8) / comb(total, 8) if total - count >= 8 else 0)
                       for count in counts.values())
        rows.append({'year': year, 'ply': ply, 'sample_games': 8, 'eligible_games': total,
                     'games_ending_before_ply': sum(int(row['year']) == year for row in accepted.values()) - total,
                     'distinct_positions_in_archive': len(counts), 'expected_positions_in_eight_games': expected})
    with (data / 'opening_diversity.csv').open('w', newline='') as destination:
        writer = csv.DictWriter(destination, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
    trends = []
    for ply in [8, 12, 16, 20, 24]:
        for population in ['all_years', 'single_match_years']:
            for since in [1886, 1970]:
                # two round robins and the year with two title matches have different opponent mixtures
                sample = [row for row in rows if row['ply'] == ply and row['year'] >= since
                          and (population == 'all_years' or row['year'] not in [1910, 1948, 2007])]
                fit = calendar_trend(np.array([row['year'] for row in sample]),
                                     np.array([row['expected_positions_in_eight_games'] for row in sample]), 10)
                fit['slope_positions_per_century'] = fit.pop('slope_plies_per_century')
                trends.append({'ply': ply, 'population': population, **fit})
    with (data / 'opening_diversity_trends.csv').open('w', newline='') as destination:
        writer = csv.DictWriter(destination, fieldnames=list(trends[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(trends)
    print(len(rows), 'year/ply comparisons;', len(trends), 'exploratory trends')


if __name__ == '__main__':
    main()
