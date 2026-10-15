'''
Created on 4 August 2026

plot reviewed position novelty and comparison-archive sensitivity

@author: Dinghao Luo
'''

#%% imports
import csv
from collections import defaultdict
from pathlib import Path
from statistics import median

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


#%% load
data = []

with Path('data/novelty.csv').open() as source:
    for row in csv.DictReader(source):
        if row['first_novelty_ply'] and int(row['reference_games']) > 0:
            data.append((int(row['year']), int(row['first_novelty_ply'])))


#%% median per year
by_year = defaultdict(list)
for y, p in data:
    by_year[y].append(p)

med_years = sorted(by_year)
medians = [median(by_year[y]) for y in med_years]

sampled = defaultdict(list)
with Path('data/novelty_sensitivity.csv').open() as source:
    for row in csv.DictReader(source):
        if row['first_novelty_ply']:
            sampled[int(row['year']), int(row['seed'])].append(int(row['first_novelty_ply']))
sample_years = sorted({year for year, _ in sampled})
seeds = sorted({seed for _, seed in sampled})
sample_medians = [
    [median(sampled[year, seed]) for seed in seeds] for year in sample_years
]
sample_low, sample_mid, sample_high = np.percentile(sample_medians, [10, 50, 90], axis=1)

with Path('data/novelty_year_summary.csv').open('w', newline='') as destination:
    writer = csv.writer(destination, lineterminator='\n')
    writer.writerow(['year', 'games', 'growing_archive_median', 'fixed_100_median',
                     'fixed_100_p10', 'fixed_100_p90'])
    for year, value in zip(med_years, medians):
        if year in sample_years:
            index = sample_years.index(year)
            sampled_values = [sample_mid[index], sample_low[index], sample_high[index]]
        else:
            sampled_values = ['', '', '']
        writer.writerow([year, len(by_year[year]), value, *sampled_values])
growing_slope = np.polyfit(sample_years, [median(by_year[y]) for y in sample_years], 1)[0] * 100
fixed_slope = np.polyfit(sample_years, sample_mid, 1)[0] * 100
print(f'descriptive plies per century: growing archive {growing_slope:.2f}; fixed 100 {fixed_slope:.2f}')


#%% plot
fig, ax = plt.subplots(figsize=(12, 5))
years, plies = zip(*data)
ax.scatter(years, plies, alpha=0.15, s=8, color='steelblue', label='individual games; all earlier events')
ax.plot(med_years, medians, color='darkred', linewidth=1.5, label='median; all earlier events')
ax.plot(sample_years, sample_mid, color='black', linewidth=1.5, label='median; 100 earlier games')
ax.fill_between(sample_years, sample_low, sample_high, color='grey', alpha=0.25,
                label='10th to 90th percentile across 20 archive samples')
ax.set_xlabel('championship start year')
ax.set_ylabel('first unseen position (ply)')
ax.set_title('Main title line: played classical games, compared with earlier events')
ax.legend(fontsize=8, loc='upper left')
fig.tight_layout()
fig.savefig('plots/novelty_over_time.png', dpi=150)
plt.close(fig)
