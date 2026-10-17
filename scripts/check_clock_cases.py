'''
Created on 15 October 2026

check reported preparation and late mistakes with the same frozen engine

@author: Dinghao Luo
'''

#%% imports
import csv
import hashlib
import io
import json
from pathlib import Path
from zipfile import ZipFile

import chess.engine
import chess.pgn

from pal_css_2005_case import ENGINE, search


#%% cases
# the later examples test specific accounts, not an error rate for all games
CASES = [
    ('zacks_tank_loss_12', 'pal_final.zip', 11, 23),
    ('zacks_tank_loss_14', 'pal_final.zip', 11, 27),
    ('nielsen_endgame_28', 'pal_2007_annotations.pgn', 1, 55),
    ('nielsen_prepared_exchange', 'pal_2007_final5.zip', 2, 52),
    ('nielsen_prepared_long_think', 'pal_2007_final5.zip', 2, 68),
]


#%% main
def main() -> None:
    data = Path('data/derived')
    cache = Path('cache/sources')
    config = json.loads((data / 'stockfish_config.json').read_text())
    frozen = {row['file']: row['sha256'] for row in json.loads(Path('data/curated/source_files.json').read_text())}
    assert hashlib.sha256(ENGINE.read_bytes()).hexdigest() == config['binary_sha256']
    inputs = {}
    rows = []
    with chess.engine.SimpleEngine.popen_uci(str(ENGINE)) as engine:
        engine.configure(config['options'])
        for case_id, name, ordinal, ply in CASES:
            raw = (cache / name).read_bytes()
            inputs[name] = hashlib.sha256(raw).hexdigest()
            assert inputs[name] == frozen[name], name
            if name.endswith('.zip'):
                with ZipFile(io.BytesIO(raw)) as archive:
                    raw = archive.read(next(n for n in archive.namelist() if n.lower().endswith('.pgn')))
            pgn = io.StringIO(raw.decode('latin-1'))
            games = list(iter(lambda: chess.pgn.read_game(pgn), None))
            game = games[ordinal - 1]
            assert not game.errors
            moves = list(game.mainline_moves())
            board = game.board()
            for move in moves[:ply - 1]:
                board.push(move)
            played = moves[ply - 1]
            searches = [('unrestricted', None, 3, nodes) for nodes in [1_000_000, 4_000_000, 16_000_000]]
            for comparison, candidates, multipv, budget in searches:
                infos = search(engine, board, budget, candidates, multipv)
                for info in infos:
                    score = info['score'].pov(board.turn)
                    wdl = info['wdl'].pov(board.turn)
                    rows.append({'case_id': case_id, 'source_file': name, 'source_ordinal': ordinal,
                                 'ply': ply, 'played_move': board.san(played), 'played_uci': played.uci(),
                                 'comparison': comparison, 'node_budget': budget,
                                 'rank': info['multipv'], 'move_san': board.san(info['pv'][0]),
                                 'move_uci': info['pv'][0].uci(), 'mover_cp': score.score(),
                                 'mover_mate': score.mate(), 'mover_expected_score': (wdl.wins + 0.5 * wdl.draws) / 1000,
                                 'depth': info['depth'], 'search_nodes': info['search_nodes'],
                                 'fen_before': board.fen(), 'history_uci': ' '.join(move.uci() for move in board.move_stack),
                                 'pv_uci': ' '.join(move.uci() for move in info['pv'])})
            print(case_id, flush=True)
    with (data / 'clock_case_evaluations.csv').open('w', newline='') as destination:
        writer = csv.DictWriter(destination, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
    metadata = {'engine': 'Stockfish 17.1', 'binary_sha256': config['binary_sha256'],
                'options': config['options'], 'inputs_sha256': inputs,
                'selection': 'two long thinks in the timed 2005 loss; three 2007 participant claims',
                'method': 'full move history, fresh hash; last complete equal-depth MultiPV cycle with distinct roots',
                'budgets': [1000000, 4000000, 16000000],
                'interpretation': 'modern checks of selected moves, not historical engine behaviour or causal effects of thinking time',
                'output_sha256': hashlib.sha256((data / 'clock_case_evaluations.csv').read_bytes()).hexdigest()}
    (data / 'clock_case_config.json').write_text(json.dumps(metadata, indent=2) + '\n')


if __name__ == '__main__':
    main()
