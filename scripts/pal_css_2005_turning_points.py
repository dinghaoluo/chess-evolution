'''
Created on 15 October 2026

check the largest apparent deteriorations in the three annotated game scores

@author: Dinghao Luo
'''

#%% imports
import csv
import hashlib
import json

import chess
import chess.engine

from pal_css_2005_case import DATA, ENGINE, result_rows, search


#%% main
def main() -> None:
    #%% select from the complete evaluation trajectories
    with (DATA / 'pal_css_2005_games.csv').open() as source:
        games = {row['source_ordinal']: row for row in csv.DictReader(source)}
    with (DATA / 'pal_css_2005_trajectory.csv').open() as source:
        trajectory = list(csv.DictReader(source))
    selected = []
    for ordinal in ['13', '22', '26']:
        rows = [row for row in trajectory if row['source_ordinal'] == ordinal]
        candidates = []
        for before, after in zip(rows, rows[1:]):
            ply = int(before['ply'])
            played = games[ordinal]['moves_uci'].split()[ply - 1]
            if played == before['move_uci']:
                continue
            sign = 1 if ply % 2 == 1 else -1
            change = sign * (float(after['white_expected_score']) - float(before['white_expected_score']))
            candidates.append({**before, 'played_move': played, 'screened_score_change': change})
        # this is an exploratory screen; a score change alone is not a move loss
        selected += sorted(candidates, key=lambda row: row['screened_score_change'])[:3]


    #%% compare the played move with the screening recommendation
    config_path = DATA / 'pal_css_2005_case_config.json'
    config = json.loads(config_path.read_text())
    assert hashlib.sha256(ENGINE.read_bytes()).hexdigest() == config['binary_sha256']
    results = []
    with chess.engine.SimpleEngine.popen_uci(str(ENGINE)) as engine:
        engine.configure(config['options'])
        for row in selected:
            board = chess.Board(row['initial_fen'])
            for move in row['history_uci'].split():
                board.push_uci(move)
            moves = [board.parse_uci(row[key]) for key in ['played_move', 'move_uci']]
            case_id = 'game' + row['source_ordinal'] + '_ply' + row['ply']
            for nodes in [4_000_000, 16_000_000]:
                infos = search(engine, board, nodes, moves, 2)
                paired = result_rows(infos, board, row['source_ordinal'], case_id, 'turning_pair', nodes)
                for result in paired:
                    result['played_move_uci'] = row['played_move']
                    result['screening_move_uci'] = row['move_uci']
                    result['screened_expected_score_change'] = row['screened_score_change']
                results += paired
            print(case_id, flush=True)
    with (DATA / 'pal_css_2005_turning_points.csv').open('w', newline='') as destination:
        writer = csv.DictWriter(destination, fieldnames=list(results[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(results)


if __name__ == '__main__':
    main()
