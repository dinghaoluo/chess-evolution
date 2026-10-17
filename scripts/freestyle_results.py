'''
Created on 16 October 2026

count Hydra results and keep reported event comparisons separate

@author: Dinghao Luo
'''

#%% imports
import csv
from pathlib import Path


#%% main
def main() -> None:
    curated = Path('data/curated')
    derived = Path('data/derived')
    with (derived / 'pal_css_clock_games.csv').open() as source:
        games = list(csv.DictReader(source))
    with (curated / 'freestyle_entries.csv').open() as source:
        entries = list(csv.DictReader(source))
    matches, summaries = [], []
    for entry in entries:
        own = []
        for game in games:
            if (game['edition'], game['stage'], game['accepted_for_timing']) != (entry['edition'], entry['stage'], '1'):
                continue
            names = {side: game[side].split(',')[0].strip().casefold() for side in ['white', 'black']}
            if entry['account'] not in names.values():
                continue
            side = next(side for side in names if names[side] == entry['account'])
            score = 0.5 if game['result'] == '1/2-1/2' else int((game['result'] == '1-0') == (side == 'white'))
            row = {'account': entry['account'], 'entry_type': entry['entry_type'], 'game_id': game['game_id'],
                   'round': game['round'], 'side': side, 'opponent': game['black' if side == 'white' else 'white'],
                   'score': score, 'opponent_type': 'unclassified', 'source_url': entry['source_url']}
            own.append(row)
        assert len(own) == 8, entry['account']
        matches.extend(own)
        summaries.append({**entry, 'games': len(own), 'wins': sum(row['score'] == 1 for row in own),
                          'draws': sum(row['score'] == 0.5 for row in own), 'losses': sum(row['score'] == 0 for row in own),
                          'points': sum(row['score'] for row in own)})
    assert sum(row['points'] for row in summaries) == 7.5
    with (curated / 'freestyle_comparisons.csv').open() as source:
        comparisons = list(csv.DictReader(source))
    for row in comparisons:
        counts = [int(row[key]) for key in ['human_wins', 'draws', 'engine_wins']]
        row.update({'games': sum(counts), 'human_points': counts[0] + counts[1] / 2,
                    'engine_points': counts[2] + counts[1] / 2})
        assert int(row['human_white_games']) + int(row['human_black_games']) == row['games']
    with (curated / 'freestyle_events.csv').open() as source:
        events = list(csv.DictReader(source))
    for event in events:
        final = [game for game in games if game['edition'] == event['edition'] and game['stage'] == 'final']
        if not final:
            continue
        points = {}
        for game in final:
            white = 0.5 if game['result'] == '1/2-1/2' else int(game['result'] == '1-0')
            for side, score in [('white', white), ('black', 1 - white)]:
                name = game[side].split(',')[0].strip().casefold()
                points[name] = points.get(name, 0) + score
        assert points[event['winner'].casefold()] == max(points.values())
        event['winner_points'] = points[event['winner'].casefold()]
    for name, rows in [('hydra_games.csv', matches), ('hydra_results.csv', summaries),
                       ('freestyle_comparisons.csv', comparisons), ('freestyle_events.csv', events)]:
        with (derived / name).open('w', newline='') as destination:
            writer = csv.DictWriter(destination, fieldnames=list(rows[0]), lineterminator='\n')
            writer.writeheader()
            writer.writerows(rows)


if __name__ == '__main__':
    main()
