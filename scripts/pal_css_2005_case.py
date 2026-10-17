'''
Created on 15 October 2026

check the reported decisions and evaluation changes in the annotated PAL/CSS games

@author: Dinghao Luo
'''

#%% imports
import csv
import hashlib
import json
from pathlib import Path

import chess
import chess.engine


#%% inputs
DATA = Path('data/derived')
ENGINE = Path('cache/engines/stockfish-17.1/stockfish/stockfish-macos-m1-apple-silicon')
BUDGETS = [1_000_000, 4_000_000, 16_000_000]


#%% search
def search(
        engine: chess.engine.SimpleEngine, board: chess.Board, nodes: int,
        moves: list[chess.Move] | None = None, multipv: int = 2,
) -> list[dict]:
    iteration = {}
    completed = []
    roots = list(board.legal_moves) if moves is None else moves
    if not roots:
        raise ValueError('search requires at least one legal move')
    multipv = min(multipv, len(roots))
    # a node limit can interrupt the next iteration after only one candidate
    with engine.analysis(board, chess.engine.Limit(nodes=nodes), multipv=multipv,
                         root_moves=moves, game=object()) as analysis:
        for info in analysis:
            if 'score' not in info:
                continue
            # a revised rank 1 starts another cycle even at the same depth
            if info['multipv'] == 1:
                iteration = {}
            if info.get('lowerbound') or info.get('upperbound'):
                continue
            iteration[info['multipv']] = info
            if info['multipv'] == multipv and len(iteration) == multipv:
                candidates = [iteration[rank] for rank in range(1, multipv + 1)]
                if (len({candidate['depth'] for candidate in candidates}) == 1
                        and len({candidate['pv'][0] for candidate in candidates}) == multipv):
                    completed = candidates
        total_nodes = max((info.get('nodes', 0) for info in analysis.multipv), default=0)
    if not completed:
        raise chess.engine.EngineError('node budget ended before a complete exact MultiPV cycle')
    return [{**info, 'search_nodes': total_nodes} for info in completed]


def result_rows(
        infos: list[dict], board: chess.Board, ordinal: str, case_id: str,
        comparison: str, nodes: int,
) -> list[dict]:
    rows = []
    for info in infos:
        score = info['score'].white()
        wdl = info['wdl'].white()
        rows.append({
            'source_ordinal': ordinal, 'case_id': case_id, 'ply': board.ply() + 1,
            'comparison': comparison, 'node_budget': nodes, 'rank': info['multipv'],
            'move_uci': info['pv'][0].uci(), 'move_san': board.san(info['pv'][0]),
            'white_cp': score.score(), 'white_mate': score.mate(),
            'white_win': wdl.wins, 'draw': wdl.draws, 'black_win': wdl.losses,
            'white_expected_score': (wdl.wins + 0.5 * wdl.draws) / 1000,
            'depth': info['depth'], 'nodes': info['nodes'],
            'search_nodes': info['search_nodes'], 'initial_fen': board.root().fen(),
            'fen_before': board.fen(),
            'history_uci': ' '.join(move.uci() for move in board.move_stack),
            'pv_uci': ' '.join(move.uci() for move in info['pv']),
            'pv_san': board.variation_san(info['pv']),
        })
    return rows


#%% comparisons
def main() -> None:
    config = json.loads((DATA / 'stockfish_config.json').read_text())
    assert hashlib.sha256(ENGINE.read_bytes()).hexdigest() == config['binary_sha256']
    with (DATA / 'pal_css_2005_games.csv').open() as source:
        games = {row['source_ordinal']: row for row in csv.DictReader(source)}
    with (Path('data/curated') / 'pal_css_2005_decisions.csv').open() as source:
        cases = list(csv.DictReader(source))
    rows = []
    with chess.engine.SimpleEngine.popen_uci(str(ENGINE)) as engine:
        engine.configure(config['options'])
        for case in cases:
            ordinal = case['source_ordinal']
            game = games[ordinal]
            board = chess.Board(game['initial_fen'])
            for move in game['moves_uci'].split()[:int(case['ply']) - 1]:
                board.push_uci(move)
            assert board.fen() == case['fen_before'], case['case_id']
            searches = [('unrestricted', board, None, 3, nodes) for nodes in BUDGETS]
            if case['reported_alternative_uci']:
                moves = [board.parse_uci(case[key])
                         for key in ['move_uci', 'reported_alternative_uci']]
                searches += [('reported_pair', board, moves, 2, nodes) for nodes in BUDGETS]
            if case['case_id'] == 'zacks_game22_27':
                moves = [board.parse_san(san) for san in ['h4', 'f4', 'Ng3']]
                searches += [('reported_plans', board, moves, 3, nodes) for nodes in BUDGETS]
            if case['case_id'] == 'zacks_dobrov_35':
                for key in ['move_uci', 'reported_alternative_uci']:
                    branch = board.copy()
                    branch.push_uci(case[key])
                    searches.append(('reply_after_' + case[key], branch, None, 2, BUDGETS[-1]))
            for comparison, position, moves, multipv, nodes in searches:
                infos = search(engine, position, nodes, moves, multipv)
                if comparison.startswith('reply_after_'):
                    rg8 = position.parse_san('Rg8')
                    if rg8 not in [info['pv'][0] for info in infos]:
                        forced = search(engine, position, nodes, [rg8], 1)[0]
                        infos.append({**forced, 'multipv': ''})
                rows += result_rows(infos, position, ordinal, case['case_id'], comparison, nodes)
            print(case['case_id'], flush=True)

        # all supplied positions show whether the chosen moments omit later reversals
        trajectory = []
        for ordinal in ['13', '22', '26']:
            board = chess.Board(games[ordinal]['initial_fen'])
            for ply, move in enumerate(games[ordinal]['moves_uci'].split(), 1):
                if ply >= 11:
                    infos = search(engine, board, BUDGETS[0], multipv=1)
                    trajectory += result_rows(infos, board, ordinal, '', 'trajectory', BUDGETS[0])
                board.push_uci(move)
            print('trajectory', ordinal, flush=True)

    for name, output in [('pal_css_2005_case', rows), ('pal_css_2005_trajectory', trajectory)]:
        if not output:
            continue
        with (DATA / (name + '.csv')).open('w', newline='') as destination:
            writer = csv.DictWriter(destination, fieldnames=list(output[0]), lineterminator='\n')
            writer.writeheader()
            writer.writerows(output)
    case_config = {
        'binary_sha256': config['binary_sha256'], 'options': config['options'],
        'engine': 'Stockfish 17.1', 'python_chess_version': chess.__version__,
        'nodes': BUDGETS, 'score_perspective': 'white',
        'hash_policy': 'ucinewgame before each search',
        'iteration': 'last exact completed MultiPV cycle, reset on rank 1; distinct roots at equal depth',
        'position_history': 'complete move stack from the source game',
        'selection': 'all documented decisions, plus the annotated Bf4 alternative and three White plans',
        'comparisons': 'unrestricted MultiPV 3; shared restricted searches for reported alternatives',
        'reply_check': 'unrestricted MultiPV 2 after each move-18 candidate; separate forced Rg8 if absent',
        'trajectory': 'unrestricted single PV, 1M nodes, every supplied position from ply 11 in all three annotated scores',
        'interpretation': 'modern evaluations; trajectories locate changes and do not measure move loss',
        'turning_points': {
            'selection': 'three largest mover-perspective WDL deteriorations per side in each supplied annotated score at 1M nodes, where the played move differed from the recommendation',
            'comparison': 'shared root search of the played move and the 1M recommendation, at 4M and 16M nodes',
            'interpretation': 'exploratory checks of evaluation changes; not an intervention effect estimate',
            'trajectory_sha256': hashlib.sha256((DATA / 'pal_css_2005_trajectory.csv').read_bytes()).hexdigest(),
        },
        'inputs': {str(path): hashlib.sha256(path.read_bytes()).hexdigest()
                   for path in [DATA / 'pal_css_2005_games.csv', Path('data/curated/pal_css_2005_decisions.csv')]},
        'outputs': {name: hashlib.sha256((DATA / name).read_bytes()).hexdigest()
                    for name in ['pal_css_2005_case.csv', 'pal_css_2005_trajectory.csv']},
    }
    (DATA / 'pal_css_2005_case_config.json').write_text(json.dumps(case_config, indent=2) + '\n')


if __name__ == '__main__':
    main()
