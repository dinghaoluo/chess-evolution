'''
Created on 2 August 2026

parse pgnmentor pgns into a per-ply csv with fen positions

@author: Dinghao Luo
'''

#%% imports
import csv
import chess.pgn
from pathlib import Path

#%% paths
RAW = Path('data/raw/pgnmentor')
OUT = Path('data/games.csv')

COLS = [
    'game_id', 'source_file', 'event', 'date',
    'white', 'black', 'result', 'eco',
    'ply', 'move', 'move_uci', 'fen',
]

#%% main
game_id = 0

with open(OUT, 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=COLS)
    writer.writeheader()

    for pgn_file in sorted(RAW.glob('*.pgn')):
        with open(pgn_file) as pf:
            while True:
                game = chess.pgn.read_game(pf)
                if game is None:
                    break

                game_id += 1
                h = game.headers
                meta = {
                    'game_id': game_id,
                    'source_file': pgn_file.name,
                    'event': h.get('Event', ''),
                    'date': h.get('Date', ''),
                    'white': h.get('White', ''),
                    'black': h.get('Black', ''),
                    'result': h.get('Result', ''),
                    'eco': h.get('ECO', ''),
                }

                board = game.board()
                for i, move in enumerate(game.mainline_moves(), 1):
                    san = board.san(move)
                    board.push(move)
                    writer.writerow({
                        **meta,
                        'ply': i,
                        'move': san,
                        'move_uci': move.uci(),
                        'fen': board.fen(),
                    })
