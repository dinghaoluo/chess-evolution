'''
Created on 15 October 2026

plot opening time across title matches and a prepared move checked during play

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


#%% style
font_manager.fontManager.addfont('plots/fonts/Piazzolla-Regular.ttf')
sns.set_theme(style='ticks', rc={
    'font.family': 'Piazzolla', 'font.size': 12, 'axes.labelsize': 12,
    'xtick.labelsize': 11, 'ytick.labelsize': 11,
    'axes.edgecolor': '#cfd3d0', 'axes.linewidth': 0.6,
    'text.color': '#2c3133', 'axes.labelcolor': '#5d6465',
    'xtick.color': '#5d6465', 'ytick.color': '#5d6465',
    'figure.facecolor': '#f2f2ed', 'axes.facecolor': '#f2f2ed',
    'savefig.facecolor': '#f2f2ed', 'svg.fonttype': 'path',
})


#%% championship matches
def main() -> None:
    data = Path('data')
    with (data / 'championship_opening_time.csv').open() as source:
        games = list(csv.DictReader(source))
    with (data / 'championship_clock_years.csv').open() as source:
        years = list(csv.DictReader(source))
    fig, ax = plt.subplots(figsize=(8.8, 4.7))
    fig.subplots_adjust(left=0.085, right=0.965, top=0.76, bottom=0.18)
    fig.text(0.085, 0.95, 'Time spent on the first twenty moves', fontsize=18, va='top')
    fig.text(0.085, 0.85, 'World Championship matches', fontsize=11, color='#5d6465')
    fig.text(0.965, 0.85, 'minutes per player', ha='right', fontsize=11, color='#5d6465')
    rng = np.random.default_rng(20261015)
    for year in years:
        x = int(year['year'])
        values = [float(row['mean_minutes_first_20']) for row in games if int(row['year']) == x]
        ax.scatter(x + rng.uniform(-0.13, 0.13, len(values)), values,
                   s=20, color='#7e8989', alpha=0.5, linewidths=0, zorder=2)
        ax.plot([x, x], [float(year['q25_minutes_first_20']), float(year['q75_minutes_first_20'])],
                color='#96513e', linewidth=3, solid_capstyle='round', zorder=3)
    ax.plot([int(row['year']) for row in years], [float(row['median_minutes_first_20']) for row in years],
            color='#96513e', marker='o', markersize=5, linewidth=1.5, zorder=4)
    ax.set(xlim=(2020.6, 2024.4), ylim=(0, 120), xlabel='', ylabel='')
    ax.set_xticks([2021, 2023, 2024])
    ax.set_yticks([0, 30, 60, 90, 120])
    ax.set_axisbelow(True)
    ax.yaxis.grid(True, color='#dde0dc', linewidth=0.55)
    ax.tick_params(axis='x', length=4, width=0.6, pad=8)
    ax.tick_params(axis='y', length=0, pad=9)
    sns.despine(ax=ax, left=True)
    fig.text(0.085, 0.04, 'game averages; median and middle half', fontsize=10, color='#5d6465')
    for suffix in ['png', 'svg']:
        fig.savefig(Path('plots') / f'championship_opening_time.{suffix}', dpi=220)
    plt.close(fig)

    #%% Nielsen against Rodo
    with (data / 'pal_css_move_times.csv').open() as source:
        rows = [row for row in csv.DictReader(source) if row['game_id'] == 'pal_2007_final5:2'
                and int(row['ply']) % 2 == 0 and int(row['ply']) <= 80]
    assert all(row['elapsed_seconds'] for row in rows)
    moves = np.array([int(row['ply']) // 2 for row in rows])
    minutes = np.array([float(row['elapsed_seconds']) / 60 for row in rows])
    fig, ax = plt.subplots(figsize=(8.8, 4.7))
    fig.subplots_adjust(left=0.085, right=0.965, top=0.76, bottom=0.18)
    fig.text(0.085, 0.95, 'Checking a prepared move', fontsize=18, va='top')
    fig.text(0.085, 0.85, 'Nielsen against Rodo, 23 March 2007', fontsize=11, color='#5d6465')
    fig.text(0.965, 0.85, 'minutes per move', ha='right', fontsize=11, color='#5d6465')
    ax.axvspan(0.5, 34.5, color='#e6e5dd', alpha=0.6)
    ax.axvline(34.5, color='#9fa8a3', linewidth=0.7, linestyle=(0, (3, 4)))
    ax.plot(moves, minutes, color='#96513e', linewidth=1.5, marker='o', markersize=2.5)
    ax.annotate('34...Nc7', (34, minutes[moves == 34][0]), xytext=(24, 18.8), fontsize=11,
                color='#763e30', arrowprops={'arrowstyle': '-', 'color': '#96513e', 'linewidth': 0.7})
    ax.text(2, 19.2, 'reported preparation', fontsize=10, color='#717b76')
    ax.set(xlim=(0.5, 40.5), ylim=(0, 21), xlabel='Black’s move', ylabel='')
    ax.set_xticks([1, 10, 20, 30, 40])
    ax.set_yticks([0, 5, 10, 15, 20])
    ax.set_axisbelow(True)
    ax.yaxis.grid(True, color='#dde0dc', linewidth=0.55)
    ax.tick_params(axis='x', length=4, width=0.6, pad=8)
    ax.tick_params(axis='y', length=0, pad=9)
    sns.despine(ax=ax, left=True)
    for suffix in ['png', 'svg']:
        fig.savefig(Path('plots') / f'prepared_long_think.{suffix}', dpi=220)
    plt.close(fig)


if __name__ == '__main__':
    main()
