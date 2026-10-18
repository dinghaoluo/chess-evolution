'''
Created on 15 October 2026

check saved histories, clocks, selected comparisons, and figure provenance

@author: Dinghao Luo
'''

#%% imports
import csv
import hashlib
import io
import json
import unittest
from collections import defaultdict
from pathlib import Path
from unittest.mock import MagicMock
from zipfile import ZipFile

import chess
import chess.engine
import chess.pgn

from engine_ladder import candidate_class, position_board
from pal_css_2005_case import ENGINE, search


#%% saved evidence
def read_rows(path: str) -> list[dict]:
    with Path(path).open() as source:
        return list(csv.DictReader(source))


class EvidenceChecks(unittest.TestCase):
    def test_source_hashes(self):
        for row in json.loads(Path('data/curated/source_files.json').read_text()):
            path = Path('cache/sources') / row['file']
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), row['sha256'], row['file'])

    def test_repetition_history(self):
        board = chess.Board()
        for move in ['g1f3', 'g8f6', 'f3g1', 'f6g8'] * 4:
            board.push_uci(move)
        self.assertTrue(board.is_fivefold_repetition())
        self.assertFalse(chess.Board(board.fen()).is_fivefold_repetition())

    def test_single_legal_root(self):
        board = chess.Board('7k/8/6K1/8/8/8/8/7R b - - 0 1')
        self.assertEqual(board.legal_moves.count(), 1)
        config = json.loads(Path('data/derived/stockfish_config.json').read_text())
        with chess.engine.SimpleEngine.popen_uci(str(ENGINE)) as engine:
            engine.configure(config['options'])
            infos = search(engine, board, 10000, multipv=3)
        self.assertEqual(len(infos), 1)
        self.assertEqual(infos[0]['pv'][0], next(iter(board.legal_moves)))

    def test_incomplete_cycle_fails_explicitly(self):
        analysis = MagicMock()
        analysis.__enter__.return_value = analysis
        analysis.__iter__.return_value = iter([{'multipv': 1, 'depth': 4,
            'pv': [chess.Move.from_uci('e2e4')], 'score': chess.engine.PovScore(chess.engine.Cp(20), chess.WHITE)}])
        analysis.multipv = [{'nodes': 20}]
        engine = MagicMock()
        engine.analysis.return_value = analysis
        with self.assertRaisesRegex(chess.engine.EngineError, 'complete exact MultiPV'):
            search(engine, chess.Board(), 20, multipv=3)
        analysis.__iter__.return_value = iter([])
        analysis.multipv = []
        with self.assertRaisesRegex(chess.engine.EngineError, 'complete exact MultiPV'):
            search(engine, chess.Board(), 1, multipv=3)

    def test_shared_prepared_position(self):
        games = {row['source_ordinal']: row for row in read_rows('data/derived/pal_css_2005_games.csv')}
        repeated = []
        for ordinal, reply in [('4', 'Ng3'), ('8', 'f4'), ('22', 'h4')]:
            board = chess.Board(games[ordinal]['initial_fen'])
            moves = games[ordinal]['moves_uci'].split()
            for move in moves[:26]:
                board.push_uci(move)
            repeated.append(' '.join(board.fen().split()[:4]))
            self.assertEqual(board.san(board.parse_uci(moves[26])), reply)
        self.assertEqual(len(set(repeated)), 1)
        self.assertLess(games['4']['date'], games['8']['date'])
        self.assertLess(games['8']['date'], games['22']['date'])

    def test_clock_reconstruction(self):
        games = {row['game_id']: row for row in read_rows('data/derived/pal_css_clock_games.csv')}
        grouped = defaultdict(list)
        for row in read_rows('data/derived/pal_css_move_times.csv'):
            grouped[row['game_id']].append(row)
        for game_id, rows in grouped.items():
            game = games[game_id]
            elapsed, missing = {1: 0, 0: 0}, {1: 0, 0: 0}
            board = chess.Board()
            self.assertEqual(len(rows), int(game['plies']))
            for ply, row in enumerate(rows, 1):
                self.assertEqual(int(row['ply']), ply)
                move = board.parse_uci(row['move_uci'])
                self.assertEqual(board.san(move), row['move_san'])
                board.push(move)
                side = ply % 2
                if row['elapsed_seconds']:
                    seconds = float(row['elapsed_seconds'])
                    self.assertGreaterEqual(seconds, 0)
                    elapsed[side] += seconds
                else:
                    missing[side] += 1
                for colour, parity, move_count in [('white', 1, (ply + 1) // 2), ('black', 0, ply // 2)]:
                    self.assertEqual(int(row[colour + '_missing_times']), missing[parity])
                    self.assertAlmostEqual(float(row[colour + '_elapsed_lower_seconds']), elapsed[parity])
                    if game['increment_seconds']:
                        expected = float(game['initial_seconds']) + float(game['increment_seconds']) * move_count - elapsed[parity]
                        self.assertAlmostEqual(float(row[colour + '_clock_upper_seconds']), expected)
                    else:
                        self.assertEqual(row[colour + '_clock_upper_seconds'], '')
        final = grouped['pal_final:18']
        self.assertEqual([(row['ply'], row['move_san']) for row in final if not row['elapsed_seconds']], [('30', 'Kh8')])

    def test_hydra_population(self):
        rows = read_rows('data/derived/hydra_results.csv')
        self.assertEqual({row['account']: float(row['points']) for row in rows}, {'zor_champ': 3.5, 'ares01': 4.0})
        self.assertEqual({row['account']: row['entry_type'] for row in rows}, {'zor_champ': 'engine_only', 'ares01': 'human_engine'})
        games = read_rows('data/derived/hydra_games.csv')
        self.assertEqual(len({row['game_id'] for row in games}), 16)
        self.assertNotIn('pal_2005_main:10', {row['game_id'] for row in games})

    def test_engine_histories_and_pairs(self):
        games = {row['source_ordinal']: row for row in read_rows('data/derived/pal_css_2005_games.csv')}
        cases = {row['case_id']: row for row in read_rows('data/curated/pal_css_2005_decisions.csv')}
        groups = defaultdict(list)
        for filename in ['pal_css_2005_case.csv', 'pal_css_2005_trajectory.csv', 'pal_css_2005_turning_points.csv']:
            for row in read_rows('data/derived/' + filename):
                game = games[row['source_ordinal']]
                expected = game['moves_uci'].split()[:int(row['ply']) - 1]
                if row['comparison'].startswith('reply_after_'):
                    case = cases[row['case_id']]
                    expected = game['moves_uci'].split()[:int(case['ply']) - 1]
                    expected.append(row['comparison'].removeprefix('reply_after_'))
                self.assertEqual(row['initial_fen'], game['initial_fen'])
                self.assertEqual(row['history_uci'].split(), expected)
                board = chess.Board(row['initial_fen'])
                for move in row['history_uci'].split():
                    board.push_uci(move)
                self.assertEqual(board.fen(), row['fen_before'])
                self.assertEqual(board.ply() + 1, int(row['ply']))
                self.assertEqual(board.san(board.parse_uci(row['move_uci'])), row['move_san'])
                pv = [chess.Move.from_uci(move) for move in row['pv_uci'].split()]
                self.assertEqual(board.variation_san(pv), row['pv_san'])
                self.assertEqual(pv[0].uci(), row['move_uci'])
                self.assertEqual(sum(int(row[key]) for key in ['white_win', 'draw', 'black_win']), 1000)
                if row['rank']:
                    key = row['case_id'], row['source_ordinal'], row['ply'], row['comparison'], row['node_budget']
                    groups[key].append(row)
        for key, rows in groups.items():
            ranks = sorted(int(row['rank']) for row in rows)
            self.assertEqual(ranks, list(range(1, len(rows) + 1)), key)
            self.assertEqual(len({row['move_uci'] for row in rows}), len(rows), key)
            self.assertEqual(len({row['depth'] for row in rows}), 1, key)
        for key, rows in groups.items():
            if key[3] == 'reported_pair':
                self.assertEqual({row['move_uci'] for row in rows}, {cases[key[0]]['move_uci'], cases[key[0]]['reported_alternative_uci']})

    def test_clock_case_histories(self):
        parsed = {}
        for row in read_rows('data/derived/clock_case_evaluations.csv'):
            name = row['source_file']
            if name not in parsed:
                raw = (Path('cache/sources') / name).read_bytes()
                if name.endswith('.zip'):
                    with ZipFile(io.BytesIO(raw)) as archive:
                        raw = archive.read(next(name for name in archive.namelist() if name.lower().endswith('.pgn')))
                pgn = io.StringIO(raw.decode('latin-1'))
                parsed[name] = list(iter(lambda: chess.pgn.read_game(pgn), None))
            game = parsed[name][int(row['source_ordinal']) - 1]
            board = game.board()
            expected = list(game.mainline_moves())[:int(row['ply']) - 1]
            for move in expected:
                board.push(move)
            self.assertEqual(row['history_uci'].split(), [move.uci() for move in expected])
            self.assertEqual(board.fen(), row['fen_before'])
            self.assertIn(board.parse_uci(row['move_uci']), board.legal_moves)
            board.variation_san([chess.Move.from_uci(move) for move in row['pv_uci'].split()])

    def test_symmetric_turning_points(self):
        cases = {}
        for row in read_rows('data/derived/pal_css_2005_turning_points.csv'):
            cases[row['case_id']] = row
        counts = defaultdict(int)
        for row in cases.values():
            counts[row['source_ordinal'], int(row['ply']) % 2] += 1
        self.assertEqual(dict(counts), {(ordinal, side): 3 for ordinal in ['13', '22', '26'] for side in [0, 1]})

    def test_engine_ladder_coverage(self):
        cases = read_rows('data/derived/decision_positions.csv')
        self.assertEqual(len(cases), 18)
        for case in cases:
            position_board(case)
        rows = read_rows('data/derived/engine_ladder.csv')
        expected = {(case['case_id'], engine, str(budget)) for case in cases
                    for engine in ['fruit-2.1', 'stockfish-4', 'stockfish-8', 'stockfish-12', 'stockfish-17.1']
                    for budget in [250000, 1000000, 4000000]}
        self.assertEqual(len(rows), len(expected))
        self.assertEqual({(row['case_id'], row['engine'], row['node_budget']) for row in rows}, expected)
        for row in rows:
            self.assertEqual(int(row['matches_played']), int(row['played_uci'] == row['recommended_uci']))
            self.assertGreater(int(row['search_nodes']), 0)
            if row['candidate_search_status'] != 'separate_forced_roots':
                expected_class = 'selected' if int(row['matches_played']) else 'unavailable'
                self.assertEqual(row['candidate_status'], expected_class)
                if expected_class == 'unavailable':
                    self.assertEqual(row['engine'], 'fruit-2.1')
                self.assertEqual(row['candidate_gap_cp'], '')
                continue
            scores = {label: chess.engine.Cp(int(row[label + '_forced_cp'])) if row[label + '_forced_cp']
                      else chess.engine.Mate(int(row[label + '_forced_mate'])) for label in ['played', 'reference']}
            self.assertEqual(row['candidate_status'], candidate_class(False, scores['played'], scores['reference'], 20))
            if row['candidate_gap_cp']:
                self.assertEqual(int(row['candidate_gap_cp']), scores['reference'].score() - scores['played'].score())

    def test_candidate_class_boundaries(self):
        cp, mate = chess.engine.Cp, chess.engine.Mate
        self.assertEqual(candidate_class(False, cp(0), cp(20), 20), 'near_equal')
        self.assertEqual(candidate_class(False, cp(0), cp(21), 20), 'rejected')
        self.assertEqual(candidate_class(False, cp(21), cp(0), 20), 'search_reversal')
        self.assertEqual(candidate_class(False, mate(3), mate(4), 20), 'search_reversal')
        self.assertEqual(candidate_class(False, mate(-3), cp(0), 20), 'rejected')
        self.assertEqual(candidate_class(True, cp(0), cp(0), 20), 'selected')

    def test_engine_repeatability(self):
        saved = json.loads(Path('data/derived/engine_repeatability.json').read_text())
        self.assertEqual({row['engine'] for row in saved['results']}, {'fruit-2.1', 'stockfish-4', 'stockfish-8',
                         'stockfish-12', 'stockfish-13', 'stockfish-14', 'stockfish-15', 'stockfish-16', 'stockfish-17.1'})
        for result in saved['results']:
            self.assertEqual(result['exact_search_repeatable'], result['runs'][0] == result['runs'][1])
            self.assertEqual(result['move_and_score_repeatable'], all(result['runs'][0][key] == result['runs'][1][key]
                             for key in ['move_uci', 'mover_cp', 'mover_mate']))
        for name, digest in saved['inputs_sha256'].items():
            self.assertEqual(hashlib.sha256(Path(name).read_bytes()).hexdigest(), digest)

    def test_restored_corpus(self):
        saved = json.loads(Path('data/curated/restored_corpus.json').read_text())
        if not Path(saved['destination']).exists():
            self.skipTest('optional restored corpus unavailable; local retired archive required')
        self.assertEqual(saved['lumbra_raw_pgn_members'], [])
        pgns = [row for row in saved['files'] if row['member'].endswith('.pgn')]
        self.assertEqual(len(pgns), 59)
        for row in saved['files']:
            path = Path(saved['destination']) / row['member']
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), row['sha256'])

    def test_saved_search_fingerprints(self):
        for name in ['pal_css_2005_case_config', 'engine_ladder_config', 'reference_comparisons_config']:
            config = json.loads(Path('data/derived/' + name + '.json').read_text())
            inputs = config.get('inputs_sha256', config.get('inputs', {}))
            for path, digest in inputs.items():
                self.assertEqual(hashlib.sha256(Path(path).read_bytes()).hexdigest(), digest, path)
            for name, digest in config.get('outputs', {}).items():
                self.assertEqual(hashlib.sha256((Path('data/derived') / name).read_bytes()).hexdigest(), digest)
        for name, output in [('engine_ladder_config', 'engine_ladder.csv'),
                             ('reference_comparisons_config', 'reference_comparisons.csv'),
                             ('clock_case_config', 'clock_case_evaluations.csv'),
                             ('pal_css_2005_turning_points_config', 'pal_css_2005_turning_points.csv')]:
            config = json.loads(Path('data/derived/' + name + '.json').read_text())
            key = 'output_sha256'
            self.assertEqual(hashlib.sha256(Path('data/derived/' + output).read_bytes()).hexdigest(), config[key])
            for name, digest in config.get('inputs_sha256', {}).items():
                path = Path(name) if '/' in name else Path('cache/sources') / name
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), digest)
        config = json.loads(Path('data/derived/pal_css_2005_case_config.json').read_text())
        turning = json.loads(Path('data/derived/pal_css_2005_turning_points_config.json').read_text())
        digest = hashlib.sha256(Path('data/derived/pal_css_2005_trajectory.csv').read_bytes()).hexdigest()
        self.assertEqual(digest, config['turning_points']['trajectory_sha256'])
        self.assertEqual(digest, turning['trajectory_sha256'])
        for build in json.loads(Path('data/derived/engine_builds.json').read_text()):
            self.assertEqual(hashlib.sha256(Path(build['binary']).read_bytes()).hexdigest(), build['binary_sha256'])
        builds = json.loads(Path('data/derived/engine_builds.json').read_text())
        saved = json.loads(Path('data/derived/engine_ladder_config.json').read_text())['engines']
        for current, old in zip(builds, saved, strict=True):
            for key in ['name', 'binary_sha256', 'options']:
                self.assertEqual(current[key], old[key])

    def test_panel_provenance(self):
        paths = list(Path('panels').glob('*.json'))
        self.assertEqual({path.stem for path in paths}, {'pal_css_2005_clock', 'prepared_long_think',
                         'engine_ladder', 'decision_explorer', 'preparation_accounts', 'freestyle_history',
                         'iccf_outcomes', 'nielsen_releases', 'rating_participation', 'advice_noise_floor'})
        for path in paths:
            panel = json.loads(path.read_text())
            for name, digest in panel['inputs_sha256'].items():
                self.assertEqual(hashlib.sha256(Path(name).read_bytes()).hexdigest(), digest, name)
            self.assertTrue(panel['limits'])

    def test_iccf_outcome_accounting(self):
        games = read_rows('data/curated/iccf_32_decisive_games.csv')
        players = read_rows('data/curated/iccf_32_players.csv')
        self.assertEqual(len({row['game_id'] for row in games}), 17)
        self.assertEqual(len(players), 17)
        self.assertEqual(sum(int(row['draws']) for row in players), 2 * 119)
        for player in players:
            self.assertEqual(sum(int(player[key]) for key in ['wins', 'draws', 'losses']), 16)
            self.assertEqual(sum(game['winner'] == player['player'] for game in games), int(player['wins']))
            self.assertEqual(sum(game['loser'] == player['player'] for game in games), int(player['losses']))
        counts = {category: sum(row['outcome_category'] == category for row in games)
                  for category in {row['outcome_category'] for row in games}}
        self.assertEqual(counts, {'reported_batch_resignation': 13, 'participant_contested_resignation': 1,
                                 'reported_input_error': 1, 'reported_mating_blunder': 1, 'reported_board_win': 1})
        for row in read_rows('data/curated/iccf_finals.csv'):
            self.assertEqual(int(row['draws']) + int(row['decisive_recorded']), int(row['games']))
            if row['edition'] == '33':
                self.assertEqual(row['decisive_recorded'], row['administrative_decisive'])

    def test_new_research_fingerprints(self):
        for name in ['nielsen_engine_builds_config', 'nielsen_releases_config', 'engine_build_checks_config',
                     'rating_participation_config', 'advice_noise_floor_config', 'online_standard_games_config',
                     'freestyle_2014_audit', 'research_figures_config']:
            saved = json.loads(Path('data/derived/' + name + '.json').read_text())
            for key in ['inputs_sha256', 'outputs_sha256']:
                for filename, digest in saved.get(key, {}).items():
                    self.assertEqual(hashlib.sha256(Path(filename).read_bytes()).hexdigest(), digest, filename)
        for build in json.loads(Path('data/derived/nielsen_engine_builds.json').read_text()):
            self.assertEqual(build['bench_nodes'], build['expected_bench_nodes'])
            self.assertEqual(hashlib.sha256(Path(build['binary']).read_bytes()).hexdigest(), build['binary_sha256'])

    def test_historical_rating_fields(self):
        from rating_participation import players
        sources = {row['year']: row for row in read_rows('data/curated/rating_sources.csv')}
        entries = list(players(sources['1997']))
        kasparov = next(row for row in entries if row['id'] == '4100018')
        self.assertEqual((kasparov['name'], kasparov['rating'], kasparov['birth_date']),
                         ('Kasparov, Garry', 2795, '1963.04.13'))
        self.assertTrue(any(row['rating'] >= 2250 and 'i' in row['flag'] for row in entries))
        counts = {row['year']: row for row in read_rows('data/derived/rating_participation.csv')}
        self.assertEqual(counts['1975']['listed_total'], '1534')
        self.assertEqual(counts['1975']['active_2250'], '')
        self.assertEqual(counts['1972']['membership_2250'], '')
        self.assertTrue(all(row['living_title_holders'] == '' for row in counts.values()))
        for row in counts.values():
            if row['active_2250'] and row['membership_2250']:
                self.assertLessEqual(int(row['active_2250']), int(row['membership_2250']))
        self.assertEqual(counts['2002']['membership_2250'], '')
        self.assertEqual(counts['2011']['status'], 'available')

    def test_nielsen_search_coverage(self):
        panel = json.loads(Path('panels/nielsen_releases.json').read_text())
        cases = {row['case_id']: row for row in panel['cases']}
        rows = read_rows('data/derived/nielsen_releases.csv')
        self.assertEqual(len(rows), 54)
        keys = {(row['case_id'], row['engine'], int(row['node_budget'])) for row in rows}
        self.assertEqual(len(keys), 54)
        for row in rows:
            board = position_board(cases[row['case_id']])
            self.assertIn(chess.Move.from_uci(row['recommended_uci']), board.legal_moves)
            self.assertEqual(board.san(chess.Move.from_uci(row['recommended_uci'])), row['recommended_san'])

    def test_matched_advice_and_activity_totals(self):
        preferences = read_rows('data/derived/advice_preferences.csv')
        repeated = {row['game_id'] for row in preferences if row['nodes'] == '400000'}
        self.assertEqual(len(repeated), 50)
        counts = defaultdict(int)
        for row in preferences:
            if row['game_id'] in repeated:
                counts[row['engine'], row['nodes']] += 1
        self.assertEqual(len(counts), 8)
        self.assertEqual(set(counts.values()), {50})
        threshold = {(row['year'], row['threshold']): row for row in read_rows('data/derived/rating_thresholds.csv')}
        for row in read_rows('data/derived/rating_activity_bridge.csv'):
            self.assertEqual(int(row['retained']) + int(row['gained_eligible']), int(row['active_2009']))
            for year in ['2008', '2009']:
                self.assertEqual(int(row['active_' + year]) + int(row['ambiguous_entries_' + year]),
                                 int(threshold[year, row['threshold']]['active']))

    def test_literature_copy_hashes(self):
        copies = json.loads(Path('data/curated/literature_catalogue.json').read_text())['copies']
        self.assertEqual(len({row['file'] for row in copies}), len(copies))
        for row in copies:
            self.assertEqual(hashlib.sha256(Path(row['file']).read_bytes()).hexdigest(), row['sha256'])


if __name__ == '__main__':
    unittest.main()
