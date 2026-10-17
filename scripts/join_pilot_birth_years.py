'''
Created on 16 October 2026

join sampled players to the nearest January list without filling missing birth years

@author: Dinghao Luo
'''

#%% imports
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

from rating_participation import players
from sample_learning_pilot import date_interval, names_agree, normalise_name


#%% sampled identities
def birth_year(value: str, list_year: int) -> int | None:
    full_year = re.search(r'\b(18\d{2}|19\d{2}|20\d{2})\b', value)
    if full_year:
        year = int(full_year[1])
        return year if 0 <= list_year - year <= 100 else None
    short_date = re.fullmatch(r'\d{2}\.\d{2}\.(\d{2})', value)
    if short_date:
        candidates = [base + int(short_date[1]) for base in [1800, 1900, 2000] if 0 <= list_year - base - int(short_date[1]) <= 100]
        return candidates[0] if len(candidates) == 1 else None
    return None


def nearest_january(value: str) -> int:
    when = date.fromisoformat(value.replace('.', '-'))
    return min([when.year, when.year + 1], key=lambda year: (abs((date(year, 1, 1) - when).days), year))


def main() -> None:
    sample_path = Path('data/derived/learning_pilot_sample.csv')
    sample = list(csv.DictReader(sample_path.open()))
    sources = {int(row['year']): row for row in csv.DictReader(Path('data/curated/rating_sources.csv').open()) if row['status'] == 'available'}
    events = {item['event_id']: item for item in json.loads(Path('data/curated/learning_classical_events.json').read_text())['events']}
    lists = {}
    inputs = [sample_path, Path(__file__), Path('scripts/rating_participation.py'), Path('scripts/sample_learning_pilot.py'), Path('data/curated/rating_sources.csv'), Path('data/curated/learning_classical_events.json')]
    rows = []
    for side in sample:
        lower, upper = date_interval(side['date'])
        lower = max(lower, events[side['event_id']]['start'])
        upper = min(upper, events[side['event_id']]['end'])
        first, last = nearest_january(lower), nearest_january(upper)
        row = {**side, 'january_year': first if first == last else '', 'match_status': '',
               'matched_id': '', 'matched_name': '', 'birth_date_raw': '', 'birth_year': '',
               'age_lower': '', 'age_upper': '', 'age_group': '', 'list_distance_days_min': '', 'list_distance_days_max': ''}
        if first != last:
            row['match_status'] = 'nearest_list_ambiguous'
        elif first not in sources:
            row['match_status'] = 'list_unavailable'
        else:
            if first not in lists:
                entries = list(players(sources[first]))
                by_id, by_name = defaultdict(list), defaultdict(list)
                for item in entries:
                    by_id[item['id']].append(item)
                    by_name[normalise_name(item['name'])].append(item)
                lists[first] = by_id, by_name
                inputs.append(Path(sources[first]['file']))
            by_id, by_name = lists[first]
            id_matches = by_id.get(side['pgn_fide_id'], []) if side['pgn_fide_id'] else []
            matches = id_matches or by_name.get(normalise_name(side['player']), [])
            if len(matches) > 1:
                row['match_status'] = 'ambiguous_identity'
            elif not matches:
                row['match_status'] = 'unmatched'
            elif not names_agree(side['player'], matches[0]['name']):
                row['match_status'] = 'id_name_conflict'
            else:
                match = matches[0]
                row.update({'match_status': 'id_and_name' if id_matches else 'exact_name',
                            'matched_id': match['id'], 'matched_name': match['name'], 'birth_date_raw': match['birth_date']})
                year = birth_year(match['birth_date'], first)
                if year is not None:
                    upper_age = int(side['year']) - year
                    lower_age = upper_age - 1
                    row.update({'birth_year': year, 'age_lower': lower_age, 'age_upper': upper_age,
                                'age_group': 'under20' if upper_age < 20 else '25to40' if lower_age >= 25 and upper_age <= 40 else 'boundary_or_other'})
            distances = [abs((date(first, 1, 1) - date.fromisoformat(value.replace('.', '-'))).days) for value in [lower, upper]]
            row.update({'list_distance_days_min': min(distances), 'list_distance_days_max': max(distances)})
        rows.append(row)
    output = Path('data/derived/learning_pilot_birth_years.csv')
    with output.open('w', newline='') as destination:
        writer = csv.DictWriter(destination, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
    counts = Counter((row['year'], row['match_status'], bool(row['birth_year'])) for row in rows)
    config = {'inputs_sha256': {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in inputs},
              'outputs_sha256': {str(output): hashlib.sha256(output.read_bytes()).hexdigest()},
              'counts': [{'year': key[0], 'match_status': key[1], 'birth_year_available': key[2], 'count': value} for key, value in sorted(counts.items())],
              'limits': ['Only sampled players are joined; PGN Elo still defines the band.',
                         'Exact supplied ID requires compatible name; otherwise a unique exact normalised full-name match is accepted.',
                         'No fuzzy surname matching, imputed birth year, or full top-100 identity join.',
                         'Two-digit birth years require one candidate aged 0–100 on the list; unresolved centuries remain missing.',
                         'Birth-year ages span one year; under-20 and 25–40 groups exclude boundary ambiguity.',
                         'Original game-date intervals are intersected with documented event dates; no exact day is invented.',
                         'List coverage, source identity errors and name changes can reduce the match rate.']}
    Path('data/derived/learning_pilot_birth_config.json').write_text(json.dumps(config, indent=2) + '\n')
    print(len(rows), 'sampled players;', sum(row['match_status'] in ['id_and_name', 'exact_name'] for row in rows), 'matched;', sum(bool(row['birth_year']) for row in rows), 'birth years')


if __name__ == '__main__':
    main()
