'''
Created on 15 October 2026

check historical leakage, illegal scores, and repetition history

@author: Dinghao Luo
'''

#%% imports
import csv
import json
import subprocess
import tempfile
from pathlib import Path

import chess
import numpy as np
from statsmodels.regression.linear_model import OLS
from statsmodels.stats.sandwich_covariance import S_hac_simple

from novelty_trend_tests import calendar_trend


#%% reference contamination
binary = Path('.venv/master-index-build/release/master-index').resolve()
with tempfile.TemporaryDirectory() as directory:
    folder = Path(directory)
    board = chess.Board()
    board.push_uci('e2e4')
    with (folder / 'targets.csv').open('w', newline='') as destination:
        writer = csv.writer(destination)
        writer.writerow(['position_id', 'fen', 'previous_fen', 'move_uci'])
        writer.writerow([1, board.fen(), '', ''])
        board.push_uci('e7e5')
        writer.writerow([2, board.fen(), '', ''])
    (folder / 'games.csv').write_text('game_id,moves_uci,white,black\n1,e2e4 e7e5,A,B\n')
    pgn = '''[Event "illegal score"]
[Date "1700.01.01"]

1. e4 e5 2. Ke2 Ke7 3. Ke1 Ke8 4. e4 *

[Event "misdated target"]
[Date "1800.01.01"]
[White "A"]
[Black "B"]

1. e4 e5 *

[Event "correspondence"]
[Date "1850.01.01"]

1. e4 e5 *

[Event "ordinary game"]
[Date "1900.??.??"]

1. e4 e5 *

[Event "WCh"]
[Date "1750.01.01"]
[White "A"]
[Black "B"]

1. e4 e5 *
'''
    run = subprocess.run([str(binary), str(folder / 'targets.csv'), str(folder / 'games.csv'),
                          str(folder / 'out')],
                         input=pgn, text=True, capture_output=True, check=True)
    summary = json.loads(run.stdout)
    assert summary['rejected_games'] == 1
    assert summary['excluded_non_otb_metadata'] == 1
    assert summary['excluded_championship_copies'] == 1
    assert summary['excluded_championship_metadata'] == 1
    with (folder / 'out.positions.csv').open() as source:
        positions = list(csv.DictReader(source))
    assert len(positions) == 2
    assert all(row['earliest_date_end'] == '19001231' for row in positions)
    assert all(row['source_ordinal'] == '4' for row in positions)
    with (folder / 'out.samples.csv').open() as source:
        sampled = list(csv.DictReader(source))
    assert len(sampled) == 1 and sampled[0]['source_ordinal'] == '4'
    assert set(sampled[0]['position_ids'].split()) == {'1', '2'}


#%% saved engine positions
with Path('data/stockfish_pilot.csv').open() as source:
    for row in csv.DictReader(source):
        board = chess.Board(row['initial_fen'])
        for move in row['history_uci'].split():
            board.push_uci(move)
        assert board.fen() == row['fen_before'], row['position_id']
        assert len(board.move_stack) == int(row['ply']) - 1
        assert board.parse_uci(row['played_move']) in board.legal_moves

board = chess.Board()
for move in ['g1f3', 'g8f6', 'f3g1', 'f6g8'] * 4:
    board.push_uci(move)
assert board.is_fivefold_repetition()
assert not chess.Board(board.fen()).is_fivefold_repetition()


#%% calendar-year covariance
years = np.arange(1950, 1990)
values = np.sin(years / 3) + 0.15 * (years - years.mean())
design = np.column_stack((np.ones(len(years)), (years - years.mean()) / 100))
ordinary = OLS(values, design).fit(cov_type='HAC', cov_kwds={'maxlags': 5, 'use_correction': True}, use_t=True)
test = calendar_trend(years, values, 5)
assert np.allclose([test['ci95_low'], test['ci95_high']], ordinary.conf_int()[1])
assert np.isclose(test['two_sided_p'], ordinary.pvalues[1])

with Path('data/master_novelty_years.csv').open() as source:
    rows = list(csv.DictReader(source))
years = np.array([int(row['year']) for row in rows])
values = np.array([float(row['prior_year_first_new_ply_median']) for row in rows])
design = np.column_stack((np.ones(len(years)), (years - years.mean()) / 100))
fit = OLS(values, design).fit()
# zero scores in missing years reproduce the calendar weights
scores = np.zeros((years.max() - years.min() + 1, 2))
scores[years - years.min()] = design * fit.resid[:, None]
xtx_inverse = fit.normalized_cov_params
covariance = xtx_inverse @ S_hac_simple(scores, nlags=10) @ xtx_inverse * len(years) / fit.df_resid
expected = fit.t_test([0, 1], cov_p=covariance, use_t=True)
test = calendar_trend(years, values, 10)
assert np.allclose([test['ci95_low'], test['ci95_high']], expected.conf_int()[0])
assert np.isclose(test['two_sided_p'], expected.pvalue)
print('reference exclusions, engine histories, and calendar covariance checked')
