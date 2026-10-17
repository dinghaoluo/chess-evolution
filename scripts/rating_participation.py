'''
Created on 16 October 2026

count January rated-list entries above a common historical threshold

@author: Dinghao Luo
'''

#%% imports
import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from zipfile import ZipFile

from bs4 import BeautifulSoup

from build_panels import read_rows, write_panel


#%% list readers
def players(source: dict):
    year = int(source['year'])
    path = Path(source['file'])
    assert hashlib.sha256(path.read_bytes()).hexdigest() == source['sha256']
    if source['source'] == 'olimpbase':
        soup = BeautifulSoup(path.read_bytes(), 'html.parser')
        lines = soup.pre.get_text().replace('\\r\\n', '\n').splitlines()
        for line in lines:
            if not line.strip() or 'Player_ID' in line or line.strip() == 'Inactive players':
                continue
            rating = line[67:71].strip()
            assert rating.isdigit() and 1000 <= int(rating) <= 3500, (year, line)
            yield {'id': line[7:18].strip(), 'name': line[18:56].strip(),
                   'rating': int(rating), 'birth_date': line[84:95].strip(),
                   'flag': line[100:].strip(), 'title': line[56:62].strip()}
        return
    with ZipFile(path) as archive:
        names = [name for name in archive.namelist() if name.lower().endswith('.txt')]
        assert len(names) == 1
        lines = archive.read(names[0]).decode('latin1').splitlines()
    for line in lines:
        if not line.strip() or not line.lstrip()[0].isdigit():
            continue
        identity = re.match(r'\s*(\d+)\s+', line)
        assert identity, (year, line)
        if year >= 2013:
            tail = re.search(r'\s(\d{1,4})\s+(\d+)\s+(\d+)\s+(\d{1,4})\s*([a-z]*)\s*$', line)
            assert tail, (year, line)
            yield {'id': identity[1], 'name': line[15:75].strip(), 'rating': int(tail[1]),
                   'birth_date': tail[4], 'flag': tail[5], 'title': line[84:89].strip()}
        else:
            country = re.search(r'\s([A-Za-z]{3})\s+(\d{1,4})\s+(\d+)\s*(.*?)\s*$', line)
            assert country, (year, line)
            if country[1] == 'Fed':
                assert year == 2006 and 1 <= int(identity[1]) <= 10 and country[2] == '0', line
            prefix = line[identity.end():country.start()].rstrip()
            title = re.search(r'\s([gw]?[mfc]|w?g|w?im|w?fm|w?gm|w?cm|m|f)\s*$', prefix, re.I)
            name = prefix[:title.start()].strip() if title else prefix.strip()
            suffix = country[4]
            flag = re.search(r'([a-z]+)\s*$', suffix)
            birth = suffix[:flag.start()].strip() if flag else suffix.strip()
            yield {'id': identity[1], 'name': name, 'rating': int(country[2]),
                   'birth_date': birth, 'flag': flag[1] if flag else '',
                   'title': title[1] if title else ''}


#%% counts
def main() -> None:
    sources = read_rows('data/curated/rating_sources.csv')
    awards = {int(row['year']): row for row in read_rows('data/curated/title_awards.csv')}
    summary = BeautifulSoup(Path('cache/research/olimpbase-summary.html').read_bytes(), 'html.parser')
    published_totals = {}
    for item in summary.select('tr'):
        cells = item.get_text('|', strip=True).split('|')
        if re.fullmatch(r'Jan \d{4}', cells[0]):
            published_totals[int(cells[0][-4:])] = int(cells[1].replace(',', ''))
    rows, threshold_rows, bridge_lists = [], [], {}
    for source in sources:
        year = int(source['year'])
        row = {'year': year, 'date': source['date'], 'threshold': 2250,
               'listed_total': None, 'observed_minimum': None, 'zero_rating_entries': None, 'membership_2250': None,
               'active_2250': None, 'living_title_holders': None, 'new_open_titles': None,
               'new_women_titles': None, 'summary_total': published_totals.get(year),
               'summary_difference': None, 'status': source['status'], 'limit': source['limit']}
        if source['status'] == 'available':
            entries = list(players(source))
            if year in [2008, 2009]:
                bridge_lists[year] = entries
            if year >= 2000:
                for threshold in [2000, 2250, 2400]:
                    threshold_rows.append({'year': year, 'threshold': threshold,
                                           'listed': None if year == 2002 else sum(entry['rating'] >= threshold for entry in entries),
                                           'active': sum(entry['rating'] >= threshold and 'i' not in entry['flag'] for entry in entries)})
            row['listed_total'] = len(entries)
            row['observed_minimum'] = min(entry['rating'] for entry in entries if entry['rating'] > 0)
            row['zero_rating_entries'] = sum(entry['rating'] == 0 for entry in entries)
            if year in published_totals:
                row['summary_difference'] = len(entries) - published_totals[year]
            if year == 1971:
                row['status'] = 'unofficial_excluded'
            else:
                row['membership_2250'] = sum(entry['rating'] >= 2250 for entry in entries)
                if year >= 2000:
                    row['active_2250'] = sum(entry['rating'] >= 2250 and 'i' not in entry['flag'] for entry in entries)
                else:
                    row['limit'] = 'active status unavailable before July 1999, even where the reconstructed list contains flags'
                if year == 2002:
                    row['membership_2250'] = None
                    row['status'] = 'membership_coverage_gap'
                    row['limit'] = 'only 84 of 8678 entries at 2250+ are flagged inactive, against 2800 in January 2001; total-membership coverage not reconciled'
                if year == 2011:
                    leaders = {entry['id']: entry['rating'] for entry in entries if entry['id'] in ['1503014', '5000017', '13300474']}
                    assert leaders == {'1503014': 2814, '5000017': 2810, '13300474': 2805}
                    row['limit'] = 'Nov10 header is stale: January URL and Carlsen 2814/Anand 2810/Aronian 2805 agree with the contemporary FIDE January announcement'
            if row['summary_difference']:
                row['limit'] += '; text-list total differs from the published summary by ' + str(row['summary_difference']) + ' entries'
        # These are awards, not people; a player can receive more than one title.
        if year in awards:
            row['new_open_titles'] = int(awards[year]['open_titles'])
            row['new_women_titles'] = int(awards[year]['women_titles'])
        rows.append(row)
    output = Path('data/derived/rating_participation.csv')
    with output.open('w', newline='') as destination:
        writer = csv.DictWriter(destination, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
    threshold_output = Path('data/derived/rating_thresholds.csv')
    with threshold_output.open('w', newline='') as destination:
        writer = csv.DictWriter(destination, fieldnames=list(threshold_rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(threshold_rows)
    bridge_rows = []
    ambiguous_ids = set()
    for entries in bridge_lists.values():
        ambiguous_ids.update(key for key, count in Counter(entry['id'] for entry in entries).items() if count > 1)
    before, after = [{entry['id']: entry for entry in bridge_lists[year] if entry['id'] not in ambiguous_ids}
                     for year in [2008, 2009]]
    for threshold in [2000, 2250, 2400]:
        initial = {key for key, entry in before.items() if entry['rating'] >= threshold and 'i' not in entry['flag']}
        final = {key for key, entry in after.items() if entry['rating'] >= threshold and 'i' not in entry['flag']}
        lost = initial - final
        row = {'threshold': threshold, 'active_2008': len(initial), 'active_2009': len(final),
               'ambiguous_entries_2008': sum(entry['id'] in ambiguous_ids and entry['rating'] >= threshold and 'i' not in entry['flag'] for entry in bridge_lists[2008]),
               'ambiguous_entries_2009': sum(entry['id'] in ambiguous_ids and entry['rating'] >= threshold and 'i' not in entry['flag'] for entry in bridge_lists[2009]),
               'retained': len(initial & final),
               'became_inactive': sum(key in after and 'i' in after[key]['flag'] for key in lost),
               'missing_after': sum(key not in after for key in lost),
               'active_below_threshold': sum(key in after and 'i' not in after[key]['flag'] for key in lost),
               'gained_eligible': len(final - initial)}
        assert row['retained'] + row['became_inactive'] + row['missing_after'] + row['active_below_threshold'] == row['active_2008']
        bridge_rows.append(row)
    bridge_output = Path('data/derived/rating_activity_bridge.csv')
    with bridge_output.open('w', newline='') as destination:
        writer = csv.DictWriter(destination, fieldnames=list(bridge_rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(bridge_rows)
    inputs = ['data/curated/rating_sources.csv', 'data/curated/rating_floor_changes.csv', 'data/curated/rating_activity_rules.csv', 'data/curated/title_awards.csv',
              'cache/research/olimpbase-summary.html', 'cache/research/fide-title-statistics-2011.pdf',
              'cache/research/fide-january-2011.html', 'scripts/rating_participation.py']
    inputs += [source['file'] for source in sources if source['status'] == 'available']
    config = {'annual_date': 'January', 'threshold': 2250,
              'inputs_sha256': {name: hashlib.sha256(Path(name).read_bytes()).hexdigest() for name in inputs},
              'outputs_sha256': {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in [output, threshold_output, bridge_output]}}
    Path('data/derived/rating_participation_config.json').write_text(json.dumps(config, indent=2) + '\n')
    write_panel('rating_participation', {'title': 'Human participation above a fixed rating threshold',
                'series': rows, 'threshold_series': threshold_rows, 'floor_changes': read_rows('data/curated/rating_floor_changes.csv'),
                'activity_rules': read_rows('data/curated/rating_activity_rules.csv'),
                'limits': ['January standard-rated list entries at 2250+, not all registered FIDE members or all people playing chess.',
                           '2250 is a conservative common threshold; changing ratings and coverage prevent a constant-skill interpretation.',
                           '1971 is unofficial; 1972–74 have no January edition; total-membership coverage in 2002 is unresolved. Gaps are not interpolated.',
                           'The 1975 text has 1534 entries against the summary’s 1543; use observed counts with this unresolved coverage difference.',
                           'The 2011 Nov10 header is stale: three leading ratings match FIDE’s January announcement. The downloaded contents are preserved.',
                           'Active means absence of the list inactive flag; unavailable before 2000 in this January series.',
                           'The threshold series counts entries; the 2008–09 identity bridge excludes duplicated IDs from both editions.',
                           'The January 2009 activity drop precedes the documented July 2009 changes; its exact rule implementation remains unverified.',
                           'The inactivity look-back doubled from 12 to 24 months for November 2020–December 2022; earlier historical rule coverage remains incomplete.',
                           'Living title holders cannot be identified from these lists and remain entirely unavailable.',
                           '2005–10 title awards are separate published counts, including CM/WCM; they count awards, not unique new title holders.',
                           'March 2024 changes ratings below 2000 directly, but remains a discontinuity in the rating system.',
                           'Growth cannot identify an engine effect, professional income, employment security, or a growth rate for all chess.']},
                ['data/derived/rating_participation.csv', str(threshold_output), 'data/derived/rating_participation_config.json',
                 'data/curated/rating_floor_changes.csv', 'data/curated/rating_activity_rules.csv'])
    print('rated-list series saved; living-title series unavailable; title awards available only for 2005–10')


if __name__ == '__main__':
    main()
