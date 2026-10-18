'''
Created on 16 October 2026

detect the frozen early h-pawn pattern and its a-pawn comparison

@author: Dinghao Luo
'''

#%% imports
import chess
import chess.pgn


#%% detector
def material_and_king(board: chess.Board, attacker: chess.Color) -> bool:
    opponent = not attacker
    king = board.king(opponent)
    return (king is not None and chess.square_file(king) in [6, 7]
            and all(board.pieces(chess.QUEEN, colour) for colour in chess.COLORS)
            and sum(len(board.pieces(piece, colour)) for piece in [chess.ROOK, chess.BISHOP, chess.KNIGHT]
                    for colour in chess.COLORS) >= 4)


def detect_patterns(game: chess.pgn.Game) -> list[dict]:
    board = game.board()
    assert not board.chess960 and not game.errors
    original_pawns = {}
    for colour in chess.COLORS:
        for file in ['a', 'h']:
            square = chess.parse_square(file + ('2' if colour else '7'))
            original_pawns[colour, file] = square if board.piece_at(square) == chess.Piece(chess.PAWN, colour) else None
    castled = {colour: False for colour in chess.COLORS}
    first_arrival = set()
    results = {(colour, file): {'colour': 'white' if colour else 'black', 'pawn_file': file,
                               'castling_opportunity': False, 'strict_opportunity': False,
                               'event': False, 'first_arrival_ply': None, 'event_ply': None}
               for colour in chess.COLORS for file in ['a', 'h']}
    for move in game.mainline_moves():
        if board.fullmove_number > 24:
            break
        mover = board.turn
        for file in ['a', 'h']:
            if castled[not mover] and material_and_king(board, mover):
                results[mover, file]['strict_opportunity'] = True
        kingside_castle = board.is_kingside_castling(move)
        captured_square = move.to_square
        if board.is_en_passant(move):
            captured_square += -8 if mover else 8
        moving_pawns = [key for key, square in original_pawns.items() if square == move.from_square]
        for key, square in original_pawns.items():
            if square == captured_square and key not in moving_pawns:
                original_pawns[key] = None
        board.push(move)
        if kingside_castle:
            castled[mover] = True
        for key in moving_pawns:
            original_pawns[key] = move.to_square if not move.promotion else None
            colour, file = key
            ranks = [4, 5] if colour else [3, 2]
            if (key in first_arrival or original_pawns[key] is None
                    or chess.square_file(move.to_square) != chess.FILE_NAMES.index(file)
                    or chess.square_rank(move.to_square) not in ranks):
                continue
            first_arrival.add(key)
            result = results[key]
            result['first_arrival_ply'] = board.ply()
            if castled[not colour] and material_and_king(board, colour):
                result['event'] = True
                result['event_ply'] = board.ply()
    for (colour, file), result in results.items():
        result['castling_opportunity'] = castled[not colour]
    return list(results.values())
