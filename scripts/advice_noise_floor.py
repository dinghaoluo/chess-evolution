'''
Created on 16 October 2026

compare release disagreement with budget sensitivity on matched positions

@author: Dinghao Luo
'''

#%% imports
import csv
import hashlib
import itertools
import json
from pathlib import Path

import numpy as np

from build_panels import write_panel


#%% matched comparisons
def main() -> None:
    source = Path('data/derived/advice_preferences.csv')
    rows = list(csv.DictReader(source.read_text().splitlines()))
    engines = list(dict.fromkeys(row['engine'] for row in rows))
    moves = {(row['game_id'], row['engine'], int(row['nodes'])): row['move_uci'] for row in rows}
    identities = sorted({row['game_id'] for row in rows if row['nodes'] == '400000'})
    assert len(identities) == 50
    rng = np.random.default_rng(20261016)
    resamples = rng.integers(0, len(identities), size=(2000, len(identities)))
    output_rows = []
    for first, second in itertools.combinations(engines, 2):
        first_noise = np.array([moves[game, first, 100000] != moves[game, first, 400000] for game in identities])
        second_noise = np.array([moves[game, second, 100000] != moves[game, second, 400000] for game in identities])
        noise = (first_noise.astype(float) + second_noise.astype(float)) / 2
        row = {'first': first, 'second': second, 'positions': len(identities),
               'within_first_agreement': float(1 - first_noise.mean()),
               'within_second_agreement': float(1 - second_noise.mean()),
               'mean_budget_disagreement': float(noise.mean())}
        for budget in [100000, 400000]:
            disagreement = np.array([moves[game, first, budget] != moves[game, second, budget] for game in identities])
            excess = disagreement - noise
            low, high = np.quantile(excess[resamples].mean(axis=1), [.025, .975])
            row.update({f'between_agreement_{budget}': float(1 - disagreement.mean()),
                        f'excess_disagreement_{budget}': float(excess.mean()),
                        f'excess_low_{budget}': float(low), f'excess_high_{budget}': float(high)})
        output_rows.append(row)
    output = Path('data/derived/advice_noise_floor.csv')
    with output.open('w', newline='') as destination:
        writer = csv.DictWriter(destination, fieldnames=list(output_rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(output_rows)
    limits = ['All comparisons use the same 50 presampled positions, one per game; the 500-position agreement estimate is separate.',
              'The descriptive noise floor is the mean of the two releases\' budget-disagreement rates, not an identified measurement-error model.',
              'Excess disagreement subtracts that floor; its interval uses 2000 paired game bootstraps, seed 20261016.',
              'Changing nodes changes search effort; this cannot isolate software knowledge from search instability.']
    config = {'inputs_sha256': {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in [source, Path(__file__)]},
              'outputs_sha256': {str(output): hashlib.sha256(output.read_bytes()).hexdigest()}, 'limits': limits}
    config_path = Path('data/derived/advice_noise_floor_config.json')
    config_path.write_text(json.dumps(config, indent=2) + '\n')
    write_panel('advice_noise_floor', {'title': 'Release disagreement and budget sensitivity', 'comparisons': output_rows, 'limits': limits},
                [str(output), str(config_path)])
    for row in output_rows:
        print(row['first'], row['second'], round(row['between_agreement_100000'], 3), round(row['excess_disagreement_100000'], 3), round(row['excess_low_100000'], 3), round(row['excess_high_100000'], 3))


if __name__ == '__main__':
    main()
