'''
Created on 15 October 2026

summarise time allocation and check preparation accounts against the clocks

@author: Dinghao Luo
'''

#%% imports
import csv
from pathlib import Path
from statistics import median

import numpy as np


#%% main
def main() -> None:
    data = Path('data/derived')
    with (data / 'pal_css_timing.csv').open() as source:
        pal = list(csv.DictReader(source))
    with (data / 'pal_css_clock_games.csv').open() as source:
        games = {row['game_id']: row for row in csv.DictReader(source)}
    summaries = []
    for edition, stage in sorted({(int(row['edition']), row['stage']) for row in pal}):
        rows = [row for row in pal if int(row['edition']) == edition and row['stage'] == stage]
        included_games = {row['game_id'] for row in rows}
        for label, threshold in [('2p5', 2.5), ('5', 5), ('10', 10)]:
            usable = [row for row in rows if row[f'first_{label}pct_missing_before'] == '0']
            lower = [int(row[f'first_{label}pct_move']) if row[f'first_{label}pct_move']
                     else int(row['observed_moves']) + 1 for row in usable]
            upper = [int(row[f'first_{label}pct_move']) if row[f'first_{label}pct_move']
                     else np.inf for row in usable]
            # an early draw bounds the first long think; do not discard it or put it at move 31
            summaries.append({'edition': edition, 'stage': stage, 'date': min(row['date'] for row in rows),
                              'format': rows[0]['format'], 'games': len(included_games),
                              'initial_seconds': rows[0]['initial_seconds'], 'threshold_percent': threshold,
                              'sides': len(rows), 'usable_sides': len(usable),
                              'censored_sides': sum(not row[f'first_{label}pct_move'] for row in usable),
                              'median_first_think_lower': median(lower), 'median_first_think_upper': median(upper),
                              'draws': sum(games[game_id]['result'] == '1/2-1/2' for game_id in included_games)})
    with (data / 'pal_css_timing_summary.csv').open('w', newline='') as destination:
        writer = csv.DictWriter(destination, fieldnames=list(summaries[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(summaries)

    #%% independent accounts
    with (data / 'championship_clocks.csv').open() as source:
        title_clocks = {(row['game_id'], int(row['ply'])): row for row in csv.DictReader(source)}
    with (data / 'pal_css_move_times.csv').open() as source:
        pal_clocks = {(row['game_id'], int(row['ply'])): row for row in csv.DictReader(source)}
    with (Path('data/curated') / 'preparation_accounts.csv').open() as source:
        accounts = list(csv.DictReader(source))
    checks = []
    for account in accounts:
        game_id, ply = account['game_id'], int(account['ply'])
        lookup = pal_clocks if account['population'] == 'pal' else title_clocks
        clock = lookup[game_id, ply]
        assert clock['move_san'] == account['move_san'], account['case_id']
        assert ply % 2 == (account['side'] == 'white')
        own = [row for (g, p), row in lookup.items() if g == game_id and p % 2 == ply % 2]
        own.sort(key=lambda row: int(row['ply']))
        threshold = float(games[game_id]['initial_seconds']) * 0.05 if account['population'] == 'pal' else 300
        first = next((int(row['ply']) for row in own if row['elapsed_seconds']
                      and float(row['elapsed_seconds']) >= threshold), None)
        checks.append({'case_id': account['case_id'], 'game_id': game_id,
                       'claim_type': account['claim_type'], 'account_ply': ply,
                       'account_move_seconds': clock['elapsed_seconds'], 'threshold_seconds': threshold,
                       'first_qualifying_think_ply': first or '',
                       'claim': account['account'], 'source_url': account['source_url']})
    with (data / 'preparation_clock_checks.csv').open('w', newline='') as destination:
        writer = csv.DictWriter(destination, fieldnames=list(checks[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(checks)
    print(len(summaries), 'PAL/CSS summaries;', len(checks), 'preparation checks')


if __name__ == '__main__':
    main()
