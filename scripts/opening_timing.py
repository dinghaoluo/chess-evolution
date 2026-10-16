'''
Created on 15 October 2026

compare recorded opening departures with time spent at the board

@author: Dinghao Luo
'''

#%% imports
import csv
import json
from pathlib import Path

import numpy as np


#%% main
def main() -> None:
    data = Path('data')
    with (data / 'championship_clocks.csv').open() as source:
        clocks = list(csv.DictReader(source))
    with (data / 'master_novelty.csv').open() as source:
        precedent = {row['game_id']: row for row in csv.DictReader(source)}
    games = {}
    for row in clocks:
        row['ply'] = int(row['ply'])
        row['elapsed_seconds'] = float(row['elapsed_seconds']) if row['elapsed_seconds'] else np.nan
        row['clock_seconds'] = float(row['clock_seconds']) if row['clock_seconds'] else np.nan
        games.setdefault(row['game_id'], {})[row['ply']] = row
    players = []
    departures = []
    for game_id, moves in games.items():
        reference = precedent[game_id]
        first = int(reference['prior_year_first_new_ply'])
        for side in [1, 0]:
            own = [row for ply, row in moves.items() if ply % 2 == side and ply <= 60]
            row = {'game_id': game_id, 'year': reference['year'], 'round': reference['round'],
                   'side': 'white' if side else 'black',
                   'player': reference['white' if side else 'black'],
                   'first_unrecorded_ply': first}
            for minutes in [2, 5, 10]:
                slow = next((move['ply'] for move in own if move['elapsed_seconds'] >= minutes * 60), None)
                row[f'first_{minutes}min_ply'] = slow or ''
                # no qualifying think before move 30 is right-censored, not move 31
                row[f'first_{minutes}min_censored'] = int(slow is None)
                row[f'first_{minutes}min_missing_before'] = sum(not np.isfinite(move['elapsed_seconds'])
                                                              for move in own if slow is None or move['ply'] < slow)
                row[f'first_{minutes}min_before_departure'] = int(slow < first) if slow else ''
                sustained = next((own[i]['ply'] for i in range(len(own) - 2)
                                  if np.isfinite([move['elapsed_seconds'] for move in own[i:i + 3]]).all()
                                  and sum(move['elapsed_seconds'] >= minutes * 60 for move in own[i:i + 3]) >= 2), None)
                row[f'sustained_{minutes}min_ply'] = sustained or ''
            for end in [10, 20, 30]:
                endpoint = end * 2 - side
                # a recorded endpoint still gives the cumulative time after an earlier gap
                row[f'elapsed_first_{end}_seconds'] = 7200 - moves[endpoint]['clock_seconds'] if endpoint in moves else np.nan
            players.append(row)
        for baseline in ['prior_year', 'dated', 'both_2200', 'prior_year_move']:
            ply = int(reference[baseline + '_first_new_ply'])
            if ply + 5 > 60 or ply - 6 < 1:
                continue
            row = {'game_id': game_id, 'year': reference['year'], 'round': reference['round'],
                   'baseline': baseline, 'departure_ply': ply,
                   'introducer': reference['white' if ply % 2 else 'black']}
            for role, offset in [('introducer', 0), ('responder', 1)]:
                row[role + '_seconds'] = moves[ply + offset]['elapsed_seconds']
                row[role + '_legal_moves'] = moves[ply + offset]['legal_moves_before']
                for label, offsets in [('before', [-6, -4, -2]), ('after', [0, 2, 4])]:
                    window = [moves[ply + offset + step]['elapsed_seconds'] for step in offsets]
                    row[f'{role}_{label}_seconds'] = np.mean(window)
            row['introducer_clock_advantage_seconds'] = moves[ply]['clock_seconds'] - moves[ply + 1]['clock_seconds']
            departures.append(row)
    for name, rows in [('opening_thinks.csv', players), ('opening_departure_times.csv', departures)]:
        with (data / name).open('w', newline='') as destination:
            writer = csv.DictWriter(destination, fieldnames=list(rows[0]), lineterminator='\n')
            writer.writeheader()
            writer.writerows(rows)

    #%% uncertainty within these matches
    rng = np.random.default_rng(20261015)
    comparisons = []
    for baseline in ['prior_year', 'dated', 'both_2200', 'prior_year_move']:
        rows = [row for row in departures if row['baseline'] == baseline]
        for name, left, right in [
                ('reply_minus_departure', 'responder_seconds', 'introducer_seconds'),
                ('responder_after_minus_before', 'responder_after_seconds', 'responder_before_seconds'),
                ('introducer_after_minus_before', 'introducer_after_seconds', 'introducer_before_seconds')]:
            valid = [row for row in rows if np.isfinite(row[left]) and np.isfinite(row[right])]
            changes = np.array([row[left] - row[right] for row in valid])
            # resample whole games within each match; moves are not independent samples
            groups = [np.array([row[left] - row[right] for row in valid if row['year'] == year])
                      for year in ['2021', '2023', '2024']]
            draws = np.concatenate([rng.choice(group, (10000, len(group))) for group in groups], axis=1)
            interval = np.quantile(np.median(draws, axis=1), [0.025, 0.975])
            comparisons.append({'baseline': baseline, 'comparison': name, 'games': len(valid),
                                'median_difference_seconds': np.median(changes),
                                'lower_seconds': interval[0], 'upper_seconds': interval[1],
                                'positive_games': int(sum(changes > 0)), 'negative_games': int(sum(changes < 0)),
                                'tied_games': int(sum(changes == 0))})
    with (data / 'opening_timing_comparisons.csv').open('w', newline='') as destination:
        writer = csv.DictWriter(destination, fieldnames=list(comparisons[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(comparisons)

    # an ordinary opening also gets slower; compare the actual departure to other games' departure plies
    rows = [row for row in departures if row['baseline'] == 'prior_year'
            and all(np.isfinite(games[row['game_id']][ply]['elapsed_seconds']) for ply in range(1, 39))]
    strata = [[i for i, row in enumerate(rows) if row['year'] == year and row['departure_ply'] % 2 == side]
              for year in ['2021', '2023', '2024'] for side in [0, 1]]
    plies = np.array([row['departure_ply'] for row in rows])
    changes = np.array([[
        np.mean([moves[ply + offset]['elapsed_seconds'] for offset in range(6)])
        - np.mean([moves[ply + offset]['elapsed_seconds'] for offset in range(-6, 0)])
        for ply in plies] for moves in [games[row['game_id']] for row in rows]])
    actual = np.median(changes[np.arange(len(rows)), np.arange(len(rows))])
    shuffled = []
    for _ in range(10000):
        assignment = np.arange(len(rows))
        for indices in strata:
            assignment[indices] = rng.permutation(indices)
        shuffled.append(np.median(changes[np.arange(len(rows)), assignment]))
    placebo = {'games': len(rows), 'actual_median_increase_seconds': float(actual),
               'shuffled_median_increase_seconds': float(np.median(shuffled)),
               'shuffled_95_percent_interval_seconds': np.quantile(shuffled, [0.025, 0.975]).tolist(),
               'one_sided_permutation_p': (1 + sum(value >= actual for value in shuffled)) / 10001,
               'comparison': 'departure plies shuffled between games of the same match and introducer colour; both players combined',
               'limit': 'association conditional on exchangeability within strata, not a randomised intervention'}
    (data / 'opening_timing_placebo.json').write_text(json.dumps(placebo, indent=2) + '\n')
    methods = {
        'opening_limit': 'first 30 moves per player, before increment or an extra time period in every included match',
        'long_think': 'first move taking at least five minutes; two and ten minutes are sensitivity checks',
        'sustained_thinking': 'first three-move window with two qualifying thinks; a retrospective description',
        'preparation': 'timing thresholds have no preparation label; independent player statements are checked separately',
        'departure': 'first position absent from earlier years, matching the historical plot; exact-date and other baselines retained',
        'windows': 'three moves by the same player before departure and three from departure onward',
        'uncertainty': '10000 percentile bootstrap samples of complete games, stratified by match; conditional on these players and matches',
        'time_series': 'three matches cannot identify a general trend or an engine effect',
        'opponent_comparison': 'paired descriptions; choices of opening, player, and position difficulty are not randomised',
        'missing_early_times': 'first observed long thinks flagged if an earlier move time is missing; cumulative time uses the recorded endpoint clock',
        'placebo': '10000 shuffles of departure plies within match and introducer colour; one game with early missing times excluded',
    }
    (data / 'opening_timing_methods.json').write_text(json.dumps(methods, indent=2) + '\n')
    print(len(players), 'game sides;', len(departures), 'departure comparisons')


if __name__ == '__main__':
    main()
