'''
Created on 4 August 2026

plot championship departures from earlier recorded positions

@author: Dinghao Luo
'''

#%% imports
import csv
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np
import seaborn as sns


#%% annual medians
with Path('data/master_novelty_years.csv').open() as source:
    summary = list(csv.DictReader(source))
years = np.array([int(row['year']) for row in summary])
medians = np.array([float(row['prior_year_first_new_ply_median']) for row in summary])
# leave a quartile blank if censoring prevents its estimation
q25 = np.array([float(row['prior_year_first_new_ply_q25'] or np.nan) for row in summary])
q75 = np.array([float(row['prior_year_first_new_ply_q75'] or np.nan) for row in summary])
with Path('data/novelty_trend_tests.csv').open() as source:
    trend = next(row for row in csv.DictReader(source) if row['measure'] == 'full_reference'
                 and row['start_year'] == '1886' and row['bandwidth_years'] == '10')


#%% figure
font_manager.fontManager.addfont('plots/fonts/Piazzolla-Regular.ttf')
sns.set_theme(style='ticks', rc={
    'font.family': 'Piazzolla', 'font.size': 12,
    'axes.labelsize': 12, 'xtick.labelsize': 11, 'ytick.labelsize': 11,
    'axes.edgecolor': '#cfd3d0', 'axes.linewidth': 0.6,
    'text.color': '#2c3133', 'axes.labelcolor': '#2c3133',
    'xtick.color': '#5d6465', 'ytick.color': '#5d6465',
    'figure.facecolor': '#f2f2ed', 'axes.facecolor': '#f2f2ed',
    'savefig.facecolor': '#f2f2ed', 'pdf.fonttype': 42, 'svg.fonttype': 'path',
})
fig, ax = plt.subplots(figsize=(8.8, 4.3))
fig.subplots_adjust(left=0.065, right=0.965, top=0.79, bottom=0.15)
fig.text(0.065, 0.95, 'First unrecorded position', fontsize=17, va='top')
fig.text(0.065, 0.845, 'ply', fontsize=10.5, color='#5d6465')
fig.text(0.965, 0.845, 'median; bars show the middle 50% of games',
         ha='right', fontsize=10.5, color='#5d6465')
ax.vlines(years, q25, q75, color='#c0c6c1', linewidth=1.1, zorder=2)
sns.lineplot(x=years, y=medians, ax=ax, color='#96513e', linewidth=1.65,
             marker='o', markersize=3.8, markeredgewidth=0, errorbar=None, zorder=3)
ax.set(xlim=(1883, 2030), ylim=(0, 40), xlabel='', ylabel='')
ax.set_xticks([1886, 1920, 1960, 2000, 2024])
ax.set_yticks([0, 10, 20, 30, 40])
ax.set_axisbelow(True)
ax.yaxis.grid(True, color='#dde0dc', linewidth=0.55)
ax.tick_params(axis='x', length=4, width=0.6, pad=8)
ax.tick_params(axis='y', length=0, pad=9)
sns.despine(ax=ax, left=True)
slope, low, high, p = (float(trend[key]) for key in
                      ['slope_plies_per_century', 'ci95_low', 'ci95_high', 'two_sided_p'])
p_text = 'p < 0.001' if p < 0.001 else f'p = {p:.3f}'
fig.text(0.065, 0.025,
         f'linear trend {slope:+.1f} plies/century (95% CI {low:.1f} to {high:.1f}; {p_text}; calendar HAC)',
         fontsize=9.5, color='#5d6465')
for suffix in ['png', 'svg']:
    fig.savefig(Path('plots') / f'novelty_over_time.{suffix}', dpi=220)
plt.close(fig)
