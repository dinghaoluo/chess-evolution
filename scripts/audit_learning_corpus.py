'''
Created on 16 October 2026

audit source headers before classifying classical games or sampling players

@author: Dinghao Luo
'''

#%% imports
import csv
import hashlib
import json
import re
import subprocess
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


#%% one batch
def audit(source: dict) -> dict:
    path = Path(source['file'])
    with path.open('rb') as raw:
        assert hashlib.file_digest(raw, 'sha256').hexdigest() == source['sha256']
    assert source['status'] == 'archived_hash_match'
    destination = Path('cache/learning/pgn') / (source['batch'] + '.pgn')
    destination.parent.mkdir(exist_ok=True)
    command = ['bsdtar', '-xOf', str(path), source['pgn_member']]
    process = subprocess.Popen(command, stdout=subprocess.PIPE)
    digest = hashlib.sha256()
    headers, games, fields, years, events = {}, 0, Counter(), Counter(), Counter()
    pilot_years = {1985, 1995, 2005, 2015, 2024}
    target_years = pilot_years | set(range(1995, 2004))
    selected_headers = []

    def count() -> None:
        nonlocal games
        if not headers:
            return
        games += 1
        fields.update(headers.keys())
        date = headers.get('Date', '')
        year = int(date[:4]) if re.match(r'^\d{4}\.', date) else 0
        years[year, 'records'] += 1
        if year not in target_years:
            return
        time_control = headers.get('TimeControl', '')
        termination = headers.get('Termination', '')
        event, site = headers.get('Event', ''), headers.get('Site', '')
        mode = headers.get('Mode', '')
        events[year, event, site, time_control, termination, mode] += 1
        for colour in ['White', 'Black']:
            elo = headers.get(colour + 'Elo', '')
            if not elo.isdigit() or int(elo) < 2200:
                continue
            band = '2600+' if int(elo) >= 2600 else '2400-2599' if int(elo) >= 2400 else '2200-2399'
            years[year, band + '_sides'] += 1
            years[year, band + '_with_time_control'] += time_control not in ['', '?', '-']
            years[year, band + '_with_fide_id'] += bool(headers.get(colour + 'FideId', ''))
        # These header examples diagnose the source; they are not an analytical sample.
        if len(selected_headers) < 100:
            selected_headers.append({'source_ordinal': games, 'headers': dict(headers)})

    with destination.open('wb') as raw:
        for line in process.stdout:
            raw.write(line)
            digest.update(line)
            if line.startswith(b'[Event '):
                count()
                headers = {}
            if line.startswith(b'['):
                match = re.fullmatch(rb'\[(\w+) "(.*)"\]\s*', line)
                assert match, (source['batch'], games, line[:100])
                headers[match[1].decode('ascii')] = match[2].decode('utf-8').replace('\\"', '"').replace('\\\\', '\\')
        count()
    process.stdout.close()
    assert process.wait() == 0
    field_path = Path('data/derived') / (source['batch'] + '_headers.json')
    field_path.write_text(json.dumps({'records': games, 'header_fields': dict(fields), 'examples': selected_headers},
                                    indent=2, ensure_ascii=False) + '\n')
    result = {'batch': source['batch'], 'archive': source['file'], 'archive_sha256': source['sha256'],
              'pgn': str(destination), 'pgn_sha256': digest.hexdigest(), 'pgn_bytes': destination.stat().st_size,
              'records': games, 'header_audit': str(field_path),
              'header_audit_sha256': hashlib.sha256(field_path.read_bytes()).hexdigest()}
    Path('data/derived/' + source['batch'] + '_audit.json').write_text(json.dumps(result, indent=2) + '\n')
    print(source['batch'], games, 'headers audited', flush=True)
    return {'source': result, 'years': years, 'events': events}


#%% main
def main() -> None:
    manifest = Path('data/curated/learning_corpus_sources.json')
    sources = json.loads(manifest.read_text())['sources']
    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(audit, sources))
    years, events = Counter(), Counter()
    for result in results:
        years.update(result['years'])
        events.update(result['events'])
    output = Path('data/derived/learning_header_coverage.csv')
    with output.open('w', newline='') as target:
        writer = csv.writer(target, lineterminator='\n')
        writer.writerow(['year', 'quantity', 'count'])
        writer.writerows((*key, count) for key, count in sorted(years.items()))
    event_path = Path('data/derived/learning_event_headers.csv')
    with event_path.open('w', newline='') as target:
        writer = csv.writer(target, lineterminator='\n')
        writer.writerow(['year', 'event', 'site', 'time_control', 'termination', 'mode', 'records'])
        writer.writerows((*key, count) for key, count in sorted(events.items()))
    config = {'inputs_sha256': {str(manifest): hashlib.sha256(manifest.read_bytes()).hexdigest(),
                               'scripts/audit_learning_corpus.py': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},
              'outputs_sha256': {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in [output, event_path]},
              'sources': [result['source'] for result in results],
              'limits': ['Header counts are not eligible classical games, verified identities, or legal-mainline counts.',
                         'The old non-OTB filter and championship exclusions are not applied.',
                         'Time-control tags and source OTB labels require a separate event and mainline audit before sampling.',
                         '100 source-order examples per batch diagnose metadata only; they are not a random sample.']}
    Path('data/derived/learning_header_audit_config.json').write_text(json.dumps(config, indent=2) + '\n')


if __name__ == '__main__':
    main()
