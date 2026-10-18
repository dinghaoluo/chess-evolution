'''
Created on 16 October 2026

compare release recommendations on a frozen sample of verified positions

@author: Dinghao Luo
'''

#%% imports
import csv
import hashlib
import json
from collections import Counter, defaultdict, deque
from itertools import combinations
from pathlib import Path

import chess
import chess.engine
import numpy as np

from pal_css_2005_case import search, result_rows


#%% sampling
def sample_positions(pool: list[dict], protocol: dict) -> list[dict]:
    strata = defaultdict(list)
    for game in pool:
        if 'reference_headers' not in game:
            continue
        board, positions = chess.Board(), []
        for value in game['moves_uci'].split():
            colour = 'White' if board.turn else 'Black'
            elo = game['headers'].get(colour + 'Elo', '')
            if 9 <= board.fullmove_number <= 40 and elo.isdigit() and int(elo) >= 2200:
                positions.append({'game_id': game['game_id'], 'year': game['year'], 'event_id': game['event_id'],
                                  'ply': board.ply() + 1, 'fullmove': board.fullmove_number, 'pgn_elo': int(elo),
                                  'history_uci': ' '.join(move.uci() for move in board.move_stack), 'pieces': len(board.piece_map()),
                                  'played': value, 'source_ordinal': game['ordinal']})
            board.push_uci(value)
        if not positions:
            continue
        chosen = min(positions, key=lambda row: hashlib.sha256(f'{protocol["seed"]}|advice|{row["game_id"]}|{row["ply"]}'.encode()).hexdigest())
        rating = chosen['pgn_elo']
        chosen['band'] = '2600+' if rating >= 2600 else '2400-2599' if rating >= 2400 else '2200-2399'
        key = chosen['year'], chosen['band'], chosen['fullmove'] > 20, chosen['pieces'] >= 20
        strata[key].append(chosen)
    queues = [deque(sorted(rows, key=lambda row: hashlib.sha256(f'{protocol["seed"]}|advice-game|{row["game_id"]}'.encode()).hexdigest())) for key, rows in sorted(strata.items())]
    selected = []
    while len(selected) < protocol['positions'] and any(queues):
        for queue in queues:
            if queue and len(selected) < protocol['positions']:
                selected.append(queue.popleft())
    stable = sorted(selected, key=lambda row: hashlib.sha256(f'{protocol["seed"]}|advice-stability|{row["game_id"]}'.encode()).hexdigest())[:protocol['stability_positions']]
    stable_ids = {row['game_id'] for row in stable}
    for row in selected:
        row['stability_position'] = row['game_id'] in stable_ids
    return selected


#%% fixed searches
def main() -> None:
    protocol_path, pool_path = Path('data/curated/advice_protocol.json'), Path('data/derived/learning_pilot_pool.jsonl')
    protocol = json.loads(protocol_path.read_text())
    builds = {build['name']: build for build in json.loads(Path('data/derived/engine_builds.json').read_text())}
    selected = sample_positions([json.loads(line) for line in pool_path.read_text().splitlines()], protocol)
    sample_path = Path('data/derived/advice_sample.csv')
    with sample_path.open('w', newline='') as destination:
        writer = csv.DictWriter(destination, fieldnames=list(selected[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(selected)
    sample_hash = hashlib.sha256(sample_path.read_bytes()).hexdigest()
    print('sample frozen:', len(selected), 'positions;', sample_hash, flush=True)
    engines = {}
    for name in protocol['engines']:
        build = builds[name]
        assert hashlib.sha256(Path(build['binary']).read_bytes()).hexdigest() == build['binary_sha256']
        engine = chess.engine.SimpleEngine.popen_uci(build['binary'])
        engine.configure(build['options'])
        engines[name] = engine
    searches, preferences, judged = [], [], []
    try:
        for index, case in enumerate(selected, 1):
            board = chess.Board()
            for value in case['history_uci'].split():
                board.push_uci(value)
            for budget in ([protocol['node_budget'], protocol['stability_nodes']] if case['stability_position'] else [protocol['node_budget']]):
                roots = {}
                for name in protocol['engines']:
                    info = search(engines[name], board, budget, multipv=1)
                    move = info[0]['pv'][0]
                    roots[name] = move
                    preferences.append({'game_id': case['game_id'], 'ply': case['ply'], 'engine': name,
                                        'nodes': budget, 'move_uci': move.uci(), 'move_san': board.san(move)})
                    # older releases do not all emit WDL; retain their native CP and mate
                    searches.append({'game_id': case['game_id'], 'ply': case['ply'], 'engine': name, 'stage': 'recommendation',
                                     'budget': budget, 'move_uci': move.uci(), 'white_cp': info[0]['score'].white().score(),
                                     'white_mate': info[0]['score'].white().mate(), 'depth': info[0]['depth'],
                                     'nodes': info[0]['nodes'], 'search_nodes': info[0]['search_nodes'],
                                     'fen_before': board.fen(), 'history_uci': case['history_uci'],
                                     'pv_uci': ' '.join(move.uci() for move in info[0]['pv'])})
                infos = search(engines[protocol['judge']], board, budget, list(dict.fromkeys(roots.values())), len(set(roots.values())))
                searches += [{**row, 'engine': protocol['judge'], 'stage': 'judge'} for row in result_rows(infos, board, str(case['source_ordinal']), case['game_id'], 'advice_candidates', budget)]
                expected = {}
                for info in infos:
                    wdl = info['wdl'].pov(board.turn)
                    expected[info['pv'][0]] = (wdl.wins + wdl.draws / 2) / 1000
                modern = expected[roots[protocol['judge']]]
                for name, move in roots.items():
                    difference = modern - expected[move]
                    judged.append({'game_id': case['game_id'], 'ply': case['ply'], 'engine': name, 'nodes': budget,
                                   'modern_minus_release': difference, 'nonnegative_loss': max(0, difference),
                                   'judge_reversal': difference < 0, 'above_0_02': difference > .02, 'above_0_05': difference > .05})
            if index % 50 == 0:
                print(index, '/', len(selected), 'positions', flush=True)
    finally:
        for engine in engines.values():
            engine.quit()
    outputs = [sample_path]
    for name, rows in [('advice_preferences', preferences), ('advice_judgements', judged)]:
        path = Path('data/derived/' + name + '.csv')
        with path.open('w', newline='') as destination:
            writer = csv.DictWriter(destination, fieldnames=list(rows[0]), lineterminator='\n')
            writer.writeheader()
            writer.writerows(rows)
        outputs.append(path)
    path = Path('data/derived/advice_searches.jsonl')
    path.write_text(''.join(json.dumps(row) + '\n' for row in searches))
    outputs.append(path)
    rng, comparisons = np.random.default_rng(protocol['seed']), []
    lookup = {(row['game_id'], row['engine'], row['nodes']): row['move_uci'] for row in preferences}
    for first, second in combinations(protocol['engines'], 2):
        agreement = np.array([lookup[row['game_id'], first, protocol['node_budget']] == lookup[row['game_id'], second, protocol['node_budget']] for row in selected])
        low, high = np.quantile([rng.choice(agreement, len(agreement)).mean() for _ in range(2000)], [.025, .975])
        comparisons.append({'first': first, 'second': second, 'positions': len(selected),
                            'agreement': float(agreement.mean()), 'bootstrap_low': float(low), 'bootstrap_high': float(high)})
    path = Path('data/derived/advice_agreement.csv')
    with path.open('w', newline='') as destination:
        writer = csv.DictWriter(destination, fieldnames=list(comparisons[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(comparisons)
    outputs.append(path)
    inputs = [protocol_path, pool_path, Path(__file__), Path('scripts/pal_css_2005_case.py'), Path('data/derived/engine_builds.json')]
    config = {'protocol': protocol, 'engines': [builds[name] for name in protocol['engines']],
              'sample_sha256_before_search': sample_hash, 'coverage': dict(Counter(row['year'] for row in selected)),
              'inputs_sha256': {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in inputs},
              'outputs_sha256': {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in outputs},
              'limits': protocol['limits']}
    Path('data/derived/advice_config.json').write_text(json.dumps(config, indent=2) + '\n')


if __name__ == '__main__':
    main()
