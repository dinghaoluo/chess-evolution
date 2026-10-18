'''
Created on 16 October 2026

summarise judged advice gaps and the presampled budget check

@author: Dinghao Luo
'''

#%% imports
import csv
import hashlib
import json
from pathlib import Path

import numpy as np


#%% main
def main() -> None:
    inputs = [Path('data/derived/' + name) for name in ['advice_config.json', 'advice_preferences.csv', 'advice_judgements.csv']]
    inputs.append(Path(__file__))
    config = json.loads(inputs[0].read_text())
    for name, fingerprint in config['outputs_sha256'].items():
        assert hashlib.sha256(Path(name).read_bytes()).hexdigest() == fingerprint
    preferences = list(csv.DictReader(inputs[1].read_text().splitlines()))
    judgements = list(csv.DictReader(inputs[2].read_text().splitlines()))
    moves = {(row['game_id'], row['engine'], row['nodes']): row['move_uci'] for row in preferences}
    scores = {(row['game_id'], row['engine'], row['nodes']): row for row in judgements}
    rng, rows = np.random.default_rng(20261016), []
    for name in config['protocol']['engines']:
        base = [row for row in judgements if row['engine'] == name and row['nodes'] == '100000']
        stable = [row for row in judgements if row['engine'] == name and row['nodes'] == '400000']
        loss = np.array([float(row['nonnegative_loss']) for row in base])
        low, high = np.quantile([rng.choice(loss, len(loss)).mean() for _ in range(2000)], [.025, .975])
        changes = np.array([abs(float(row['nonnegative_loss']) - float(scores[row['game_id'], name, '100000']['nonnegative_loss'])) for row in stable])
        row = {'engine': name, 'positions': len(base), 'mean_nonnegative_loss': float(loss.mean()),
               'bootstrap_low': float(low), 'bootstrap_high': float(high),
               'above_0_02': sum(row['above_0_02'] == 'True' for row in base),
               'above_0_05': sum(row['above_0_05'] == 'True' for row in base),
               'judge_reversals': sum(row['judge_reversal'] == 'True' for row in base),
               'stability_positions': len(stable),
               'stable_recommendations': sum(moves[row['game_id'], name, '100000'] == moves[row['game_id'], name, '400000'] for row in stable),
               'stability_loss_change_above_0_02': int(sum(changes > .02)),
               'stability_loss_change_p95': float(np.quantile(changes, .95))}
        rows.append(row)
    output = Path('data/derived/advice_summary.csv')
    with output.open('w', newline='') as destination:
        writer = csv.DictWriter(destination, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
    saved = {'inputs_sha256': {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in inputs},
             'outputs_sha256': {str(output): hashlib.sha256(output.read_bytes()).hexdigest()},
             'bootstrap': '2000 sampled-game/position resamples, seed 20261016; one position per game',
             'limits': config['limits'] + ['Loss is relative to the modern screening recommendation under its shared-root rescore; negative signed differences remain in the raw table.']}
    Path('data/derived/advice_summary_config.json').write_text(json.dumps(saved, indent=2) + '\n')


if __name__ == '__main__':
    main()
