'''
Created on 15 October 2026

check championship dates against complete matching game scores

@author: Dinghao Luo
'''

#%% imports
import csv
import calendar
import re
import unicodedata
from datetime import datetime
from collections import defaultdict
from pathlib import Path


#%% player identities
DATA = Path('data')


def surname(name: str) -> str:
    name = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode()
    name = name.split(',')[0].lower().strip()
    if len(name.split()[-1]) == 1:
        name = name.rsplit(' ', 1)[0]
    name = re.sub('[^a-z]', '', name)
    return {'kortschnoj': 'korchnoi', 'kortchnoi': 'korchnoi', 'spasski': 'spassky'}.get(name, name)


def exact_date(date: str) -> bool:
    try:
        datetime.strptime(date, '%Y.%m.%d')
        return True
    except ValueError:
        return False


#%% source comparisons
with (DATA / 'novelty.csv').open() as source:
    games = list(csv.DictReader(source))
matches = defaultdict(list)
with (DATA / 'master_game_matches.csv').open() as source:
    for row in csv.DictReader(source):
        matches[row['game_id']].append(row)
rows = []
for game in games:
    candidates = [row for row in matches[game['game_id']]
                  if surname(row['white']) == surname(game['white'])
                  and surname(row['black']) == surname(game['black'])
                  and row['date'][:4].isdigit()
                  and int(game['year']) <= int(row['date'][:4]) <= int(game['year']) +
                  int(game['event_id'] in ['world_1890', 'world_1896', 'world_1984'])]
    exact_dates = sorted({row['date'] for row in candidates if exact_date(row['date'])})
    resolved = game['date']
    status = 'original exact date' if '?' not in resolved else 'unresolved'
    if '?' in resolved and len(exact_dates) == 1:
        resolved = exact_dates[0]
        status = 'unique exact date in matching full scores'
    elif len(exact_dates) > 1:
        status = 'conflicting dates; original retained'
    elif exact_dates and resolved != exact_dates[0]:
        status = 'source disagrees with original exact date; original retained'
    witness = next((row for row in candidates if row['date'] == resolved), {})
    rows.append({'game_id': game['game_id'], 'event_id': game['event_id'], 'round': game['round'],
                 'original_date': game['date'], 'analysis_date': resolved, 'status': status,
                 'matching_records': len(candidates), 'exact_dates': ';'.join(exact_dates),
                 'witness_batch': witness.get('batch', ''), 'witness_ordinal': witness.get('source_ordinal', '')})
# a unique source date can still contradict the round order
for event_id in {row['event_id'] for row in rows}:
    exact = sorted([row for row in rows if row['event_id'] == event_id and exact_date(row['analysis_date'])],
                   key=lambda row: int(row['round'].split('.')[0]))
    conflicts = set()
    for previous, current in zip(exact, exact[1:]):
        if current['analysis_date'] < previous['analysis_date']:
            conflicts.update([previous['game_id'], current['game_id']])
    for row in exact:
        if row['game_id'] in conflicts:
            row['status'] = 'round chronology conflict; original retained'
            row['analysis_date'] = row['original_date']

# incomplete dates remain intervals; earlier rounds can establish the following year
for row in rows:
    year, month, day = row['analysis_date'].split('.')
    low = year + ('01' if month == '??' else month) + ('01' if day == '??' else day)
    high_month = 12 if month == '??' else int(month)
    high_day = calendar.monthrange(int(year), high_month)[1] if day == '??' else int(day)
    high_year = int(year) + int(month == '??' and row['event_id'] in ['world_1890', 'world_1896', 'world_1984'])
    high = f'{high_year:04}{high_month:02}{high_day:02}'
    before = [other['analysis_date'].replace('.', '') for other in rows
              if other['event_id'] == row['event_id'] and exact_date(other['analysis_date'])
              and int(other['round'].split('.')[0]) < int(row['round'].split('.')[0])]
    after = [other['analysis_date'].replace('.', '') for other in rows
             if other['event_id'] == row['event_id'] and exact_date(other['analysis_date'])
             and int(other['round'].split('.')[0]) > int(row['round'].split('.')[0])]
    row['date_lower_bound'] = max([low] + before)
    row['date_upper_bound'] = min([high] + after)
    assert row['date_lower_bound'] <= row['date_upper_bound'], row

with (DATA / 'game_date_audit.csv').open('w', newline='') as destination:
    writer = csv.DictWriter(destination, fieldnames=list(rows[0]), lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows)
print(sum('?' not in row['analysis_date'] for row in rows), 'exact dates;',
      sum('conflict' in row['status'] or 'disagree' in row['status'] for row in rows), 'conflicts retained')
