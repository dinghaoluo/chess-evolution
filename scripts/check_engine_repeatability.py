'''
Created on 16 October 2026

repeat a saved position in fresh engine processes at the same node budget

@author: Dinghao Luo
'''

#%% imports
import hashlib
import json
from pathlib import Path

import chess.engine

from engine_ladder import decision_positions, position_board


#%% main
def main() -> None:
    builds = json.loads(Path('data/derived/engine_builds.json').read_text())
    builds += json.loads(Path('data/derived/nielsen_engine_builds.json').read_text())
    case = decision_positions()[0]
    board = position_board(case)
    results = []
    for build in builds:
        assert hashlib.sha256(Path(build['binary']).read_bytes()).hexdigest() == build['binary_sha256']
        runs = []
        for _ in range(2):
            with chess.engine.SimpleEngine.popen_uci(build['binary']) as engine:
                engine.configure(build['options'])
                result = engine.play(board, chess.engine.Limit(nodes=250000), info=chess.engine.INFO_ALL)
            score = result.info['score'].pov(board.turn)
            runs.append({'move_uci': result.move.uci(), 'mover_cp': score.score(), 'mover_mate': score.mate(),
                         'nodes': result.info['nodes'], 'depth': result.info['depth']})
        results.append({'engine': build['name'], 'runs': runs,
                        'exact_search_repeatable': runs[0] == runs[1],
                        'move_and_score_repeatable': all(runs[0][key] == runs[1][key]
                            for key in ['move_uci', 'mover_cp', 'mover_mate'])})
    output = {'case_id': case['case_id'], 'initial_fen': case['initial_fen'], 'history_uci': case['history_uci'],
              'node_budget': 250000, 'engines': builds, 'results': results,
              'limits': ['One selected position, two fresh processes per engine, on this build and machine.',
                         'Requested node limits may overshoot; actual-node differences can prevent exact repeatability.',
                         'This is a repeatability check, without validation of the build against official bench signatures.'],
              'inputs_sha256': {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in [
                  Path('data/curated/pal_css_2005_decisions.csv'), Path('data/derived/engine_builds.json'),
                  Path('data/derived/nielsen_engine_builds.json'), Path(__file__)]}}
    Path('data/derived/engine_repeatability.json').write_text(json.dumps(output, indent=2) + '\n')
    print(sum(row['exact_search_repeatable'] for row in results), 'of', len(builds),
          'engines repeated exactly;', sum(row['move_and_score_repeatable'] for row in results), 'repeated move and score')


if __name__ == '__main__':
    main()
