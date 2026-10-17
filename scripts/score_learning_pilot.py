'''
Created on 16 October 2026

measure pilot loss variance and search stability without fitting historical trends

@author: Dinghao Luo
'''

#%% imports
import argparse
import csv
import hashlib
import json
import math
import time
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import chess
import chess.engine
import numpy as np

from pal_css_2005_case import search, result_rows


#%% move losses
def move_metrics(infos: list[dict], played: chess.Move, recommended: chess.Move, colour: chess.Color) -> dict:
    by_move = {info['pv'][0]: info for info in infos}
    expectation = {}
    centipawns, mates = {}, {}
    for move, info in by_move.items():
        wdl = info['wdl'].pov(colour)
        expectation[move] = (wdl.wins + wdl.draws / 2) / 1000
        score = info['score'].pov(colour)
        centipawns[move], mates[move] = score.score(), score.mate()
    signed_loss = expectation[recommended] - expectation[played]
    mate_case = any(value is not None for value in mates.values())
    signed_cp = None if mate_case else centipawns[recommended] - centipawns[played]
    proxy = {move: by_move[move]['score'].pov(colour).score(mate_score=100000) for move in by_move}
    win_percent = {move: 100 / (1 + math.exp(-0.00368208 * cp)) for move, cp in proxy.items()}
    win_loss = max(0, win_percent[recommended] - win_percent[played])
    accuracy = min(100, max(0, 103.1668 * math.exp(-0.04354 * win_loss) - 3.1669))
    return {'signed_expected_loss': signed_loss, 'expected_loss': max(0, signed_loss),
            'ranking_reversed': signed_loss < 0, 'blunder': signed_loss > 0.10,
            'mate_comparison': mate_case, 'signed_cp_loss': signed_cp,
            'cp_loss': None if signed_cp is None else max(0, signed_cp), 'move_accuracy': accuracy}


def score_game(task: tuple[dict, list[dict], dict]) -> dict:
    game, sides, engine_config = task
    board = chess.Board()
    moves = [chess.Move.from_uci(value) for value in game['moves_uci'].split()]
    colours = {side['colour'] for side in sides}
    eligible_plies = [ply for ply in range(1, len(moves) + 1)
                      if 9 <= (ply + 1) // 2 <= 60 and ('white' if ply % 2 else 'black') in colours]
    stability_ply = min(eligible_plies, key=lambda ply: hashlib.sha256(f'20261016|stability|{game["game_id"]}|{ply}'.encode()).hexdigest()) if eligible_plies else None
    paths = [Path('data/local/learning_pilot') / (game['game_id'] + suffix) for suffix in ['_searches.jsonl', '_moves.jsonl']]
    inputs_key = hashlib.sha256(json.dumps(task, sort_keys=True).encode()).hexdigest()
    complete = paths[0].with_name(game['game_id'] + '_complete.json')
    if complete.exists():
        saved = json.loads(complete.read_text())
        assert saved['inputs_key'] == inputs_key
        assert all(hashlib.sha256(Path(name).read_bytes()).hexdigest() == value for name, value in saved['outputs_sha256'].items())
        return saved
    started, metrics, searches = time.perf_counter(), [], []
    with chess.engine.SimpleEngine.popen_uci(engine_config['binary']) as engine:
        engine.configure(engine_config['options'])
        for ply, move in enumerate(moves, 1):
            colour = 'white' if board.turn else 'black'
            if ply in eligible_plies:
                for nodes in ([25000, 100000] if ply == stability_ply else [25000]):
                    screening = search(engine, board, nodes, multipv=1)
                    recommended = screening[0]['pv'][0]
                    roots = list(dict.fromkeys([recommended, move]))
                    paired = screening if len(roots) == 1 else search(engine, board, nodes, roots, len(roots))
                    search_id = game['game_id'] + ':' + str(ply) + ':' + str(nodes)
                    searches += [{**row, 'search_id': search_id} for row in result_rows(screening, board, str(game['ordinal']), game['game_id'], 'screening', nodes)]
                    if len(roots) > 1:
                        searches += [{**row, 'search_id': search_id} for row in result_rows(paired, board, str(game['ordinal']), game['game_id'], 'paired', nodes)]
                    metrics.append({'game_id': game['game_id'], 'ply': ply, 'fullmove': board.fullmove_number,
                                    'colour': colour, 'nodes': nodes, 'recommended': recommended.uci(), 'played': move.uci(),
                                    'pieces': len(board.piece_map()), 'stability_position': ply == stability_ply,
                                    **move_metrics(paired, move, recommended, board.turn)})
            board.push(move)
    for path, rows in zip(paths, [searches, metrics]):
        path.write_text(''.join(json.dumps(row) + '\n' for row in rows))
    result = {'game_id': game['game_id'], 'inputs_key': inputs_key,
              'seconds': time.perf_counter() - started, 'screened_moves': sum(row['nodes'] == 25000 for row in metrics),
              'outputs_sha256': {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}}
    complete.write_text(json.dumps(result, indent=2) + '\n')
    return result


#%% variance and throughput
def summarise(completed: list[dict], sample: list[dict], inputs: list[Path]) -> None:
    moves = defaultdict(list)
    stability = []
    for item in completed:
        path = Path('data/local/learning_pilot') / (item['game_id'] + '_moves.jsonl')
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        for row in rows:
            if row['nodes'] == 25000:
                moves[row['game_id'], row['colour']].append(row)
        pairs = defaultdict(dict)
        for row in rows:
            if row['stability_position']:
                pairs[row['ply']][row['nodes']] = row
        for ply, pair in pairs.items():
            low, high = pair[25000], pair[100000]
            stability.append({'game_id': item['game_id'], 'ply': ply,
                              'same_recommendation': low['recommended'] == high['recommended'],
                              'loss_change': high['expected_loss'] - low['expected_loss'],
                              'absolute_loss_change': abs(high['expected_loss'] - low['expected_loss'])})
    player_games = []
    for side in sample:
        rows = moves[side['game_id'], side['colour']]
        primary = [row for row in rows if 9 <= row['fullmove'] <= 40]
        secondary = [row for row in rows if 11 <= row['fullmove'] <= 60]
        cp = [row['cp_loss'] for row in secondary if row['cp_loss'] is not None]
        player_games.append({**side, 'primary_moves': len(primary), 'secondary_moves': len(secondary),
                             'mean_loss': float(np.mean([row['expected_loss'] for row in primary])) if primary else None,
                             'mean_loss_without_seven_piece': float(np.mean([row['expected_loss'] for row in primary if row['pieces'] > 7])) if any(row['pieces'] > 7 for row in primary) else None,
                             'reversed_rankings': sum(row['ranking_reversed'] for row in rows),
                             'blunders': sum(row['blunder'] for row in primary),
                             'mean_move_accuracy': float(np.mean([row['move_accuracy'] for row in secondary])) if secondary else None,
                             'cp_denominator': len(cp), 'mate_comparisons': sum(row['mate_comparison'] for row in secondary),
                             **{'cp_ge_' + str(limit): sum(loss >= limit for loss in cp) for limit in [50, 100, 200]},
                             'cp_50_lt100': sum(50 <= loss < 100 for loss in cp),
                             'cp_100_lt200': sum(100 <= loss < 200 for loss in cp),
                             'cp_ge_200_bin': sum(loss >= 200 for loss in cp)})
    variances = []
    rng = np.random.default_rng(20261016)
    for year in [1985, 1995, 2005, 2015, 2024]:
        for band in ['2200-2399', '2400-2599', '2600+']:
            rows = [row for row in player_games if row['year'] == str(year) and row['band'] == band and row['mean_loss'] is not None]
            values = np.array([row['mean_loss'] for row in rows])
            # no mean comparisons: this pilot informs variance, not a historical finding
            variance = float(np.var(values, ddof=1)) if len(values) > 1 else None
            interval = np.quantile([np.var(rng.choice(values, len(values)), ddof=1) for _ in range(2000)], [0.025, 0.975]).tolist() if len(values) > 1 else [None, None]
            clusters = defaultdict(list)
            for row in rows:
                clusters[row['game_id']].append(row['mean_loss'])
            cluster_values = list(clusters.values())
            game_interval = np.quantile([np.var(np.concatenate([cluster_values[index] for index in rng.integers(len(cluster_values), size=len(cluster_values))]), ddof=1)
                                         for _ in range(2000)], [0.025, 0.975]).tolist() if len(cluster_values) > 1 else [None, None]
            variances.append({'year': year, 'band': band, 'player_games': len(values), 'games': len(clusters),
                              'variance': variance, 'bootstrap_low': interval[0], 'bootstrap_high': interval[1],
                              'game_bootstrap_low': game_interval[0], 'game_bootstrap_high': game_interval[1],
                              'sd': float(np.sqrt(variance)) if variance is not None else None})
    outputs = []
    for name, rows in [('learning_pilot_player_games', player_games), ('learning_pilot_variance', variances), ('learning_pilot_stability', stability)]:
        path = Path('data/derived/' + name + '.csv')
        with path.open('w', newline='') as destination:
            writer = csv.DictWriter(destination, fieldnames=list(rows[0]), lineterminator='\n')
            writer.writeheader()
            writer.writerows(rows)
        outputs.append(path)
    config = {'engine': json.loads(Path('data/derived/stockfish_config.json').read_text()),
              'budgets': [25000, 100000], 'primary_window': [9, 40], 'secondary_window': [11, 60],
              'search': 'single-PV screening; same-board shared-root comparison when played move differs; fresh hash each search',
              'bootstrap': '2000 player and game-cluster resamples within each year/band, seed 20261016; cap gives one observation per player-year',
              'total_worker_seconds': sum(item['seconds'] for item in completed),
              'screened_moves': sum(item['screened_moves'] for item in completed),
              'inputs_sha256': {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in inputs},
              'outputs_sha256': {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in outputs},
              'game_outputs': completed,
              'limits': ['Documented-event pool only; variance is conditional on event coverage and pilot budget.',
                         'Bootstrap intervals concern the sampled pool; they omit event-selection and engine-judgement uncertainty.',
                         'Within a year-band each player contributes once; game clusters retain both sampled sides. Cross-band gaps are not estimated.',
                         'No historical trend, band-gap effect, or main sample-size choice is inferred from this restricted pilot.',
                         'Arithmetic mean of move accuracy is not Lichess whole-game accuracy.',
                         'Raw native WDL and CP depend on Stockfish version and search budget.']}
    Path('data/derived/learning_pilot_scoring_config.json').write_text(json.dumps(config, indent=2) + '\n')
    print(len(player_games), 'player-games scored;', round(config['total_worker_seconds']), 'worker-seconds', flush=True)


#%% main
def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--workers', type=int, default=3)
    parser.add_argument('--summarise-only', action='store_true')
    args = parser.parse_args()
    inputs = [Path('data/derived/' + name) for name in ['learning_pilot_pool.jsonl', 'learning_pilot_sample.csv', 'learning_pilot_sample_config.json', 'stockfish_config.json']]
    inputs += [Path(__file__), Path('scripts/pal_css_2005_case.py'), Path('notes/hypotheses.md')]
    config = json.loads(inputs[3].read_text())
    config['pilot_code_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    config['protocol_sha256'] = hashlib.sha256(Path('notes/hypotheses.md').read_bytes()).hexdigest()
    frozen_sample = json.loads(inputs[2].read_text())
    for name, fingerprint in frozen_sample['outputs_sha256'].items():
        assert hashlib.sha256(Path(name).read_bytes()).hexdigest() == fingerprint
    assert hashlib.sha256(Path(config['binary']).read_bytes()).hexdigest() == config['binary_sha256']
    sample = list(csv.DictReader(inputs[1].open()))
    games = {game['game_id']: game for game in (json.loads(line) for line in inputs[0].read_text().splitlines())}
    sides = defaultdict(list)
    for row in sample:
        sides[row['game_id']].append(row)
    Path('data/local/learning_pilot').mkdir(parents=True, exist_ok=True)
    completed = []
    if args.summarise_only:
        completed = [json.loads((Path('data/local/learning_pilot') / (game_id + '_complete.json')).read_text()) for game_id in sorted(sides)]
    else:
        tasks = [(games[game_id], sides[game_id], config) for game_id in sorted(sides)]
        with ProcessPoolExecutor(max_workers=args.workers) as pool:
            for item in pool.map(score_game, tasks):
                completed.append(item)
                if len(completed) % 10 == 0:
                    print(len(completed), '/', len(tasks), 'games scored', flush=True)
    summarise(completed, sample, inputs)


if __name__ == '__main__':
    main()
