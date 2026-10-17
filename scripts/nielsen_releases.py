'''
Created on 16 October 2026

bracket the first tested release selecting each Nielsen move

@author: Dinghao Luo
'''

#%% imports
import csv
import hashlib
import json
from pathlib import Path

import chess.engine

from engine_ladder import BUDGETS, decision_positions, position_board, score_candidates


#%% main
def main() -> None:
    folder = Path('data/derived')
    cases = [case for case in decision_positions() if case['case_id'].startswith('nielsen')]
    config = json.loads((folder / 'engine_ladder_config.json').read_text())
    assert hashlib.sha256((folder / 'engine_ladder.csv').read_bytes()).hexdigest() == config['output_sha256']
    with (folder / 'engine_ladder.csv').open() as source:
        rows = [row for row in csv.DictReader(source) if row['case_id'].startswith('nielsen')]
    builds = json.loads((folder / 'nielsen_engine_builds.json').read_text())
    for build in builds:
        assert build['bench_nodes'] == build['expected_bench_nodes']
        assert hashlib.sha256(Path(build['binary']).read_bytes()).hexdigest() == build['binary_sha256']
        for case in cases:
            board = position_board(case)
            for budget in BUDGETS:
                with chess.engine.SimpleEngine.popen_uci(build['binary']) as engine:
                    engine.configure(build['options'])
                    result = engine.play(board, chess.engine.Limit(nodes=budget), info=chess.engine.INFO_ALL)
                score = result.info['score'].pov(board.turn)
                row = {'case_id': case['case_id'], 'engine': build['name'], 'release_year': build['year'],
                       'node_budget': budget, 'search_nodes': result.info['nodes'], 'depth': result.info['depth'],
                       'played_uci': case['move_uci'], 'recommended_uci': result.move.uci(),
                       'recommended_san': board.san(result.move), 'matches_played': int(result.move.uci() == case['move_uci']),
                       'mover_cp': score.score(), 'mover_mate': score.mate()}
                rows.append(score_candidates(build, board, row))
        print(build['name'], 'Nielsen positions checked', flush=True)
    rows.sort(key=lambda row: (row['case_id'], int(row['node_budget']), int(row['release_year']),
                              int(row['engine'].split('-')[1].split('.')[0])))
    output = folder / 'nielsen_releases.csv'
    with output.open('w', newline='') as destination:
        writer = csv.DictWriter(destination, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
    summary = []
    for case in cases:
        for budget in BUDGETS:
            own = [row for row in rows if row['case_id'] == case['case_id'] and int(row['node_budget']) == budget]
            first = next((i for i, row in enumerate(own) if int(row['matches_played'])), None)
            summary.append({'case_id': case['case_id'], 'node_budget': budget,
                            'first_matching_tested_release': own[first]['engine'] if first is not None else '',
                            'previous_tested_release': own[first - 1]['engine'] if first else '',
                            'later_disagreements': ' '.join(row['engine'] for row in own[first + 1:] if not int(row['matches_played'])) if first is not None else ''})
    summary_file = folder / 'nielsen_release_summary.csv'
    with summary_file.open('w', newline='') as destination:
        writer = csv.DictWriter(destination, fieldnames=list(summary[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(summary)
    inputs = [folder / 'engine_ladder.csv', folder / 'engine_ladder_config.json', folder / 'nielsen_engine_builds.json',
              Path('data/curated/nielsen_engine_sources.json'), folder / 'decision_positions.csv']
    limits = ['Two participant-selected positions, full source-game history, fresh processes, three requested node budgets.',
              'First tested release; sparse releases and budget dependence prevent a date for human advantage.',
              'Unrestricted move selection and separate candidate scores answer different questions; near-equal is within 20 cp.',
              'Fruit candidate restriction is unavailable; centipawn scales and costs per node differ between engines.']
    metadata = {'inputs_sha256': {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in inputs},
                'outputs_sha256': {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in [output, summary_file]},
                'budgets': BUDGETS, 'builds': builds, 'limits': limits}
    (folder / 'nielsen_releases_config.json').write_text(json.dumps(metadata, indent=2) + '\n')
    panel = {'title': 'Nielsen moves across the tested releases', 'cases': cases, 'searches': rows, 'summary': summary,
             'limits': limits, 'inputs_sha256': {str(output): hashlib.sha256(output.read_bytes()).hexdigest(),
                                                str(summary_file): hashlib.sha256(summary_file.read_bytes()).hexdigest()}}
    Path('panels/nielsen_releases.json').write_text(json.dumps(panel, indent=2) + '\n')


if __name__ == '__main__':
    main()
