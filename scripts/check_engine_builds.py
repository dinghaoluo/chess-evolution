'''
Created on 16 October 2026

check release bench signatures and compare the Fruit mirror with Debian source

@author: Dinghao Luo
'''

#%% imports
import difflib
import hashlib
import json
import re
import subprocess
import tarfile
from pathlib import Path


#%% main
def main() -> None:
    references = json.loads(Path('data/curated/engine_bench_references.json').read_text())
    builds = json.loads(Path('data/derived/engine_builds.json').read_text())
    checked = []
    for build in builds:
        if build['name'] not in ['stockfish-4', 'stockfish-8', 'stockfish-12']:
            continue
        reference = next(row for row in references if row['name'] == build['name'])
        assert hashlib.sha256(Path(build['binary']).read_bytes()).hexdigest() == build['binary_sha256']
        run = subprocess.run([build['binary'], 'bench'], capture_output=True, text=True, check=True)
        text = run.stdout + run.stderr
        log = Path('cache/research') / (build['name'] + '-bench.log')
        log.write_text(text)
        nodes = int(re.search(r'Nodes searched\s*:\s*(\d+)', text).group(1))
        checked.append({'engine': build['name'], 'binary_sha256': build['binary_sha256'],
                        'nodes': nodes, 'expected_nodes': reference['expected_nodes'],
                        'matches_official': nodes == reference['expected_nodes'], 'source_url': reference['source_url'],
                        'log': str(log), 'log_sha256': hashlib.sha256(log.read_bytes()).hexdigest()})
    assert all(row['matches_official'] for row in checked)
    output = Path('data/derived/engine_bench_checks.json')
    output.write_text(json.dumps(checked, indent=2) + '\n')

    archives = [Path('cache/engines/fruit-2.1.tar.gz'), Path('cache/research/fruit-debian.orig.tar.gz')]
    fruit = next(build for build in builds if build['name'] == 'fruit-2.1')
    sources = json.loads(Path('data/curated/research_sources.json').read_text())
    debian = next(row for row in sources if row['file'] == str(archives[1]))
    assert hashlib.sha256(archives[0].read_bytes()).hexdigest() == fruit['source_sha256']
    assert hashlib.sha256(archives[1].read_bytes()).hexdigest() == debian['sha256']
    dsc = Path('cache/research/fruit-debian.dsc')
    assert debian['sha256'] in dsc.read_text()
    trees = []
    for path in archives:
        with tarfile.open(path) as archive:
            trees.append({str(Path(member.name).relative_to(Path(member.name).parts[0])): archive.extractfile(member).read()
                          for member in archive if member.isfile() and '/src/' in member.name})
    names = sorted(set(trees[0]) | set(trees[1]))
    changed, diff = [], []
    for name in names:
        left = trees[0].get(name, b'').decode('latin-1').splitlines()
        right = trees[1].get(name, b'').decode('latin-1').splitlines()
        if left == right:
            continue
        changed.append(name)
        diff.extend(difflib.unified_diff(left, right, fromfile='mirror/' + name, tofile='debian/' + name, lineterm=''))
    comparison = Path('data/derived/fruit_source.diff')
    comparison.write_text('\n'.join(diff) + ('\n' if diff else ''))
    report = {'source_files': len(names), 'changed_after_newline_normalisation': changed,
              'changed_cpp_or_headers': [name for name in changed if Path(name).suffix in ['.cpp', '.h']],
              'inputs_sha256': {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in [*archives, dsc]},
              'diff_sha256': hashlib.sha256(comparison.read_bytes()).hexdigest(),
              'limits': ['Compares the unpatched mirror with Debian original DFSG source, normalising line endings only.',
                         'The local node-limit patch is recorded separately in engine_builds.json.',
                         'Debian .dsc checksum checked; its OpenPGP signature was not independently authenticated.']}
    Path('data/derived/fruit_source_check.json').write_text(json.dumps(report, indent=2) + '\n')
    config = {'inputs_sha256': {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in [
                  Path('data/curated/engine_bench_references.json'), Path('data/derived/engine_builds.json')]},
              'outputs_sha256': {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in [
                  output, comparison, Path('data/derived/fruit_source_check.json')]}}
    Path('data/derived/engine_build_checks_config.json').write_text(json.dumps(config, indent=2) + '\n')
    print('three official bench signatures matched; Fruit differences:', ', '.join(changed) or 'none')


if __name__ == '__main__':
    main()
