'''
Created on 16 October 2026

sample player-games only from documented classical events

@author: Dinghao Luo
'''

#%% imports
import calendar
import csv
import hashlib
import io
import json
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from zipfile import ZipFile

import chess.pgn


#%% identities and dates
def normalise_name(name: str) -> str:
    return re.sub(r'[^a-z0-9,]', '', unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode().lower())


def player_key(name: str) -> str:
    parts = normalise_name(name).split(',')
    return parts[0] + ',' + (parts[1][:1] if len(parts) == 2 else '')


def reference_name(name: str) -> str:
    return re.sub(r' [A-Z]{3}$', '', name)


def names_agree(name: str, reference: str) -> bool:
    name, reference = normalise_name(name), normalise_name(reference_name(reference))
    if name == reference:
        return True
    left, right = name.split(','), reference.split(',')
    return len(left) == len(right) == 2 and left[0] == right[0] and bool(left[1]) and bool(right[1]) and (left[1].startswith(right[1]) or right[1].startswith(left[1]))


def date_interval(value: str) -> tuple[str, str]:
    year, month, day = value.split('.')
    if '?' in year:
        raise ValueError(value)
    first_month, last_month = (1, 12) if '?' in month else (int(month), int(month))
    first_day = 1 if '?' in day else int(day)
    last_day = calendar.monthrange(int(year), last_month)[1] if '?' in day else int(day)
    return (f'{year}.{first_month:02}.{first_day:02}', f'{year}.{last_month:02}.{last_day:02}')


def mainline_key(game: chess.pgn.Game) -> str:
    return hashlib.sha256((' '.join(move.uci() for move in game.mainline_moves()) + ' ' + game.headers['Result']).encode()).hexdigest()


def raw_games(path: Path):
    digest, content, ordinal = hashlib.sha256(), [], 0
    with path.open('rb') as source:
        for line in source:
            digest.update(line)
            if line.startswith(b'[Event ') and content:
                ordinal += 1
                yield ordinal, b''.join(content)
                content = []
            content.append(line)
        if content:
            ordinal += 1
            yield ordinal, b''.join(content)
    yield None, digest.hexdigest()


#%% eligibility and duplicate audit
def main() -> None:
    ledger = Path('data/curated/learning_classical_events.json')
    events = json.loads(ledger.read_text())['events']
    inputs = [ledger, Path('data/derived/learning_header_audit_config.json'), Path(__file__)]
    references, reference_errors = {}, []
    for event in events:
        if event['source_file']:
            inputs.append(Path(event['source_file']))
        if not event['independent_scores']:
            continue
        scores = defaultdict(list)
        paths = event['independent_scores']
        for name in paths if isinstance(paths, list) else [paths]:
            path = Path(name)
            inputs.append(path)
            if path.suffix == '.zip':
                with ZipFile(path) as archive:
                    texts = [archive.read(name).decode('latin1') for name in archive.namelist() if name.lower().endswith('.pgn')]
            else:
                texts = [path.read_text(encoding='utf-8-sig')]
            for text in texts:
                source = io.StringIO(text)
                while (game := chess.pgn.read_game(source)) is not None:
                    if game.errors:
                        reference_errors.append({'file': str(path), 'headers': dict(game.headers), 'errors': [str(error) for error in game.errors]})
                        continue
                    scores[mainline_key(game)].append(dict(game.headers))
        references[event['event_id']] = scores
    counts, candidates, exclusions, groups = Counter(), [], [], defaultdict(list)
    header_config = json.loads(inputs[1].read_text())
    for source in header_config['sources']:
        relevant = [event for event in events if int(source['batch'][4:8]) <= event['year'] <= int(source['batch'][9:13])]
        for ordinal, raw in raw_games(Path(source['pgn'])):
            if ordinal is None:
                assert raw == source['pgn_sha256']
                break
            event_match = re.search(rb'^\[Event "(.*)"\]', raw, re.M)
            game_date = re.search(rb'^\[Date "(.*)"\]', raw, re.M)
            if not event_match or not game_date:
                continue
            event_name = event_match[1].decode('utf-8')
            matching = [event for event in relevant if event_name in event['aliases'] and game_date[1][:4].decode() == str(event['year'])]
            if not matching:
                continue
            assert len(matching) == 1
            event = matching[0]
            counts[event['event_id'], 'candidate_records'] += 1
            game = chess.pgn.read_game(io.StringIO(raw.decode('utf-8')))
            headers = dict(game.headers)
            reason, reference = None, None
            if game.errors:
                reason = 'illegal_mainline'
            elif headers.get('Variant', 'Standard') != 'Standard' or game.board().fen() != chess.STARTING_FEN:
                reason = 'nonstandard_start'
            elif headers['Result'] not in ['1-0', '0-1', '1/2-1/2'] or not list(game.mainline_moves()):
                reason = 'unplayed_or_unfinished'
            else:
                lower, upper = date_interval(headers['Date'])
                if upper < event['start'] or lower > event['end']:
                    reason = 'outside_event_dates'
                elif event['event_id'] in references and mainline_key(game) not in references[event['event_id']]:
                    reason = 'independent_score_mismatch'
                elif event['event_id'] in references:
                    matches = [item for item in references[event['event_id']][mainline_key(game)]
                               if all(names_agree(headers[colour], item[colour]) for colour in ['White', 'Black'])]
                    if len(matches) != 1:
                        reason = 'independent_identity_mismatch'
                    else:
                        reference = matches[0]
            item = {'batch': source['batch'], 'ordinal': ordinal, 'event_id': event['event_id'],
                    'year': event['year'], 'headers': headers, 'moves_uci': ' '.join(m.uci() for m in game.mainline_moves()),
                    'raw_sha256': hashlib.sha256(raw).hexdigest()}
            if reason:
                counts[event['event_id'], reason] += 1
                exclusions.append({**item, 'reason': reason})
                continue
            # surname and initial identify candidate duplicates only, never a cross-year player
            if reference:
                item['reference_headers'] = reference
            identity_headers = reference or headers
            key = (event['event_id'], player_key(identity_headers['White']), player_key(identity_headers['Black']), identity_headers['Round'].split('.')[0])
            groups[key].append(item)
        print(source['batch'], 'event candidates checked', flush=True)
    for group in groups.values():
        versions = {item['moves_uci'] + ' ' + item['headers']['Result'] for item in group}
        if len(versions) > 1:
            for item in group:
                counts[item['event_id'], 'conflicting_versions'] += 1
                exclusions.append({**item, 'reason': 'conflicting_versions'})
            continue
        ordered = sorted(group, key=lambda item: (-sum(bool(v) for v in item['headers'].values()), item['batch'], item['ordinal']))
        chosen = ordered[0]
        chosen['game_id'] = hashlib.sha256(json.dumps([chosen['event_id'], chosen['headers']['White'], chosen['headers']['Black'], chosen['moves_uci']], ensure_ascii=False).encode()).hexdigest()[:20]
        chosen['duplicates_removed'] = len(group) - 1
        candidates.append(chosen)
        counts[chosen['event_id'], 'duplicate_records'] += len(group) - 1
        counts[chosen['event_id'], 'eligible_games'] += 1
    candidates.sort(key=lambda item: (item['year'], item['game_id']))

    # one player-year first; the hash order gives every eligible side a reproducible draw
    sides = defaultdict(list)
    for game in candidates:
        for colour in ['White', 'Black']:
            elo = game['headers'].get(colour + 'Elo', '')
            if not elo.isdigit() or int(elo) < 2200:
                continue
            rating = int(elo)
            band = '2600+' if rating >= 2600 else '2400-2599' if rating >= 2400 else '2200-2399'
            reference = game.get('reference_headers', {})
            identity = (normalise_name(reference_name(reference[colour])) if reference
                        else game['headers'].get(colour + 'FideId') or normalise_name(game['headers'][colour]))
            item = {'game_id': game['game_id'], 'year': game['year'], 'band': band,
                    'colour': colour.lower(), 'player': game['headers'][colour], 'player_key': identity,
                    'pgn_elo': rating, 'pgn_fide_id': game['headers'].get(colour + 'FideId', ''),
                    'date': game['headers']['Date'], 'event_id': game['event_id'],
                    'reference_elo': reference.get(colour + 'Elo', ''),
                    'batch': game['batch'], 'source_ordinal': game['ordinal']}
            sides[game['year'], band].append(item)
    sampled, coverage = [], []
    for year in [1985, 1995, 2005, 2015, 2024]:
        seen_players = set()
        # identities appearing in different bands in one year still get one game
        ranked = sorted([item for (y, band), items in sides.items() if y == year for item in items],
                        key=lambda item: hashlib.sha256(('20261016|' + item['game_id'] + '|' + item['colour']).encode()).hexdigest())
        selected_by_band = Counter()
        eligible_players = defaultdict(set)
        for item in ranked:
            eligible_players[item['band']].add(item['player_key'])
            if item['player_key'] in seen_players or selected_by_band[item['band']] >= 50:
                continue
            seen_players.add(item['player_key'])
            sampled.append(item)
            selected_by_band[item['band']] += 1
        for band in ['2200-2399', '2400-2599', '2600+']:
            coverage.append({'year': year, 'band': band, 'eligible_sides': len(sides[year, band]),
                             'eligible_player_keys': len(eligible_players[band]), 'sampled_player_games': selected_by_band[band],
                             'target': 50, 'shortage': 50 - selected_by_band[band]})
    paths = []
    for name, rows in [('learning_pilot_pool', candidates), ('learning_pilot_exclusions', exclusions), ('learning_reference_errors', reference_errors)]:
        path = Path('data/derived/' + name + '.jsonl')
        path.write_text(''.join(json.dumps(row, ensure_ascii=False) + '\n' for row in rows))
        paths.append(path)
    for name, rows in [('learning_pilot_sample', sampled), ('learning_pilot_coverage', coverage),
                       ('learning_event_audit', [{'event_id': key[0], 'quantity': key[1], 'count': value} for key, value in sorted(counts.items())])]:
        path = Path('data/derived/' + name + '.csv')
        with path.open('w', newline='') as destination:
            writer = csv.DictWriter(destination, fieldnames=list(rows[0]), lineterminator='\n')
            writer.writeheader()
            writer.writerows(rows)
        paths.append(path)
    config = {'seed': 20261016, 'target_per_year_band': 50, 'player_year_cap': 1,
              'sampling': 'SHA-256 ordering of seed, game ID and colour; cap across all three bands',
              'inputs_sha256': {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in inputs},
              'pgn_inputs': {source['pgn']: source['pgn_sha256'] for source in header_config['sources']},
              'outputs_sha256': {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths},
              'limits': ['Restricted documented-event pool, not representative classical chess; variance and throughput only.',
                         'Conflicting duplicate scores are quarantined; near-copy and truncated scores may still be missing.',
                         'Player-year cap uses independent event-archive names where matched, otherwise supplied FIDE ID or full normalised name; unresolved aliases can evade the cap.',
                         'Reference-archive Elo disagreements are retained beside the original mover PGN Elo; no ratings are silently replaced.',
                         'Independent game archives may share upstream scores; archived events require an exact score/result and compatible participant-name match.',
                         'Only sampled identities will be joined to rating lists; PGN Elo defines the mover band.']}
    Path('data/derived/learning_pilot_sample_config.json').write_text(json.dumps(config, indent=2) + '\n')
    print(len(candidates), 'eligible games;', len(sampled), 'sampled player-games; target 750', flush=True)


if __name__ == '__main__':
    main()
