'''
Created on 14 October 2026

check championship game lists and playing formats

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
with (DATA / 'knockout_formats.csv').open() as source:
    formats = {(row['event_id'], int(row['round'])): row for row in csv.DictReader(source)}

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
        'reviewed_at': '2026-10-15',
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
            if event['format'] in ('knockout', 'knockout_then_match'):
                # time controls are often missing from the headers
                round_number, game_number = map(int, h['Round'].split('.'))
                rule = formats[event['event_id'], round_number]
                regulation = int(rule['regulation_limit'])
                rapid = int(rule['rapid_limit'])
                game_class = ('classical' if game_number <= regulation else
                              'rapid' if game_number <= regulation + rapid else 'blitz')
                reason = 'documented regulation and rapid stages; later slots are blitz or draw odds'
                if path.name == 'FideChamp1999.pgn':
                    labelled_class = ('classical' if h['Event'] == 'FIDE-Wch k.o.' else
                                      'rapid' if 'g/' in h['Event'] else 'blitz')
                    assert game_class == labelled_class, (ordinal, h)
            elif ordinal > int(event['expected_classical_records']):
                game_class = 'rapid'
                reason = 'documented match tiebreak sequence'

            played = True
            membership = 'in_scope' if event['included'] == '1' else 'excluded_non_title'
            evidence_url = event['evidence_url']
            if event['format'] in ('knockout', 'knockout_then_match'):
                evidence_url = rule['evidence_url']
            if path.name == 'FideChamp2002.pgn' and frozenset((h['White'], h['Black'])) in WOMEN_2001_PAIRS:
                membership = 'excluded_women_title'
                reason = 'separate championship; included under misleading open-event headers'
                evidence_url = 'https://www.olimpbase.org/~B-FISH/ind-wwcc/wwc2001-wch.html'
            elif path.name == 'FideChamp2000.pgn' and ordinal == 235:
                membership = 'excluded_duplicate_version'
                reason = 'alternative score of record 231; identical first 53 plies, rejoins at ply 60'
            if (path.name, h['Round']) in {
                    ('WorldChamp1972.pgn', '2'), ('WorldChamp2006.pgn', '5')}:
                played = False
                game_class = 'unplayed'
                reason = 'forfeit; movetext is not evidence of play'
            assert moves or not played, (path.name, ordinal)
            accepted = membership == 'in_scope' and played and game_class in ('classical', 'rapid')
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
classical_slots = {}
classical_scores = Counter()
for row in classifications:
    if row['event_id'] != 'fide_2002' or row['membership'] != 'in_scope' or row['game_class'] != 'classical':
        continue
    pair = tuple(sorted([player_key(row['white']), player_key(row['black'])]))
    slot = int(row['round'].split('.')[1])
    assert slot not in classical_slots.setdefault(pair, set()), (pair, slot)
    classical_slots[pair].add(slot)
    white_score = {'1-0': 1, '0-1': 0, '1/2-1/2': 0.5}[row['result']]
    classical_scores[pair, player_key(row['white'])] += white_score
    classical_scores[pair, player_key(row['black'])] += 1 - white_score
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
    regulation_games = {6: 4, 7: 8}.get(int(row['round']), 2)
    # the final ended before its last scheduled game
    expected_classical = min(regulation_games, int(expected))
    assert classical_slots[pair] == set(range(1, expected_classical + 1)), pair
    for player, score in [('player_a', 'score_a'), ('player_b', 'score_b')]:
        regulation_score = regulation_games / 2 if expected > regulation_games else float(row[score])
        assert classical_scores[pair, player_key(row[player])] == regulation_score, pair
    row['missing_classical_records'] = 0
    row['missing_tiebreak_records'] = row['missing_records']
assert documentary_pairs == set(matches)
with (DATA / 'fide_2002_matches.csv').open('w', newline='') as destination:
    writer = csv.DictWriter(destination, fieldnames=list(documentary_matches[0]), lineterminator='\n')
    writer.writeheader()
    writer.writerows(documentary_matches)
missing_games = sum(row['missing_records'] for row in documentary_matches)
print(f'2002 open title: {missing_games} missing records against documentary match totals')

accepted_count = sum(row['accepted_for_analysis'] for row in classifications)
print(f'{len(classifications)} raw records; {accepted_count} reviewed, played title games')


#%% remaining knockout pairings
with (DATA / 'player_aliases.csv').open() as source:
    aliases = {(row['event_id'], player_key(row['source_name'])): player_key(row['canonical_name'])
               for row in csv.DictReader(source)}


def canonical_player(event_id: str, name: str) -> str:
    return aliases.get((event_id, player_key(name)), player_key(name))


def pairing_key(event_id: str, a: str, b: str) -> tuple[str, str]:
    return tuple(sorted(canonical_player(event_id, name) for name in [a, b]))


with (DATA / 'knockout_matches.csv').open() as source:
    pairings = list(csv.DictReader(source))
matched_games = set()
for match in pairings:
    event_id = match['event_id']
    pair = pairing_key(event_id, match['player_a'], match['player_b'])
    records = [row for row in classifications if row['event_id'] == event_id
               and row['membership'] == 'in_scope'
               and pairing_key(event_id, row['white'], row['black']) == pair]
    matched_games.update(row['game_id'] for row in records)
    match['raw_records'] = len(records)
    match['missing_records'] = int(match['expected_played_records']) - len(records)
    classical = [row for row in records if row['game_class'] == 'classical']
    slots = [int(row['round'].split('.')[1]) for row in classical]
    assert len(slots) == len(set(slots)), match
    match['raw_classical_slots'] = len(slots)
    match['missing_classical_records'] = int(match['expected_classical_records']) - len(slots)
    assert match['missing_records'] >= 0 and match['missing_classical_records'] >= 0, match
    assert all(int(row['round'].split('.')[0]) == int(match['round']) for row in records)
    if match['missing_classical_records'] == 0 and not int(match['walkover']):
        assert set(slots) == set(range(1, len(slots) + 1)), match
        score_a = sum({'1-0': 1, '0-1': 0, '1/2-1/2': 0.5}[row['result']]
                      if canonical_player(event_id, row['white']) == canonical_player(event_id, match['player_a'])
                      else 1 - {'1-0': 1, '0-1': 0, '1/2-1/2': 0.5}[row['result']]
                      for row in classical)
        expected_a = (int(match['regulation_limit']) / 2
                      if int(match['expected_played_records']) > int(match['regulation_limit'])
                      else float(match['score_a']))
        assert score_a == expected_a, match
assert matched_games == {row['game_id'] for row in classifications
                         if row['event_id'].startswith('fide_') and row['event_id'] in
                         {match['event_id'] for match in pairings} and row['membership'] == 'in_scope'}
with (DATA / 'knockout_matches.csv').open('w', newline='') as destination:
    writer = csv.DictWriter(destination, fieldnames=list(pairings[0]), lineterminator='\n')
    writer.writeheader()
    writer.writerows(pairings)
missing_games = sum(int(row['missing_records']) for row in pairings)
missing_classical = sum(int(row['missing_classical_records']) for row in pairings)
print(f'knockouts: {missing_games} missing games; {missing_classical} classical')
