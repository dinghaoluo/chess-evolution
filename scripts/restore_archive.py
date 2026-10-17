'''
Created on 16 October 2026

recover the title games and source ledgers without reviving retired analyses

@author: Dinghao Luo
'''

#%% imports
import argparse
import csv
import hashlib
import io
import json
import tarfile
from pathlib import Path

import chess.pgn


#%% restore
def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--archive', type=Path, default=Path('cache/retired/20261016-before-refinement.tar.gz'))
    args = parser.parse_args()
    archive = args.archive
    with archive.open('rb') as source:
        digest = hashlib.file_digest(source, 'sha256').hexdigest()
    expected = Path(str(archive) + '.sha256').read_text().split()[0]
    if digest != expected:
        raise ValueError('retired archive hash differs from its sidecar')
    destination = Path('data/local/restored')
    ledgers = {'data/source_manifest.csv', 'data/events.csv', 'data/game_classifications.csv',
               'data/master_database_sources.csv', 'scripts/sample_master_reference.py'}
    restored = []
    with tarfile.open(archive) as source:
        members = source.getmembers()
        names = [member.name for member in members]
        if len(names) != len(set(names)):
            raise ValueError('duplicate archive members')
        manifest = list(csv.DictReader(io.StringIO(source.extractfile('data/source_manifest.csv').read().decode())))
        hashes = {row['source_file']: row for row in manifest}
        selected = [member for member in members if member.name in ledgers or (
            member.name.startswith('data/raw/pgnmentor/') and member.name.endswith('.pgn'))]
        assert ledgers <= {member.name for member in selected}
        for member in selected:
            assert member.isfile() and '..' not in Path(member.name).parts
            raw = source.extractfile(member).read()
            member_digest = hashlib.sha256(raw).hexdigest()
            row = {'member': member.name, 'bytes': len(raw), 'sha256': member_digest}
            if member.name.endswith('.pgn'):
                provenance = hashes[Path(member.name).name]
                if member_digest != provenance['sha256']:
                    raise ValueError('PGN differs from the archived source manifest: ' + member.name)
                row.update({key: provenance[key] for key in ['url', 'supplement_url', 'retrieved_at', 'licence', 'notes']})
            path = destination / member.name
            path.parent.mkdir(parents=True, exist_ok=True)
            if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest() != member_digest:
                raise ValueError('existing restored file has changed: ' + str(path))
            path.write_bytes(raw)
            restored.append(row)
        lumbra_pgns = [name for name in names if 'lumbra' in name.lower() and name.lower().endswith('.pgn')]
    output = {'archive': str(archive), 'archive_sha256': digest, 'destination': str(destination),
              'files': sorted(restored, key=lambda row: row['member']),
              'lumbra_raw_pgn_members': lumbra_pgns,
              'limits': ['The archive contains Lumbra source metadata and position indexes, without raw Lumbra PGNs.',
                         'The recovered sampling script consumes retired position IDs and cannot sample new quality-of-play cohorts.',
                         'PGN Mentor redistribution permission remains unidentified; recovered games stay in ignored local storage.']}
    Path('data/curated/restored_corpus.json').write_text(json.dumps(output, indent=2) + '\n')

    # these counts audit availability; the old ledger does not certify a new population
    with (destination / 'data/game_classifications.csv').open() as source:
        classifications = {(row['source_file'], int(row['source_ordinal'])): row for row in csv.DictReader(source)}
    counts = {}
    for row in restored:
        if not row['member'].endswith('.pgn'):
            continue
        with (destination / row['member']).open(encoding='utf-8-sig') as source:
            ordinal = 0
            while (game := chess.pgn.read_game(source)) is not None:
                ordinal += 1
                if game.errors:
                    raise ValueError('illegal restored main line: ' + row['member'])
                old = classifications[Path(row['member']).name, ordinal]
                key = game.headers.get('Date', '????')[:4], old['game_class'], old['accepted_for_analysis']
                count = counts.setdefault(key, {'games': 0, 'sides_with_rating': 0, 'sides_2200_2399': 0})
                count['games'] += 1
                for colour in ['White', 'Black']:
                    value = game.headers.get(colour + 'Elo', '')
                    if value.isdigit():
                        count['sides_with_rating'] += 1
                        count['sides_2200_2399'] += 2200 <= int(value) <= 2399
    with Path('data/derived/restored_corpus_coverage.csv').open('w', newline='') as target:
        writer = csv.DictWriter(target, fieldnames=['year', 'game_class', 'previously_accepted', 'games',
                                                    'sides_with_rating', 'sides_2200_2399'], lineterminator='\n')
        writer.writeheader()
        writer.writerows({'year': key[0], 'game_class': key[1], 'previously_accepted': key[2], **counts[key]}
                         for key in sorted(counts))
    print(len([row for row in restored if row['member'].endswith('.pgn')]), 'title PGNs recovered; raw Lumbra PGNs absent')


if __name__ == '__main__':
    main()
