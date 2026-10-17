'''
Created on 16 October 2026

preserve the TWIC headers without inferring live assistance from account names

@author: Dinghao Luo
'''

#%% imports
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

import chess.pgn


#%% main
def main() -> None:
    source_path = Path('cache/research/twic-freestyle14.pgn')
    games, names = [], Counter()
    scores = []
    with source_path.open(encoding='utf-8-sig') as source:
        while (game := chess.pgn.read_game(source)) is not None:
            assert not game.errors
            games.append({'source_ordinal': len(games) + 1, 'headers': dict(game.headers),
                          'plies': game.end().ply()})
            for colour in ['White', 'Black']:
                names[colour, game.headers[colour]] += 1
                if game.headers[colour] == 'Intagrand':
                    result = game.headers['Result']
                    scores.append(0.5 if result == '1/2-1/2' else int((result == '1-0') == (colour == 'White')))
    assert len(games) == 435 and len(scores) == 29 and sum(scores) == 20.5
    outputs = [Path('data/derived/freestyle_2014_headers.json'), Path('data/derived/freestyle_2014_names.csv')]
    outputs[0].write_text(json.dumps(games, indent=2, ensure_ascii=False) + '\n')
    with outputs[1].open('w', newline='') as target:
        writer = csv.writer(target, lineterminator='\n')
        writer.writerow(['colour', 'raw_name', 'appearances', 'explicit_name_suffix', 'live_assistance'])
        for (colour, name), count in sorted(names.items()):
            suffix = name[min([name.find(char) for char in ['(', '['] if char in name], default=len(name)):]
            writer.writerow([colour, name, count, suffix, 'unclassified_from_header'])
    saved = {'games': len(games), 'intagrand_games': len(scores), 'intagrand_points': sum(scores),
             'header_fields': dict(Counter(key for game in games for key in game['headers'])),
             'inputs_sha256': {str(source_path): hashlib.sha256(source_path.read_bytes()).hexdigest()},
             'outputs_sha256': {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in outputs},
             'limits': ['435 legal main lines cover a 30-entry single round robin; aliases and replacements need separate identity evidence.',
                        'Engine names occur in White/Black account-name suffixes; no WhiteEngine, BlackEngine, WhiteType or BlackType tags exist.',
                        'A suffix does not prove engine-only play; absence does not prove live human intervention.',
                        'TimeControl appears in three games only; no Termination tags are present.',
                        'TWIC identifies Intagrand as Anson Williams and helpers; the PGNs confirm 20.5/29, not the introductory prose total of 29.']}
    Path('data/derived/freestyle_2014_audit.json').write_text(json.dumps(saved, indent=2) + '\n')
    print('435 TWIC games audited; Intagrand 20.5/29; entry mode cannot be inferred from headers')


if __name__ == '__main__':
    main()
