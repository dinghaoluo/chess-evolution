'''
Created on 16 October 2026

check pawn identity, opportunity denominators, symmetry, and the move boundary

@author: Dinghao Luo
'''

#%% imports
import unittest

import chess
import chess.pgn

from pawn_patterns import detect_patterns


#%% fixtures
START = '2bqk2r/p7/8/8/8/8/P6P/R1BQK1NR w KQk - 0 1'


def fixture(fen: str, moves: list[str]) -> chess.pgn.Game:
    board = chess.Board(fen)
    game = chess.pgn.Game()
    game.setup(board)
    node = game
    for san in moves:
        move = board.parse_san(san)
        node = node.add_variation(move)
        board.push(move)
    return game


def own(game: chess.pgn.Game, colour: str = 'white', file: str = 'h') -> dict:
    return next(row for row in detect_patterns(game) if row['colour'] == colour and row['pawn_file'] == file)


class PawnPatternChecks(unittest.TestCase):
    def test_event_and_denominators(self):
        game = fixture(START, ['h4', 'O-O', 'h5'])
        self.assertTrue(all(own(game)[key] for key in ['event', 'castling_opportunity', 'strict_opportunity']))
        self.assertEqual(own(game)['event_ply'], 3)
        self.assertFalse(own(game, 'black')['castling_opportunity'])

    def test_colour_symmetry(self):
        game = fixture(START, ['h4', 'O-O', 'h5'])
        board = game.board().mirror()
        mirror = chess.pgn.Game()
        mirror.setup(board)
        node = mirror
        for move in game.mainline_moves():
            transformed = chess.Move(chess.square_mirror(move.from_square), chess.square_mirror(move.to_square))
            self.assertIn(transformed, board.legal_moves)
            node = node.add_variation(transformed)
            board.push(transformed)
        self.assertTrue(own(mirror, 'black')['event'])

    def test_a_pawn_comparison(self):
        self.assertTrue(own(fixture(START, ['a4', 'O-O', 'a5']), file='a')['event'])

    def test_missing_queen_and_queenside_castle(self):
        no_queen = START.replace('2bqk2r', '2b1k2r')
        result = own(fixture(no_queen, ['h4', 'O-O', 'h5']))
        self.assertTrue(result['castling_opportunity'])
        self.assertFalse(result['strict_opportunity'])
        self.assertFalse(result['event'])
        queenside = START.replace('2bqk2r/p7', 'r3k2r/p2q4').replace('KQk ', 'KQkq ')
        self.assertFalse(own(fixture(queenside, ['h4', 'O-O-O', 'h5']))['castling_opportunity'])

    def test_wrong_pawn_captures_onto_file(self):
        start = START.replace('/8/8/8/8/P6P/', '/8/7p/6P1/8/P6P/')
        result = own(fixture(start, ['Nf3', 'O-O', 'gxh5']))
        self.assertTrue(result['strict_opportunity'])
        self.assertFalse(result['event'])
        self.assertIsNone(result['first_arrival_ply'])

    def test_original_pawn_returns_after_capture(self):
        start = '2bqk2r/p7/8/7p/8/6p1/P6P/R1BQK1NR w KQk - 0 1'
        result = own(fixture(start, ['hxg3', 'O-O', 'g4', 'a6', 'gxh5']))
        self.assertTrue(result['event'])

    def test_en_passant_removes_original_pawn_identity(self):
        start = '2bqk2r/pppp1ppp/8/8/1p6/8/P6P/RNBQK1NR w KQk - 0 1'
        game = fixture(start, ['a4', 'bxa3', 'Nc3', 'O-O', 'Na4', 'a6', 'Nb6', 'h6', 'Nc4', 'd6', 'Na5'])
        result = own(game, file='a')
        self.assertTrue(result['strict_opportunity'])
        self.assertFalse(result['event'])
        self.assertIsNone(result['first_arrival_ply'])

    def test_first_arrival_precedes_castling(self):
        result = own(fixture(START, ['h4', 'a6', 'h5', 'O-O', 'h6']))
        self.assertEqual(result['first_arrival_ply'], 3)
        self.assertFalse(result['event'])

    def test_material_and_king_requirements(self):
        start = '3qk2r/p7/8/8/8/8/P6P/3QK2R w Kk - 0 1'
        self.assertFalse(own(fixture(start, ['h4', 'O-O', 'h5']))['strict_opportunity'])
        result = own(fixture(START, ['Nf3', 'O-O', 'h4', 'Kf7', 'h5']))
        self.assertTrue(result['strict_opportunity'])
        self.assertFalse(result['event'])

    def test_move_24_and_25(self):
        for move_number, expected in [(22, True), (23, True), (24, False)]:
            start = START.rsplit(' ', 1)[0] + ' ' + str(move_number)
            game = fixture(start, ['h4', 'O-O', 'h5'])
            self.assertEqual(own(game)['event'], expected)
        game = fixture(START.rsplit(' ', 1)[0] + ' 24', ['Nf3', 'O-O'])
        self.assertTrue(own(game)['castling_opportunity'])
        self.assertFalse(own(game)['strict_opportunity'])


if __name__ == '__main__':
    unittest.main()
