'''
Created on 15 October 2026

recover recorded move times from the contemporary final-game archive

@author: Dinghao Luo
'''

#%% imports
import csv
import hashlib
import io
import json
from pathlib import Path
from urllib.request import urlopen
from zipfile import ZipFile

import chess.pgn


#%% source
DATA = Path('data')
CACHE = Path('.venv/research-sources')
URL = 'https://en.chessbase.com/portals/4/files/news/2005/games/freestyle-final.zip'
#%% main
def main() -> None:
    archive = CACHE / 'pal_final.zip'
    if not archive.exists():
        archive.write_bytes(urlopen(URL, timeout=60).read())
    archive_hash = hashlib.sha256(archive.read_bytes()).hexdigest()
    assert archive_hash == 'a397a6d08288d80c12280b08e3a38733b856e9e0946b9cdf255933ee4b94cf3c'
    with ZipFile(archive) as source:
        raw = source.read('freestyle-final.pgn')
    with io.StringIO(raw.decode('latin-1')) as pgn:
        games = list(iter(lambda: chess.pgn.read_game(pgn), None))
    assert len(games) == 22 and all(not game.errors for game in games)
    with (DATA / 'pal_css_2005_games.csv').open() as source:
        winners_games = list(csv.DictReader(source))


    #%% score matching and clocks
    rows = []
    matches = []
    for ordinal, game in enumerate(games, 1):
        moves = [move.uci() for move in game.mainline_moves()]
        # the winners' archive stops before the timed score in two games
        matching = [row for row in winners_games
                    if moves[:len(row['moves_uci'].split())] == row['moves_uci'].split()]
        if not matching:
            continue
        assert len(matching) == 1
        winner = matching[0]
        assert game.headers['Result'] == winner['result']
        assert game.headers['Date'] == winner['date']
        matches.append({
            'source_ordinal': winner['source_ordinal'], 'clock_source_ordinal': ordinal,
            'winners_plies': len(winner['moves_uci'].split()), 'timed_plies': len(moves),
        })
        elapsed = {True: 0, False: 0}
        missing = {True: 0, False: 0}
        for node in game.mainline():
            ply = node.ply()
            side = ply % 2 == 1
            seconds = node.emt()
            if seconds is None:
                missing[side] += 1
            else:
                elapsed[side] += seconds
            # missing elapsed time gives an upper bound, never an imputed clock
            white_clock = 3600 + 15 * ((ply + 1) // 2) - elapsed[True]
            black_clock = 3600 + 15 * (ply // 2) - elapsed[False]
            rows.append({
                'source_ordinal': winner['source_ordinal'], 'clock_source_ordinal': ordinal,
                'ply': ply, 'move_uci': node.move.uci(), 'move_san': node.san(),
                'elapsed_seconds': seconds,
                'white_clock_upper_seconds': white_clock, 'black_clock_upper_seconds': black_clock,
                'white_missing_times': missing[True], 'black_missing_times': missing[False],
            })
    with (DATA / 'pal_css_2005_clocks.csv').open('w', newline='') as destination:
        writer = csv.DictWriter(destination, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
    metadata = json.loads((DATA / 'pal_css_2005_sources.json').read_text())
    metadata['clocks'] = {
        'report_url': 'https://en.chessbase.com/post/dark-horse-zacks-wins-freestyle-che-tournament',
        'archive_url': URL, 'retrieved_at': '2026-10-15',
        'archive_sha256': archive_hash, 'pgn_sha256': hashlib.sha256(raw).hexdigest(),
        'archive_games': len(games), 'matched_games': matches,
        'field': 'PGN %emt, elapsed seconds for each move; not wall-clock timestamps',
        'clock_reconstruction': '3600 seconds plus 15 seconds per move, from the reported time control',
        'time_control_source': '60m + 15s in winners’ headers for games 20–23 and 26–27; same final-match control applied to 24–25, whose headers omit it',
        'score_completeness': 'timed scores continue beyond the winners’ scores in games 22 and 24; both versions are preserved',
        'missing_times': [{'source_ordinal': row['source_ordinal'], 'ply': row['ply']}
                          for row in rows if row['elapsed_seconds'] is None],
        'clock_limit': 'upper bounds after a missing time; no lag or server corrections available',
        'licence': 'no explicit redistribution licence identified; raw PGN retained locally',
    }
    (DATA / 'pal_css_2005_sources.json').write_text(json.dumps(metadata, indent=2) + '\n')
    print(len(matches), 'matched games;', len(rows), 'move times')


if __name__ == '__main__':
    main()
