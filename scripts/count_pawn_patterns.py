'''
Created on 16 October 2026

count the frozen pawn patterns in the verified classical event pool

@author: Dinghao Luo
'''

#%% imports
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

import chess
import chess.pgn

from pawn_patterns import detect_patterns


#%% main
def main() -> None:
    source = Path('data/derived/learning_pilot_pool.jsonl')
    counts, rows = Counter(), []
    for line in source.read_text().splitlines():
        item = json.loads(line)
        game, node = chess.pgn.Game(), None
        node = game
        for value in item['moves_uci'].split():
            node = node.add_main_variation(chess.Move.from_uci(value))
        for result in detect_patterns(game):
            colour = result['colour'].title()
            elo = item['headers'].get(colour + 'Elo', '')
            if not elo.isdigit() or int(elo) < 2200:
                continue
            rating = int(elo)
            band = '2600+' if rating >= 2600 else '2400-2599' if rating >= 2400 else '2200-2399'
            row = {'game_id': item['game_id'], 'year': item['year'], 'event_id': item['event_id'],
                   'band': band, 'pgn_elo': rating, 'player': item['headers'][colour], **result}
            rows.append(row)
            key = item['year'], band, result['pawn_file']
            counts[key, 'player_games'] += 1
            for label in ['castling_opportunity', 'strict_opportunity', 'event']:
                counts[key, label] += result[label]
    summary = []
    for key in sorted({key for key, quantity in counts}):
        row = dict(zip(['year', 'band', 'pawn_file'], key))
        row.update({label: counts[key, label] for label in ['player_games', 'castling_opportunity', 'strict_opportunity', 'event']})
        for denominator in ['castling_opportunity', 'strict_opportunity']:
            row['rate_per_' + denominator] = row['event'] / row[denominator] if row[denominator] else None
        summary.append(row)
    outputs = []
    for name, values in [('pawn_pattern_player_games', rows), ('pawn_pattern_counts', summary)]:
        path = Path('data/derived/' + name + '.csv')
        with path.open('w', newline='') as destination:
            writer = csv.DictWriter(destination, fieldnames=list(values[0]), lineterminator='\n')
            writer.writeheader()
            writer.writerows(values)
        outputs.append(path)
    inputs = [source, Path(__file__), Path('scripts/pawn_patterns.py'), Path('notes/hypotheses.md'), Path('data/derived/learning_pilot_sample_config.json')]
    config = {'inputs_sha256': {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in inputs},
              'outputs_sha256': {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in outputs},
              'limits': ['Census of eligible mover-rated sides in the restricted verified event pool, not representative historical chess.',
                         'Style events are not quality gains or direct evidence of engine teaching.',
                         'Multiple games per player and both sides per game remain dependent; no trend fit or sampling interval is reported.',
                         'Original mover PGN Elo defines bands; disagreements with independent event-archive ratings are not silently replaced.',
                         'Eligibility exclusions and differing event coverage make cross-year rates unsuitable as a historical adoption curve.']}
    Path('data/derived/pawn_pattern_config.json').write_text(json.dumps(config, indent=2) + '\n')
    print(len(rows), 'player-game/file observations counted')


if __name__ == '__main__':
    main()
