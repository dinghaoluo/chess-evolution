'''
Created on 15 October 2026

compare search budgets and game-history inputs in the Stockfish pilot

@author: Dinghao Luo
'''

#%% imports
import csv
from pathlib import Path

import numpy as np


#%% paired searches
DATA = Path('data')
with (DATA / 'stockfish_pilot.csv').open() as source:
    results = list(csv.DictReader(source))
lookup = {(row['position_id'], row['history_mode'], int(row['node_budget'])): row for row in results}
comparisons = [
    ('250k_to_1m', 'full', 250_000, 'full', 1_000_000),
    ('1m_to_4m', 'full', 1_000_000, 'full', 4_000_000),
    ('history_at_250k', 'fen_only', 250_000, 'full', 250_000),
]
summaries = []
pairs = []
for label, mode_a, budget_a, mode_b, budget_b in comparisons:
    # the fen-only diagnostic and 4m run cover subsets of the pilot
    selection = (mode_a, budget_a) if mode_a == 'fen_only' else (mode_b, budget_b)
    for result in results:
        if (result['history_mode'], int(result['node_budget'])) != selection:
            continue
        other = lookup[result['position_id'], mode_a, budget_a]
        row = lookup[result['position_id'], mode_b, budget_b]
        cp = (float(row['best_cp']) - float(other['best_cp'])
              if row['best_cp'] and other['best_cp'] else None)
        pairs.append({
            'comparison': label, 'collection': row['collection'], 'position_id': row['position_id'],
            'move_a': other['best_move'], 'move_b': row['best_move'],
            'move_changed': int(other['best_move'] != row['best_move']),
            'cp_change': cp, 'mate_a': other['best_mate'], 'mate_b': row['best_mate'],
            'expected_score_change': float(row['best_expected_score']) - float(other['best_expected_score']),
            'played_difference_a': other['cp_difference'], 'played_difference_b': row['cp_difference'],
        })
    for collection in ['championship', 'pal_css_2005']:
        selected = [row for row in pairs if row['comparison'] == label and row['collection'] == collection]
        cp = np.array([abs(row['cp_change']) for row in selected if row['cp_change'] is not None])
        expected = np.array([abs(row['expected_score_change']) for row in selected])
        summaries.append({
            'comparison': label, 'collection': collection, 'positions': len(selected),
            'preferred_move_changes': sum(row['move_changed'] for row in selected),
            'cp_pairs': len(cp), 'median_absolute_cp_change': np.median(cp),
            'p95_absolute_cp_change': np.percentile(cp, 95), 'max_absolute_cp_change': np.max(cp),
            'cp_changes_over_20': int(np.sum(cp > 20)), 'cp_changes_over_50': int(np.sum(cp > 50)),
            'median_absolute_expected_score_change': np.median(expected),
            'p95_absolute_expected_score_change': np.percentile(expected, 95),
        })


#%% evaluation differences and unstable positions
for nodes in [250_000, 1_000_000, 4_000_000]:
    rows = [row for row in results if row['history_mode'] == 'full' and int(row['node_budget']) == nodes]
    negative = sum(row['cp_difference'] != '' and float(row['cp_difference']) < 0 for row in rows)
    print(nodes, len(rows), 'positions;', negative, 'negative cp differences')
for name, rows in [('stockfish_stability', summaries), ('stockfish_stability_positions', pairs)]:
    with (DATA / (name + '.csv')).open('w', newline='') as destination:
        writer = csv.DictWriter(destination, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
for row in summaries:
    changes, count = row['preferred_move_changes'], row['positions']
    median_cp, p95_cp = row['median_absolute_cp_change'], row['p95_absolute_cp_change']
    print(row['comparison'], row['collection'], f'{changes}/{count} move changes;',
          f'median {median_cp:g} cp, p95 {p95_cp:g} cp')
