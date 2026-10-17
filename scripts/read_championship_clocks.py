'''
Created on 15 October 2026

read classical title-match clocks from the frozen Lichess broadcasts

@author: Dinghao Luo
'''

#%% imports
import csv
import hashlib
import io
import json
from pathlib import Path

import chess.pgn


#%% main
def main() -> None:
    output, sources = [], []
    inputs = json.loads(Path('data/curated/source_files.json').read_text())
    for year, expected in [(2021, 11), (2023, 14), (2024, 14)]:
        name = f'wcc_{year}_all.pgn'
        source = next(row for row in inputs if row['file'] == name)
        raw = (Path('cache/sources') / name).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == source['sha256']
        pgn = io.StringIO(raw.decode())
        games = list(iter(lambda: chess.pgn.read_game(pgn), None))
        used, missing = [], []
        for ordinal, game in enumerate(games, 1):
            assert not game.errors
            if not game.headers['TimeControl'].startswith('40/7200:'):
                continue
            round_number = int(game.headers['Round'])
            game_id = f'wcc_{year}:{round_number}'
            used.append(round_number)
            previous = {True: 7200, False: 7200}
            for node in game.mainline():
                if node.ply() > 80:
                    break
                side = not node.turn()
                clock = node.clock()
                seconds = previous[side] - clock if clock is not None and previous[side] is not None else None
                if (node.ply() + 1) // 2 == 40:
                    seconds = None
                if seconds is not None:
                    assert seconds >= 0, (game_id, node.ply())
                if clock is None:
                    missing.append({'game_id': game_id, 'ply': node.ply()})
                output.append({'game_id': game_id, 'year': year, 'round': round_number,
                               'source_ordinal': ordinal, 'ply': node.ply(), 'move_san': node.san(),
                               'move_uci': node.move.uci(), 'clock_seconds': clock, 'elapsed_seconds': seconds,
                               'game_url': game.headers['GameURL']})
                previous[side] = clock
        assert sorted(used) == list(range(1, expected + 1))
        sources.append({**source, 'classical_games': expected, 'downloaded_games': len(games),
                        'missing_clocks_through_move_40': missing})
    with Path('data/derived/championship_clocks.csv').open('w', newline='') as destination:
        writer = csv.DictWriter(destination, fieldnames=list(output[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(output)
    metadata = {'sources': sources, 'population': 'all classical games in the 2021, 2023, and 2024 title matches',
                'identity': 'broadcast year and unique classical round; main lines read from that broadcast, without an independent score join',
                'elapsed_time': 'same-player clock difference; missing neighbours stay missing; move forty omitted because the next period may be credited'}
    Path('data/derived/championship_clock_sources.json').write_text(json.dumps(metadata, indent=2) + '\n')


if __name__ == '__main__':
    main()
