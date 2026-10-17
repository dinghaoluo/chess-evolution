'''
Created on 16 October 2026

build the historical engines and identify the modern reference binary

@author: Dinghao Luo
'''

#%% imports
import hashlib
import json
import subprocess
import tarfile
from pathlib import Path
from urllib.request import urlopen

import chess
import chess.engine


#%% frozen sources
SOURCES = [
    ('fruit-2.1', 2005, 'Warpten/Fruit-2.1', '09627df3835f205c92ece013219c7a99ac4a023a', '37e0e8dd09aa53966a24ff328d1ec5a4e7bbca9a3f3a11e399e0be2c3e370624'),
    ('stockfish-4', 2013, 'official-stockfish/Stockfish', 'sf_4', '3508a3080e9aed3d9c285ebb43f6f952b8f35701969ede782dd7bdf69c1734b9'),
    ('stockfish-8', 2016, 'official-stockfish/Stockfish', 'sf_8', 'e2b77d801d8837c22c2391b8cae08622c1434a2bb5947ddb08b081e1ad35c76c'),
    ('stockfish-12', 2020, 'official-stockfish/Stockfish', 'sf_12', 'd1ec11d1cb8dfc5b33bcd6ec89ed0bafb3951cc1690851448a2696caa2022899'),
]
FOLDER = Path('cache/engines')
MODERN = FOLDER / 'stockfish-17.1/stockfish/stockfish-macos-m1-apple-silicon'


#%% build
def main() -> None:
    FOLDER.mkdir(parents=True, exist_ok=True)
    builds = []
    compiler = subprocess.check_output(['clang++', '--version'], text=True).splitlines()[0]
    for name, year, repository, revision, digest in SOURCES:
        url = f'https://codeload.github.com/{repository}/tar.gz/{revision}'
        archive = FOLDER / (name + '.tar.gz')
        if not archive.exists():
            archive.write_bytes(urlopen(url, timeout=60).read())
        assert hashlib.sha256(archive.read_bytes()).hexdigest() == digest
        folder = FOLDER / name
        folder.mkdir(exist_ok=True)
        with tarfile.open(archive) as source:
            source.extractall(folder, filter='data')
        src = next(folder.glob('*/src'))
        patch = ''
        if name == 'fruit-2.1':
            # Fruit parses 'go nodes' but never uses it; only add a stop condition
            changes = {
                'search.h': [('   bool infinite;', '   sint64 node_limit;\n   bool infinite;')],
                'search.cpp': [('   SearchInput->infinite = false;', '   SearchInput->node_limit = -1;\n   SearchInput->infinite = false;'),
                               ('void search_check() {', 'void search_check() {\n\n   if (SearchInput->node_limit >= 0 && SearchCurrent->node_nb >= SearchInput->node_limit) SearchInfo->stop = true;')],
                'protocol.cpp': [('   search_clear();\n\n   // depth limit', '   search_clear();\n   SearchInput->node_limit = nodes;\n\n   // depth limit')],
            }
            for filename, replacements in changes.items():
                path = src / filename
                text = path.read_text()
                for before, after in replacements:
                    assert text.count(before) == 1, (filename, before)
                    text = text.replace(before, after)
                path.write_text(text)
            patch = 'node-limit stop guard at the existing search_check cadence; search and evaluation otherwise unchanged'
        standard = '-std=c++11' if name == 'stockfish-4' else '-std=c++17'
        command = ['clang++', '-O3', '-DNDEBUG', standard, '-pthread', '-fno-strict-aliasing']
        if name.startswith('stockfish'):
            command += ['-DIS_64BIT', '-DUSE_PTHREADS']
        if name == 'stockfish-12':
            command += ['-DNNUE_EMBEDDING_OFF']
        # timeoday is a Windows-only file; tbcore is included by tbprobe
        files = [path for path in sorted(src.rglob('*.cpp')) if path.name not in ['timeoday.cpp', 'tbcore.cpp']]
        binary = folder / 'engine'
        command += [str(path) for path in files] + ['-o', str(binary)]
        run = subprocess.run(command, capture_output=True, text=True)
        (folder / 'build.log').write_text(run.stdout + run.stderr)
        run.check_returncode()
        net = None
        if name == 'stockfish-12':
            path = folder / 'nn-82215d0fd0df.nnue'
            net_url = 'https://tests.stockfishchess.org/api/nn/' + path.name
            if not path.exists():
                path.write_bytes(urlopen(net_url, timeout=60).read())
            net_digest = hashlib.sha256(path.read_bytes()).hexdigest()
            assert net_digest.startswith('82215d0fd0df')
            net = {'path': str(path.resolve()), 'sha256': net_digest, 'url': net_url}
        with chess.engine.SimpleEngine.popen_uci(str(binary)) as engine:
            options = {key: value for key, value in {'Hash': 64, 'Threads': 1, 'OwnBook': False,
                                                    'SyzygyPath': '', 'Contempt Factor': 0,
                                                    'Contempt': 0, 'Analysis Contempt': 'Off'}.items()
                       if key in engine.options}
            if net:
                options['EvalFile'] = net['path']
            engine.configure(options)
            probe = engine.play(chess.Board(), chess.engine.Limit(nodes=10000))
            assert probe.move in chess.Board().legal_moves
            builds.append({'name': name, 'year': year, 'engine_id': engine.id, 'binary': str(binary),
                           'binary_sha256': hashlib.sha256(binary.read_bytes()).hexdigest(),
                           'source_url': url, 'source_sha256': digest, 'compiler': compiler,
                           'command': command, 'patch': patch, 'options': options, 'network': net})
        print(name, 'built', flush=True)
    if not MODERN.exists():
        url = 'https://github.com/official-stockfish/Stockfish/releases/download/sf_17.1/stockfish-macos-m1-apple-silicon.tar'
        archive = FOLDER / 'stockfish-17.1.tar'
        archive.write_bytes(urlopen(url, timeout=60).read())
        MODERN.parent.parent.mkdir(exist_ok=True)
        with tarfile.open(archive) as source:
            source.extractall(MODERN.parent.parent, filter='data')
        MODERN.chmod(0o755)
    modern_digest = hashlib.sha256(MODERN.read_bytes()).hexdigest()
    assert modern_digest == '9345c44970093cabed9757be86a9ca86809a5b6ca1bdc654cf51a5eed7568858'
    options = {'Threads': 1, 'Hash': 64, 'UCI_ShowWDL': True, 'Skill Level': 20,
               'UCI_LimitStrength': False, 'SyzygyPath': ''}
    with chess.engine.SimpleEngine.popen_uci(str(MODERN)) as engine:
        engine.configure(options)
        modern = {'name': 'stockfish-17.1', 'year': 2025, 'engine_id': engine.id,
                  'binary': str(MODERN), 'binary_sha256': modern_digest, 'options': options,
                  'source_url': 'https://github.com/official-stockfish/Stockfish/releases/tag/sf_17.1',
                  'network': 'embedded in the official hashed binary'}
    builds.append(modern)
    # absolute network paths are local build settings; keep the saved analysis portable
    for build in builds:
        if build['name'] == 'stockfish-12':
            build['network']['path'] = str(FOLDER / 'stockfish-12/nn-82215d0fd0df.nnue')
            build['options']['EvalFile'] = build['network']['path']
    Path('data/derived/engine_builds.json').write_text(json.dumps(builds, indent=2) + '\n')
    Path('data/derived/stockfish_config.json').write_text(json.dumps({**modern,
        'python_chess_version': chess.__version__, 'hash_policy': 'new game before every search',
        'position_history': 'complete game move stack', 'syzygy': 'disabled'}, indent=2) + '\n')


if __name__ == '__main__':
    main()
