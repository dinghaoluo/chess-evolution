'''
Created on 4 August 2026

plot first_novelty_ply over time

@author: Dinghao Luo
'''

#%% imports
import csv
import matplotlib.pyplot as plt
from collections import defaultdict
from pathlib import Path


#%% load
data = []

with open(Path('data/novelty.csv')) as f:
    for row in csv.DictReader(f):
        year = row['date'][:4]
        if year == '????' or not row['first_novelty_ply']:
            continue
        data.append((int(year), int(row['first_novelty_ply'])))

years, plies = zip(*data)


#%% median per year
by_year = defaultdict(list)
for y, p in data:
    by_year[y].append(p)

med_years = sorted(by_year)
medians = [sorted(by_year[y])[len(by_year[y]) // 2] for y in med_years]


#%% plot
fig, ax = plt.subplots(figsize=(12, 5))
ax.scatter(years, plies, alpha=0.15, s=8, color='steelblue', label='individual games')
ax.plot(med_years, medians, color='darkred', linewidth=1.5, label='median per year')
ax.set_xlabel('year')
ax.set_ylabel('first novelty ply')
ax.set_title('When does a championship game first reach a novel position?')
ax.legend()
plt.tight_layout()
plt.savefig('plots/novelty_over_time.png', dpi=150)
plt.show()
