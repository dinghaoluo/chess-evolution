'''
Created on 15 October 2026

join recent championship clocks to the audited game scores

@author: Dinghao Luo
'''

#%% imports
import csv
import hashlib
import io
import itertools
import json
from pathlib import Path
from urllib.request import urlopen

import chess.pgn


#%% sources
DATA = Path('data')
CACHE = Path('.venv/research-sources')
TOURNAMENTS = {2021: 'A6snaCgb', 2023: 'lrdHUzyS', 2024: 'n3yHJI5Y'}


#%% main
def main() -> None:
    with (DATA / 'game_classifications.csv').open() as source:
        accepted = {row['game_id']: row for row in csv.DictReader(source)
                    if row['accepted_for_analysis'] == '1' and row['game_class'] == 'classical'
                    and row['event_id'] in [f'world_{year}' for year in TOURNAMENTS]}
    with (DATA / 'games.csv').open() as source:
        moves = {game_id: [row['move_uci'] for row in rows]
                 for game_id, rows in itertools.groupby(csv.DictReader(source), lambda r: r['game_id'])
                 if game_id in accepted}
    output = []
    sources = []
    for year, tournament_id in TOURNAMENTS.items():
        url = f'https://lichess.org/api/broadcast/{tournament_id}.pgn'
        path = CACHE / f'wcc_{year}_all.pgn'
        if not path.exists():
            path.write_bytes(urlopen(url, timeout=30).read())
        raw = path.read_bytes()
        pgn = io.StringIO(raw.decode())
        games = list(iter(lambda: chess.pgn.read_game(pgn), None))
        used = []
        missing = []
        for ordinal, game in enumerate(games, 1):
            assert not game.errors
            # rapid tiebreaks repeat round numbers in the same download
            if not game.headers['TimeControl'].startswith('40/7200:'):
                continue
            candidates = [game_id for game_id, row in accepted.items()
                          if row['event_id'] == f'world_{year}'
                          and row['round'].split('.')[0] == game.headers['Round']]
            assert len(candidates) == 1
            game_id = candidates[0]
            assert [move.uci() for move in game.mainline_moves()] == moves[game_id], game_id
            assert game.headers['Result'] == accepted[game_id]['result']
            used.append(game_id)
            previous = {True: 7200, False: 7200}
            for node in game.mainline():
                # all three matches have two hours and no increment before move 40
                if node.ply() > 80:
                    break
                side = not node.turn()
                clock = node.clock()
                seconds = previous[side] - clock if clock is not None and previous[side] is not None else None
                # the extra period can be credited on the move-40 clock display
                if (node.ply() + 1) // 2 == 40:
                    seconds = None
                if seconds is not None:
                    assert seconds >= 0, (year, game.headers['Round'], node.ply(), seconds)
                if clock is None:
                    missing.append({'game_id': game_id, 'ply': node.ply()})
                output.append({
                    'game_id': game_id, 'year': year, 'round': game.headers['Round'],
                    'source_ordinal': ordinal, 'ply': node.ply(), 'move_san': node.san(),
                    'move_uci': node.move.uci(), 'clock_seconds': clock, 'elapsed_seconds': seconds,
                    'legal_moves_before': node.parent.board().legal_moves.count(),
                    'game_url': game.headers['GameURL'],
                })
                previous[side] = clock
        assert len(used) == len(set(used)) == sum(row['event_id'] == f'world_{year}' for row in accepted.values())
        sources.append({'year': year, 'url': url, 'cache_file': path.name,
                        'sha256': hashlib.sha256(raw).hexdigest(), 'downloaded_games': len(games),
                        'accepted_classical_games': len(used), 'time_control': games[0].headers['TimeControl'],
                        'missing_clocks_through_move_40': missing})
    with (DATA / 'championship_clocks.csv').open('w', newline='') as destination:
        writer = csv.DictWriter(destination, fieldnames=list(output[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(output)
    metadata = {
        'retrieved_at': '2026-10-15', 'sources': sources,
        'population': 'every audited classical game in the 2021, 2023 and 2024 title matches',
        'matching': 'round and event, followed by equality of the complete main line and result',
        'elapsed_time': 'difference between successive clocks of the same player; missing neighbours stay missing',
        'move_40': 'clock retained; elapsed time omitted because the next period may already have been credited',
        'older_matches': 'official linked studies for 2013, 2014, 2016 and 2018 contain no move clocks',
        'licence': 'public broadcast export; raw annotations kept locally, derived clock measurements only',
        'help_url': 'https://lichess.org/broadcast/help',
    }
    (DATA / 'championship_clock_sources.json').write_text(json.dumps(metadata, indent=2) + '\n')
    print(len(accepted), 'classical games;', len(output), 'opening clock records')


if __name__ == '__main__':
    main()
