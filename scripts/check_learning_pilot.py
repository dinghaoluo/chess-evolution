'''
Created on 16 October 2026

check loss perspective, mate handling, identity conflicts and pilot sampling

@author: Dinghao Luo
'''

#%% imports
import csv
import hashlib
import json
import unittest
from collections import Counter
from pathlib import Path

import chess
import chess.engine

from join_pilot_birth_years import birth_year, nearest_january
from sample_learning_pilot import date_interval, names_agree
from score_learning_pilot import move_metrics


#%% scientific checks
class LearningChecks(unittest.TestCase):
    def test_mover_perspective_and_reversed_rankings(self):
        played, recommendation = chess.Move.from_uci('e7e5'), chess.Move.from_uci('d7d5')
        infos = [{'pv': [played], 'wdl': chess.engine.PovWdl(chess.engine.Wdl(100, 700, 200), chess.WHITE),
                  'score': chess.engine.PovScore(chess.engine.Cp(-50), chess.WHITE)},
                 {'pv': [recommendation], 'wdl': chess.engine.PovWdl(chess.engine.Wdl(50, 650, 300), chess.WHITE),
                  'score': chess.engine.PovScore(chess.engine.Cp(-150), chess.WHITE)}]
        result = move_metrics(infos, played, recommendation, chess.BLACK)
        self.assertAlmostEqual(result['expected_loss'], 0.075)
        self.assertEqual(result['cp_loss'], 100)
        reversed_result = move_metrics(infos, recommendation, played, chess.BLACK)
        self.assertEqual(reversed_result['expected_loss'], 0)
        self.assertTrue(reversed_result['ranking_reversed'])
        self.assertEqual(reversed_result['signed_cp_loss'], -100)
        self.assertAlmostEqual(reversed_result['move_accuracy'], 100, places=3)

    def test_mate_comparisons_stay_outside_cp_denominator(self):
        played, recommendation = chess.Move.from_uci('e2e4'), chess.Move.from_uci('d2d4')
        infos = [{'pv': [played], 'wdl': chess.engine.PovWdl(chess.engine.Wdl(0, 0, 1000), chess.WHITE),
                  'score': chess.engine.PovScore(chess.engine.Mate(-3), chess.WHITE)},
                 {'pv': [recommendation], 'wdl': chess.engine.PovWdl(chess.engine.Wdl(1000, 0, 0), chess.WHITE),
                  'score': chess.engine.PovScore(chess.engine.Mate(2), chess.WHITE)}]
        result = move_metrics(infos, played, recommendation, chess.WHITE)
        self.assertEqual(result['expected_loss'], 1)
        self.assertIsNone(result['cp_loss'])
        self.assertTrue(result['mate_comparison'])
        self.assertEqual(result['move_accuracy'], 0)

    def test_wrong_player_copies_do_not_pass_name_check(self):
        self.assertFalse(names_agree('Ydo, Pim', 'Ye, Jiangchuan CHN'))
        self.assertFalse(names_agree('Ghijsen, Pim', 'Gheorghiu, Florin ROU'))
        self.assertTrue(names_agree('Gheorghiu, F', 'Gheorghiu, Florin ROU'))
        self.assertTrue(names_agree('Gürel, Ediz', 'Gurel, Ediz TUR'))

    def test_date_and_century_uncertainty(self):
        self.assertEqual(date_interval('1985.11.??'), ('1985.11.01', '1985.11.30'))
        self.assertEqual(nearest_january('1985.11.15'), 1986)
        self.assertEqual(nearest_january('2015.04.19'), 2015)
        self.assertEqual(birth_year('17.01.72', 2005), 1972)
        self.assertIsNone(birth_year('00.00.05', 2005))
        self.assertIsNone(birth_year('0', 2024))
        self.assertIsNone(birth_year('', 1986))

    def test_sample_caps_and_source_scores(self):
        with Path('data/derived/learning_pilot_sample.csv').open() as source:
            rows = list(csv.DictReader(source))
        self.assertTrue(all(count == 1 for count in Counter((row['year'], row['player_key']) for row in rows).values()))
        self.assertTrue(all(count <= 50 for count in Counter((row['year'], row['band']) for row in rows).values()))
        games = {item['game_id']: item for item in (json.loads(line) for line in Path('data/derived/learning_pilot_pool.jsonl').read_text().splitlines())}
        for row in rows:
            game = games[row['game_id']]
            colour = row['colour'].title()
            self.assertEqual(row['pgn_elo'], game['headers'][colour + 'Elo'])
            if 'reference_headers' in game:
                self.assertTrue(all(names_agree(game['headers'][side], game['reference_headers'][side]) for side in ['White', 'Black']))

    def test_saved_learning_histories_and_common_root_scores(self):
        config = json.loads(Path('data/derived/learning_pilot_scoring_config.json').read_text())
        sample = list(csv.DictReader(Path('data/derived/learning_pilot_sample.csv').read_text().splitlines()))
        colours = {(row['game_id'], row['colour']) for row in sample}
        for item in config['game_outputs']:
            groups = {}
            for name, fingerprint in item['outputs_sha256'].items():
                path = Path(name)
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), fingerprint)
                if not name.endswith('_searches.jsonl'):
                    continue
                for row in map(json.loads, path.read_text().splitlines()):
                    board = chess.Board()
                    for value in row['history_uci'].split():
                        board.push_uci(value)
                    self.assertEqual(board.fen(), row['fen_before'])
                    self.assertEqual(board.ply() + 1, row['ply'])
                    self.assertIn((item['game_id'], 'white' if board.turn else 'black'), colours)
                    self.assertIn(board.fullmove_number, range(9, 61))
                    self.assertEqual(sum(row[key] for key in ['white_win', 'draw', 'black_win']), 1000)
                    self.assertIn(board.parse_uci(row['move_uci']), board.legal_moves)
                    groups.setdefault((row['search_id'], row['comparison']), []).append(row)
            for rows in groups.values():
                self.assertEqual(len({row['depth'] for row in rows}), 1)
                self.assertEqual(len({row['move_uci'] for row in rows}), len(rows))

    def test_learning_fingerprints_and_opportunity_counts(self):
        for name in ['learning_header_audit_config', 'learning_pilot_sample_config', 'learning_pilot_birth_config',
                     'learning_pilot_scoring_config', 'pawn_pattern_config', 'advice_summary_config']:
            config = json.loads(Path('data/derived/' + name + '.json').read_text())
            for key in ['inputs_sha256', 'outputs_sha256']:
                for path, fingerprint in config.get(key, {}).items():
                    self.assertEqual(hashlib.sha256(Path(path).read_bytes()).hexdigest(), fingerprint, path)
        rows = list(csv.DictReader(Path('data/derived/pawn_pattern_counts.csv').read_text().splitlines()))
        for row in rows:
            self.assertLessEqual(int(row['event']), int(row['strict_opportunity']))
            self.assertLessEqual(int(row['strict_opportunity']), int(row['castling_opportunity']))
            self.assertLessEqual(int(row['castling_opportunity']), int(row['player_games']))

    def test_advice_sample_and_judge(self):
        config = json.loads(Path('data/derived/advice_config.json').read_text())
        for key in ['inputs_sha256', 'outputs_sha256']:
            for path, fingerprint in config[key].items():
                self.assertEqual(hashlib.sha256(Path(path).read_bytes()).hexdigest(), fingerprint, path)
        sample_path = Path('data/derived/advice_sample.csv')
        sample = list(csv.DictReader(sample_path.read_text().splitlines()))
        self.assertEqual(hashlib.sha256(sample_path.read_bytes()).hexdigest(), config['sample_sha256_before_search'])
        self.assertEqual(len(sample), 500)
        self.assertEqual(len({row['game_id'] for row in sample}), 500)
        self.assertEqual(sum(row['stability_position'] == 'True' for row in sample), 50)
        judges = {}
        for row in map(json.loads, Path('data/derived/advice_searches.jsonl').read_text().splitlines()):
            board = chess.Board()
            for value in row['history_uci'].split():
                board.push_uci(value)
            self.assertEqual(board.fen(), row['fen_before'])
            self.assertIn(board.parse_uci(row['move_uci']), board.legal_moves)
            if row['stage'] == 'judge':
                self.assertEqual(sum(row[key] for key in ['white_win', 'draw', 'black_win']), 1000)
                judges.setdefault((row['case_id'], row['node_budget']), []).append(row)
        for rows in judges.values():
            self.assertEqual(len({row['depth'] for row in rows}), 1)
            self.assertEqual(len({row['move_uci'] for row in rows}), len(rows))


if __name__ == '__main__':
    unittest.main()
