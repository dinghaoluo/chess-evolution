'''
Created on 16 October 2026

sum complete years of standard rated games from the official Lichess index

@author: Dinghao Luo
'''

#%% imports
import csv
import hashlib
import json
from pathlib import Path

from bs4 import BeautifulSoup


#%% main
def main() -> None:
    source = Path('cache/research/lichess-database-20261016.html')
    soup = BeautifulSoup(source.read_bytes(), 'html.parser')
    monthly = {}
    for row in soup.select('#standard_games tbody tr'):
        cells = row.find_all('td')
        if cells[0].get_text(strip=True).startswith('Total:'):
            continue
        year = int(cells[0].get_text(strip=True)[:4])
        monthly.setdefault(year, []).append(int(cells[2].get_text(strip=True).replace(',', '')))
    rows = [{'year': year, 'games': sum(counts), 'months': len(counts)}
            for year, counts in sorted(monthly.items()) if year >= 2019 and len(counts) == 12]
    output = Path('data/derived/online_standard_games.csv')
    with output.open('w', newline='') as destination:
        writer = csv.DictWriter(destination, fieldnames=['year', 'games', 'months'], lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
    config = {'source_url': 'https://database.lichess.org/#standard_games', 'accessed': '2026-10-16',
              'inputs_sha256': {str(path): hashlib.sha256(path.read_bytes()).hexdigest()
                                for path in [source, Path('scripts/online_participation.py')]},
              'outputs_sha256': {str(output): hashlib.sha256(output.read_bytes()).hexdigest()},
              'limits': ['Monthly export counts, summed only for complete calendar years.',
                         'Standard denotes the chess variant, including fast clocks; it does not mean classical time control.',
                         'Games are not unique people, FIDE members, employment, or a causal engine effect.',
                         'No time-control-specific rapid growth series was verified.']}
    Path('data/derived/online_standard_games_config.json').write_text(json.dumps(config, indent=2) + '\n')


if __name__ == '__main__':
    main()
