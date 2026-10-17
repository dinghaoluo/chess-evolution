'''
Created on 16 October 2026

build and bench the four additional releases for the Nielsen comparison

@author: Dinghao Luo
'''

#%% imports
import hashlib
import json
import re
import shutil
import subprocess
import tarfile
from pathlib import Path

import chess.engine


#%% main
def main() -> None:
    source_file = Path('data/curated/nielsen_engine_sources.json')
    sources = json.loads(source_file.read_text())
    builds = []
    for source in sources:
        for item in [source['archive'], source['network']]:
            assert hashlib.sha256(Path(item['file']).read_bytes()).hexdigest() == item['sha256']
        folder = Path('cache/research') / source['name']
        folder.mkdir(exist_ok=True)
        with tarfile.open(source['archive']['file']) as archive:
            archive.extractall(folder, filter='data')
        src = next(folder.glob('*/src'))
        network = Path(source['network']['file'])
        shutil.copyfile(network, src / network.name)
        command = ['make', '-j4', 'build', 'ARCH=apple-silicon', 'COMP=clang', 'CXX=clang++']
        run = subprocess.run(command, cwd=src, capture_output=True, text=True)
        (folder / 'build.log').write_text(run.stdout + run.stderr)
        run.check_returncode()
        binary = src / 'stockfish'
        run = subprocess.run([str(binary), 'bench'], capture_output=True, text=True, check=True)
        log = folder / 'bench.log'
        log.write_text(run.stdout + run.stderr)
        nodes = int(re.search(r'Nodes searched\s*:\s*(\d+)', run.stdout + run.stderr).group(1))
        if nodes != source['expected_nodes']:
            raise ValueError(f'{source["name"]} bench differs: {nodes} versus {source["expected_nodes"]}')
        with chess.engine.SimpleEngine.popen_uci(str(binary)) as engine:
            options = {key: value for key, value in {'Threads': 1, 'Hash': 64, 'SyzygyPath': '',
                       'Contempt': 0, 'Analysis Contempt': 'Off', 'UCI_ShowWDL': True}.items() if key in engine.options}
            engine.configure(options)
            builds.append({'name': source['name'], 'year': source['year'], 'engine_id': engine.id,
                           'binary': str(binary), 'binary_sha256': hashlib.sha256(binary.read_bytes()).hexdigest(),
                           'options': options, 'archive_sha256': source['archive']['sha256'],
                           'network_sha256': source['network']['sha256'], 'commit': source['commit'],
                           'build_command': command, 'compiler': subprocess.check_output(['clang++', '--version'], text=True).splitlines()[0],
                           'bench_nodes': nodes, 'expected_bench_nodes': source['expected_nodes'],
                           'bench_log': str(log), 'bench_log_sha256': hashlib.sha256(log.read_bytes()).hexdigest()})
        print(source['name'], 'bench matched', nodes, flush=True)
    output = Path('data/derived/nielsen_engine_builds.json')
    output.write_text(json.dumps(builds, indent=2) + '\n')
    Path('data/derived/nielsen_engine_builds_config.json').write_text(json.dumps({
        'inputs_sha256': {str(source_file): hashlib.sha256(source_file.read_bytes()).hexdigest()},
        'output_sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
        'limits': ['Official apple-silicon make target with clang; one-thread searches.',
                   'Bench agreement checks the release signature, without equal costs per searched node.']}, indent=2) + '\n')


if __name__ == '__main__':
    main()
