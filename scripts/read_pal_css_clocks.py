'''
Created on 15 October 2026

read the surviving PAL/CSS clocks across tournament stages and editions

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


#%% sources
DATA = Path('data/derived')
CACHE = Path('cache/sources')
# keep stages separate: the 2005 qualifier had a much shorter time control
SOURCES = [
    ('pal_2005_qualifier', 1, 'qualifier', 1500, 10, '2005/games/freestyle-qual.zip',
     'eleven-qualify-for-main-freestyle-tournament', 'swiss'),
    ('pal_2005_main', 1, 'main', 3600, 15, '2005/games/freestyle-main.zip',
     'hydra-mies-the-quarter-finals-of-freestyle-tournament', 'swiss'),
    ('pal_final', 1, 'knockout', 3600, 15, '2005/games/freestyle-final.zip',
     'dark-horse-zacks-wins-freestyle-che-tournament', 'knockout'),
    ('pal_2006_final2', 2, 'final', 2700, 5, '2006/games/freestyle02.zip',
     'zor-champ-wins-freestyle-tournament', 'round_robin'),
    ('pal_2006_final4', 4, 'final', 3600, None, '2006/games/freestyle4f.zip',
     'the-freestyle-champion-is-xakru-dammit-', 'round_robin'),
    ('pal_2007_final5', 5, 'final', 3600, 15, '2007/games/freestyle-final5.zip',
     'freestyle-che-teaching-an-engine-how-to-fly', 'round_robin'),
    ('pal_2007_final6', 6, 'final', 3600, 15, '2007/games/freestyle06f.zip',
     'rajlich-wins-sixth-pal-c-freestyle-tournament', 'round_robin'),
]


#%% main
def main() -> None:
    frozen = {row['file']: row['sha256'] for row in json.loads(Path('data/curated/source_files.json').read_text())}
    with (DATA / 'pal_css_2005_games.csv').open() as source:
        winners = list(csv.DictReader(source))
    with (Path('data/curated') / 'pal_css_game_reviews.csv').open() as source:
        reviews = {row['game_id']: row for row in csv.DictReader(source)}
    additional = CACHE / 'pal_2005_neverfail.zip'
    if not additional.exists():
        additional.write_bytes(urlopen('https://en.chessbase.com/portals/4/files/news/2005/games/neverfail.zip', timeout=60).read())
    clocks, scores, players, sources = [], [], [], []
    for name, edition, stage, base, increment, archive_path, page, format_name in SOURCES:
        archive = CACHE / (name + '.zip')
        archive_url = 'https://en.chessbase.com/portals/4/files/news/' + archive_path
        if not archive.exists():
            archive.write_bytes(urlopen(archive_url, timeout=60).read())
        assert hashlib.sha256(archive.read_bytes()).hexdigest() == frozen[archive.name], archive.name
        with ZipFile(archive) as source:
            member = next(item for item in source.namelist() if item.lower().endswith('.pgn'))
            raw = source.read(member)
        pgn = io.StringIO(raw.decode('latin-1'))
        games = list(iter(lambda: chess.pgn.read_game(pgn), None))
        source_rows = []
        for ordinal, game in enumerate(games, 1):
            assert not game.errors, (name, ordinal)
            nodes = list(game.mainline())
            moves = [node.move.uci() for node in nodes]
            game_id = f'{name}:{ordinal}'
            tiebreak = 'TB' in game.headers['Event']
            matches = [row for row in winners if edition == 1 and row['date'] == game.headers['Date']
                       and moves[:len(row['moves_uci'].split())] == row['moves_uci'].split()]
            assert len(matches) <= 1
            if matches:
                assert game.headers['Result'] == matches[0]['result']
            row = {'game_id': game_id, 'edition': edition, 'year': game.headers['Date'][:4],
                   'date': game.headers['Date'], 'stage': stage, 'format': format_name,
                   'round': game.headers['Round'], 'white': game.headers['White'], 'black': game.headers['Black'],
                   'result': game.headers['Result'], 'plies': len(moves), 'tiebreak': int(tiebreak),
                   'initial_seconds': base if not tiebreak else '', 'increment_seconds': increment if not tiebreak else '',
                   'winners_source_ordinal': matches[0]['source_ordinal'] if matches else '',
                   'missing_times': sum(node.emt() is None for node in nodes),
                   'accepted_for_timing': reviews.get(game_id, {}).get('accepted_for_timing', '1'),
                   'source_issue': reviews.get(game_id, {}).get('reason', '')}
            scores.append(row)
            source_rows.append(row)
            elapsed = {True: 0, False: 0}
            missing = {True: 0, False: 0}
            for node in nodes:
                side = node.ply() % 2 == 1
                seconds = node.emt()
                if seconds is None:
                    missing[side] += 1
                else:
                    assert seconds >= 0, (game_id, node.ply())
                    elapsed[side] += seconds
                known_control = not tiebreak and increment is not None
                clocks.append({'game_id': game_id, 'ply': node.ply(), 'move_uci': node.move.uci(),
                               'move_san': node.san(), 'elapsed_seconds': seconds,
                               'white_elapsed_lower_seconds': elapsed[True],
                               'black_elapsed_lower_seconds': elapsed[False],
                               'white_missing_times': missing[True], 'black_missing_times': missing[False],
                               'white_clock_upper_seconds': base + increment * ((node.ply() + 1) // 2) - elapsed[True] if known_control else '',
                               'black_clock_upper_seconds': base + increment * (node.ply() // 2) - elapsed[False] if known_control else ''})
            if (row['accepted_for_timing'] == '0' or tiebreak or not nodes
                    or game.headers['Result'] not in ['1-0', '0-1', '1/2-1/2']):
                continue
            for side in [True, False]:
                own = [node for node in nodes if node.turn() != side]
                times = {((node.ply() + 1) // 2): node.emt() for node in own}
                result = {'1-0': int(side), '0-1': int(not side), '1/2-1/2': 0.5}[row['result']]
                player = {key: row[key] for key in ['game_id', 'edition', 'year', 'date', 'stage', 'format',
                                                  'round', 'initial_seconds', 'winners_source_ordinal']}
                player.update({'side': 'white' if side else 'black',
                               'player': row['white' if side else 'black'], 'score': result,
                               'observed_moves': min(30, len(own))})
                for label, fraction in [('2p5', 0.025), ('5', 0.05), ('10', 0.1)]:
                    threshold = base * fraction
                    first = next((move for move, elapsed in times.items()
                                  if move <= 30 and elapsed is not None and elapsed >= threshold), None)
                    player[f'first_{label}pct_move'] = first or ''
                    player[f'first_{label}pct_censored'] = int(first is None)
                    player[f'first_{label}pct_missing_before'] = sum(elapsed is None for move, elapsed in times.items()
                                                                          if move <= (first or 30))
                for end in [10, 17, 20]:
                    window = [times.get(move) for move in range(1, end + 1)]
                    player[f'elapsed_first_{end}_seconds'] = sum(window) if all(t is not None for t in window) else ''
                players.append(player)
        if format_name == 'round_robin':
            # the fifth archive spells 'The wizard of Os' with two capitalisations
            names = {row[key].casefold() for row in source_rows for key in ['white', 'black']}
            pairings = [tuple(sorted((row['white'].casefold(), row['black'].casefold()))) for row in source_rows]
            assert len(games) == len(names) * (len(names) - 1) // 2
            assert len(pairings) == len(set(pairings))
        sources.append({'name': name, 'edition': edition, 'stage': stage,
                        'archive_url': archive_url,
                        'report_url': 'https://en.chessbase.com/post/' + page,
                        'archive_sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
                        'pgn_sha256': hashlib.sha256(raw).hexdigest(), 'games': len(games),
                        'regular_games': sum(not row['tiebreak'] for row in source_rows),
                        'excluded_attempts': [row['game_id'] for row in source_rows if row['accepted_for_timing'] == '0'],
                        'missing_times': sum(row['missing_times'] for row in source_rows)})
    for name, rows in [('pal_css_clock_games.csv', scores), ('pal_css_move_times.csv', clocks),
                       ('pal_css_timing.csv', players)]:
        with (DATA / name).open('w', newline='') as destination:
            writer = csv.DictWriter(destination, fieldnames=list(rows[0]), lineterminator='\n')
            writer.writeheader()
            writer.writerows(rows)
    metadata = {
        'retrieved_at': '2026-10-15', 'sources': sources,
        'population': 'surviving linked archives, not a complete census of all eight editions',
        'times': 'PGN %emt; cumulative elapsed lower bounds and remaining-clock upper bounds after missing times; clocks omitted for unresolved controls and tiebreaks',
        'long_think': 'first move through move 30 using at least 5 percent of the initial time; 2.5 and 10 percent retained',
        '2005_time_controls': 'qualifier 25m+10s; main and regular knockout 60m+15s',
        '2005_rules_url': 'https://en.chessbase.com/post/the-20-000-free-for-all-che-tournament',
        '2006_edition4': 'announcement says 60m+15s; retrospective report says 60m+30s; increment left unresolved',
        'unavailable': ['2005 quarter-final linked archive returns 404',
                        'third-edition archive linked on computerschach.de not recovered',
                        'seventh and eighth editions have different or unavailable archival coverage'],
        'licence': 'no explicit redistribution licence found; raw PGNs and annotations kept locally; derived timings retained',
        'review_sha256': hashlib.sha256((Path('data/curated') / 'pal_css_game_reviews.csv').read_bytes()).hexdigest(),
        'additional_2005_account': {
            'player': 'Konstantin Orfenov, Neverfail', 'games': 8,
            'archive_url': 'https://en.chessbase.com/portals/4/files/news/2005/games/neverfail.zip',
            'archive_sha256': hashlib.sha256((CACHE / 'pal_2005_neverfail.zip').read_bytes()).hexdigest(),
            'review': 'all eight scores and annotations; few notes identify who selected a move, so no live human override inferred',
        },
    }
    (DATA / 'pal_css_clock_sources.json').write_text(json.dumps(metadata, indent=2) + '\n')
    print(len(scores), 'archived games;', len(players), 'regular game sides;',
          len({row['winners_source_ordinal'] for row in scores if row['winners_source_ordinal']}), 'timed 2005 winners scores')


if __name__ == '__main__':
    main()
