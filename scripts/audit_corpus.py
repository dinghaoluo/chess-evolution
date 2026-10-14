'''
Created on 14 October 2026

audit championship sources and classify analytical membership

@author: Dinghao Luo
'''

#%% imports
import csv
import hashlib
from collections import Counter
from pathlib import Path

import chess.pgn


#%% paths
RAW = Path('data/raw/pgnmentor')
DATA = Path('data')


#%% main
with (DATA / 'events.csv').open() as source:
    events = list(csv.DictReader(source))
by_file = {event['source_file']: event for event in events if event['source_file']}
assert set(by_file) == {path.name for path in RAW.glob('*.pgn')}

# first-round pairings from the separate women's title
WOMEN_2001_PAIRS = {
    frozenset(pair) for pair in [
        ('Mohota,N', 'Stepovaia Dianchenko,T'), ('Arakhamia,K', 'Ciuksyte,D'),
        ('Xu Yuanyuan', 'Pina,S'), ('Foisor,C', 'Gu Xiaobing'),
        ('Baginskaite,C', 'Prudnikova,S'), ('Zielinska,Mar', 'Gaprindashvili,N'),
        ('Paehtz,E', 'Radziewicz,I'), ('Kiseleva,N', 'Wang Yu'),
    ]
}

manifest = []
classifications = []
fingerprints = set()
game_id = 0
ply_source = (DATA / 'games.csv').open()
parsed_plies = iter(csv.DictReader(ply_source))

for path in sorted(RAW.glob('*.pgn')):
    event = by_file[path.name]
    notes = ''
    if path.name == 'WorldChamp2018.pgn':
        notes = 'locally repaired record separators; original acquisition hash unavailable'
    elif path.name == 'WorldChamp2023.pgn':
        notes = 'four rapid games added locally; original acquisition hash unavailable'
    manifest.append({
        'source_file': path.name,
        'url': 'https://www.pgnmentor.com/events/' + path.name,
        'supplement_url': event['supplement_url'],
        'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
        'bytes': path.stat().st_size,
        'retrieved_at': '',
        'reviewed_at': '2026-10-14',
        'licence': 'no explicit open-data licence identified',
        'notes': notes,
    })
    file_games = []
    with path.open() as source:
        while (game := chess.pgn.read_game(source)) is not None:
            assert not game.errors, (path.name, game.headers)
            game_id += 1
            ordinal = len(file_games) + 1
            h = game.headers
            moves = list(game.mainline_moves())
            board = game.board()
            for ply, move in enumerate(moves, 1):
                board.push(move)
                parsed = next(parsed_plies)
                assert parsed['game_id'] == str(game_id)
                assert parsed['source_file'] == path.name
                assert parsed['ply'] == str(ply)
                assert parsed['move_uci'] == move.uci()
                assert parsed['fen'] == board.fen()
            fingerprint = (h['White'], h['Black'], tuple(move.uci() for move in moves))
            assert fingerprint not in fingerprints, (path.name, ordinal)
            fingerprints.add(fingerprint)

            game_class = 'classical'
            reason = 'title match or round robin; event evidence'
            reviewed = True
            if event['format'] in ('knockout', 'knockout_then_match'):
                game_class = 'unknown_speed'
                reviewed = False
                reason = 'round and time-control reconciliation pending'
                if path.name == 'FideChamp1999.pgn' and h['Event'] == 'FIDE-Wch k.o.':
                    game_class = 'classical'
                    reviewed = True
                    reason = 'explicit regulation-game event label; 200 records'
                elif path.name == 'FideChamp1999.pgn' and 'g/' in h['Event']:
                    game_class = 'rapid'
                    reviewed = True
                    reason = 'explicit 25+10 or 15+10 event label'
            elif ordinal > int(event['expected_classical_records']):
                game_class = 'rapid'
                reason = 'documented match tiebreak sequence'

            played = True
            membership = 'in_scope' if event['included'] == '1' else 'excluded_non_title'
            evidence_url = event['evidence_url']
            if path.name == 'FideChamp2002.pgn' and frozenset((h['White'], h['Black'])) in WOMEN_2001_PAIRS:
                membership = 'excluded_women_title'
                reason = 'separate championship; included under misleading open-event headers'
                evidence_url = 'https://www.olimpbase.org/~B-FISH/ind-wwcc/wwc2001-wch.html'
            if (path.name, h['Round']) in {
                    ('WorldChamp1972.pgn', '2'), ('WorldChamp2006.pgn', '5')}:
                played = False
                game_class = 'unplayed'
                reason = 'forfeit; movetext is not evidence of play'
            assert moves or not played, (path.name, ordinal)
            accepted = membership == 'in_scope' and played and reviewed
            row = {
                'game_id': game_id,
                'raw_game_id': f'{path.name}:{ordinal}',
                'event_id': event['event_id'],
                'source_file': path.name,
                'source_ordinal': ordinal,
                'round': h['Round'],
                'date': h['Date'],
                'white': h['White'],
                'black': h['Black'],
                'result': h['Result'],
                'plies': len(moves),
                'game_class': game_class,
                'membership': membership,
                'played_on_board': int(played),
                'counts_for_official_score': int(membership == 'in_scope'),
                'accepted_for_analysis': int(accepted),
                'reason': reason if event['included'] == '1' else 'excluded non-title match',
                'evidence_url': evidence_url,
            }
            file_games.append(row)
            classifications.append(row)

    if event['expected_classical_records']:
        expected = int(event['expected_classical_records']) + int(event['expected_rapid_games'])
        assert len(file_games) == expected, (path.name, len(file_games), expected)

assert next(parsed_plies, None) is None
ply_source.close()

for name, rows in [('source_manifest.csv', manifest), ('game_classifications.csv', classifications)]:
    with (DATA / name).open('w', newline='') as destination:
        writer = csv.DictWriter(destination, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


#%% 2002 match completeness
def player_key(name: str) -> str:
    surname, separator, given = name.partition(',')
    return surname.replace(' ', '').lower() + (':' + given.strip()[0].lower() if separator else '')


matches = Counter(
    tuple(sorted([player_key(row['white']), player_key(row['black'])]))
    for row in classifications
    if row['event_id'] == 'fide_2002' and row['membership'] == 'in_scope'
)
with (DATA / 'fide_2002_matches.csv').open() as source:
    documentary_matches = list(csv.DictReader(source))
documentary_pairs = set()
for row in documentary_matches:
    pair = tuple(sorted([player_key(row['player_a']), player_key(row['player_b'])]))
    documentary_pairs.add(pair)
    expected = float(row['score_a']) + float(row['score_b'])
    assert expected.is_integer()
    row['raw_records'] = matches[pair]
    row['missing_records'] = int(expected) - matches[pair]
    assert row['missing_records'] >= 0, pair
assert documentary_pairs == set(matches)
with (DATA / 'fide_2002_matches.csv').open('w', newline='') as destination:
    writer = csv.DictWriter(destination, fieldnames=list(documentary_matches[0]), lineterminator='\n')
    writer.writeheader()
    writer.writerows(documentary_matches)
missing_games = sum(row['missing_records'] for row in documentary_matches)
print(f'2002 open title: {missing_games} missing records against documentary match totals')

accepted_count = sum(row['accepted_for_analysis'] for row in classifications)
print(f'{len(classifications)} raw records; {accepted_count} reviewed, played title games')
