'''
Created on 14 October 2026

evaluate selected championship games and documented PAL/CSS 2005 decisions

@author: Dinghao Luo
'''

#%% imports
import csv
import hashlib
import json
import platform
from pathlib import Path

import chess
import chess.engine
import chess.pgn


#%% configuration
DATA = Path('data')
ENGINE = Path('.venv/stockfish-17.1/stockfish/stockfish-macos-m1-apple-silicon')
OPTIONS = {'Threads': 1, 'Hash': 64, 'UCI_ShowWDL': True,
           'Skill Level': 20, 'UCI_LimitStrength': False, 'SyzygyPath': ''}
NODES = 250_000
STABILITY_NODES = 1_000_000


#%% inputs
with (DATA / 'source_manifest.csv').open() as source:
    hashes = {row['source_file']: row['sha256'] for row in csv.DictReader(source)}
with (DATA / 'game_classifications.csv').open() as source:
    reviewed = {row['game_id']: row for row in csv.DictReader(source)}
with (DATA / 'stockfish_pilot_games.csv').open() as source:
    selected = list(csv.DictReader(source))
with (DATA / 'pal_css_2005_decisions.csv').open() as source:
    cases = list(csv.DictReader(source))

positions = []
for name in {game['source_file'] for game in selected}:
    path = DATA / 'raw/pgnmentor' / name
    assert hashlib.sha256(path.read_bytes()).hexdigest() == hashes[name], name
for selected_game in selected:
    classification = reviewed[selected_game['game_id']]
    assert (classification['accepted_for_analysis'], classification['game_class']) == ('1', 'classical')
    assert classification['raw_game_id'] == selected_game['raw_game_id']
    path = DATA / 'raw/pgnmentor' / selected_game['source_file']
    with path.open() as source:
        for _ in range(int(selected_game['source_ordinal'])):
            game = chess.pgn.read_game(source)
    assert not game.errors
    board = game.board()
    raw_game_id = selected_game['raw_game_id']
    for ply, move in enumerate(game.mainline_moves(), 1):
        positions.append({
            'collection': 'championship', 'position_id': f'{raw_game_id}:{ply}',
            'game_id': selected_game['game_id'], 'event_id': selected_game['event_id'],
            'ply': ply, 'fen_before': board.fen(), 'played_move': move.uci(),
            'reported_alternative': '',
        })
        board.push(move)
for case in cases:
    positions.append({
        'collection': 'pal_css_2005', 'position_id': case['case_id'], 'game_id': '',
        'event_id': 'pal_css_2005', 'ply': int(case['ply']),
        'fen_before': case['fen_before'], 'played_move': case['move_uci'],
        'reported_alternative': case['reported_alternative_uci'],
    })


#%% engine searches
def search(engine: chess.engine.SimpleEngine, board: chess.Board, nodes: int,
           move: chess.Move | None = None) -> dict:
    info = engine.analyse(board, chess.engine.Limit(nodes=nodes), game=object(),
                          root_moves=[move] if move is not None else None)
    score = info['score'].pov(board.turn)
    return {
        'move': info['pv'][0].uci(), 'cp': score.score(), 'mate': score.mate(),
        'nodes': info['nodes'], 'depth': info['depth'],
    }


results = []
with chess.engine.SimpleEngine.popen_uci(str(ENGINE)) as engine:
    assert engine.id['name'] == 'Stockfish 17.1'
    engine.configure(OPTIONS)
    config = {
        'release_url': 'https://github.com/official-stockfish/Stockfish/releases/tag/sf_17.1',
        'binary_sha256': hashlib.sha256(ENGINE.read_bytes()).hexdigest(),
        'engine_id': engine.id, 'options': OPTIONS, 'multipv': 1, 'ponder': False,
        'eval_file': engine.options['EvalFile'].default,
        'eval_file_small': engine.options['EvalFileSmall'].default,
        'nnue': 'embedded in the hashed official binary',
        'architecture': platform.machine(), 'python_chess_version': chess.__version__,
        'nodes': NODES, 'stability_nodes': STABILITY_NODES,
        'hash_policy': 'ucinewgame before every root search',
        'position_history': 'FEN only; halfmove counter retained, prior repetitions unavailable',
        'syzygy': 'disabled; no external tablebases',
        'selection': 'first and last played classical games of four named matches',
        'stability_selection': 'every tenth championship ply and all PAL/CSS 2005 positions',
        'selected_sources': {row['source_file']: hashes[row['source_file']] for row in selected},
        'selection_sha256': hashlib.sha256((DATA / 'stockfish_pilot_games.csv').read_bytes()).hexdigest(),
        'pal_css_2005_sha256': hashlib.sha256((DATA / 'pal_css_2005_decisions.csv').read_bytes()).hexdigest(),
    }
    for position in positions:
        board = chess.Board(position['fen_before'])
        played_move = board.parse_uci(position['played_move'])
        budgets = [NODES]
        if position['collection'] == 'pal_css_2005' or position['ply'] % 10 == 0:
            budgets.append(STABILITY_NODES)
        for nodes in budgets:
            best = search(engine, board, nodes)
            played = search(engine, board, nodes, played_move)
            row = {**position, 'node_budget': nodes}
            for prefix, info in [('best', best), ('played', played)]:
                row.update({f'{prefix}_{key}': value for key, value in info.items()})
            row['cp_difference'] = (best['cp'] - played['cp']
                                    if best['cp'] is not None and played['cp'] is not None else None)
            row['move_agreement'] = int(best['move'] == played_move.uci())
            if position['reported_alternative']:
                alternative = board.parse_uci(position['reported_alternative'])
                alternative_info = search(engine, board, nodes, alternative)
            else:
                alternative_info = dict.fromkeys(['move', 'cp', 'mate', 'nodes', 'depth'])
            row.update({f'alternative_{key}': value for key, value in alternative_info.items()})
            results.append(row)


#%% write
with (DATA / 'stockfish_pilot.csv').open('w', newline='') as destination:
    writer = csv.DictWriter(destination, fieldnames=list(results[0]), lineterminator='\n')
    writer.writeheader()
    writer.writerows(results)
(DATA / 'stockfish_config.json').write_text(json.dumps(config, indent=2) + '\n')
print(f'{len(positions)} positions; {len(results)} budget comparisons')
