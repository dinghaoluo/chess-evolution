'''
Created on 16 October 2026

compare the timed decisions with Fruit under stated search-speed scenarios

@author: Dinghao Luo
'''

#%% imports
import argparse
import csv
import hashlib
import json
from pathlib import Path

import chess.engine

from engine_ladder import decision_positions, position_board
from pal_css_2005_case import search


#%% main
def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--nodes-per-second', nargs='+', type=int, default=[10000, 100000])
    args = parser.parse_args()
    assert all(speed > 0 for speed in args.nodes_per_second)
    folder = Path('data/derived')
    builds = json.loads((folder / 'engine_builds.json').read_text())
    fruit = next(build for build in builds if build['name'] == 'fruit-2.1')
    modern = next(build for build in builds if build['name'] == 'stockfish-17.1')
    for build in [fruit, modern]:
        assert hashlib.sha256(Path(build['binary']).read_bytes()).hexdigest() == build['binary_sha256']
    with (folder / 'pal_css_clock_games.csv').open() as source:
        games = [row for row in csv.DictReader(source) if row['accepted_for_timing'] == '1']
    with (folder / 'pal_css_move_times.csv').open() as source:
        clocks = {(row['game_id'], row['ply']): row for row in csv.DictReader(source)}
    results = []
    for case in decision_positions()[:16]:
        matching = [game for game in games if game['winners_source_ordinal'] == case['source_ordinal']]
        assert len(matching) <= 1
        seconds = clocks[matching[0]['game_id'], str(case['ply'])]['elapsed_seconds'] if matching else ''
        board = position_board(case)
        for speed in args.nodes_per_second:
            row = {'case_id': case['case_id'], 'elapsed_seconds': seconds,
                   'nominal_nodes_per_second': speed, 'scenario_status': 'uncalibrated_archival_excluded_from_essay', 'status': 'observed_time' if seconds else 'missing_time',
                   'reference_nodes': '', 'reference_search_nodes': '', 'reference_move_uci': '',
                   'played_uci': case['move_uci'], 'differs_from_reference': '',
                   'modern_nodes': 4000000, 'modern_played_expected_score': '',
                   'modern_reference_expected_score': '', 'modern_difference': ''}
            if seconds:
                # no pondering, preparation, parallel engines, or calibration to the team's hardware
                budget = max(1, round(float(seconds) * speed))
                with chess.engine.SimpleEngine.popen_uci(fruit['binary'], timeout=180) as engine:
                    engine.configure(fruit['options'])
                    reference = engine.play(board, chess.engine.Limit(nodes=budget), info=chess.engine.INFO_ALL)
                played = board.parse_uci(case['move_uci'])
                candidates = list(dict.fromkeys([played, reference.move]))
                with chess.engine.SimpleEngine.popen_uci(modern['binary']) as engine:
                    engine.configure(modern['options'])
                    paired = search(engine, board, 4_000_000, candidates, len(candidates))
                values = {}
                for info in paired:
                    wdl = info['wdl'].pov(board.turn)
                    values[info['pv'][0]] = (wdl.wins + wdl.draws / 2) / 1000
                row.update({'reference_nodes': budget, 'reference_search_nodes': reference.info['nodes'],
                            'reference_move_uci': reference.move.uci(), 'differs_from_reference': int(played != reference.move),
                            'modern_played_expected_score': values[played],
                            'modern_reference_expected_score': values[reference.move],
                            'modern_difference': values[played] - values[reference.move]})
            results.append(row)
        print(case['case_id'], flush=True)
    with (folder / 'reference_comparisons.csv').open('w', newline='') as destination:
        writer = csv.DictWriter(destination, fieldnames=list(results[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(results)
    paths = [Path('data/curated/pal_css_2005_decisions.csv'), folder / 'pal_css_2005_games.csv',
             folder / 'pal_css_clock_games.csv', folder / 'pal_css_move_times.csv']
    metadata = {'reference': fruit, 'modern': modern, 'nominal_nodes_per_second': args.nodes_per_second,
                'modern_nodes': 4000000, 'hash_policy': 'fresh process for each search; full game history',
                'population': 'sixteen participant-selected decisions; missing move times retained explicitly',
                'status': 'uncalibrated archival scenarios; excluded from the essay on 16 October 2026',
                'interpretation': 'deviation from a reference engine under assumed speeds; neither the team engines nor equal historical compute; modern WDL differences are model outputs',
                'inputs_sha256': {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths},
                'output_sha256': hashlib.sha256((folder / 'reference_comparisons.csv').read_bytes()).hexdigest()}
    (folder / 'reference_comparisons_config.json').write_text(json.dumps(metadata, indent=2) + '\n')


if __name__ == '__main__':
    main()
