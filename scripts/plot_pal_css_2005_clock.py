'''
Created on 15 October 2026

plot the winners’ clock through the deciding game against Dobrov

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


#%% main
def main() -> None:
    #%% recorded move times
    with Path('data/pal_css_2005_clocks.csv').open() as source:
        rows = [row for row in csv.DictReader(source)
                if row['source_ordinal'] == '26' and int(row['ply']) % 2 == 1]
    # all White times are present; Black has one missing move time
    assert all(row['white_missing_times'] == '0' for row in rows)
    moves = np.array([0] + [(int(row['ply']) + 1) // 2 for row in rows])
    minutes = np.array([60] + [float(row['white_clock_upper_seconds']) / 60 for row in rows])


    #%% figure
    font_manager.fontManager.addfont('plots/fonts/Piazzolla-Regular.ttf')
    sns.set_theme(style='ticks', rc={
        'font.family': 'Piazzolla', 'font.size': 12,
        'axes.labelsize': 12, 'xtick.labelsize': 11, 'ytick.labelsize': 11,
        'axes.edgecolor': '#cfd3d0', 'axes.linewidth': 0.6,
        'text.color': '#2c3133', 'axes.labelcolor': '#5d6465',
        'xtick.color': '#5d6465', 'ytick.color': '#5d6465',
        'figure.facecolor': '#f2f2ed', 'axes.facecolor': '#f2f2ed',
        'savefig.facecolor': '#f2f2ed', 'svg.fonttype': 'path',
    })
    fig, ax = plt.subplots(figsize=(8.8, 4.3))
    fig.subplots_adjust(left=0.075, right=0.965, top=0.77, bottom=0.18)
    fig.text(0.075, 0.95, 'ZackS against Dobrov', fontsize=17, va='top')
    fig.text(0.075, 0.855, '19 June 2005', fontsize=11, color='#5d6465')
    fig.text(0.965, 0.855, 'minutes remaining', ha='right', fontsize=11, color='#5d6465')
    sns.lineplot(x=moves, y=minutes, ax=ax, color='#96513e', linewidth=1.8, errorbar=None)
    for move, label, y_offset in [(18, '18.Qf4', 9), (23, '23.Qe3', 9)]:
        ax.plot(move, minutes[move], 'o', color='#96513e', markersize=4)
        ax.annotate(label, (move, minutes[move]), xytext=(5, y_offset),
                    textcoords='offset points', fontsize=11, color='#763e30')
    ax.set(xlim=(0, 59), ylim=(0, 66), xlabel='White’s move', ylabel='')
    ax.set_xticks([1, 10, 20, 30, 40, 50, 58])
    ax.set_yticks([0, 15, 30, 45, 60])
    ax.set_axisbelow(True)
    ax.yaxis.grid(True, color='#dde0dc', linewidth=0.55)
    ax.tick_params(axis='x', length=4, width=0.6, pad=8)
    ax.tick_params(axis='y', length=0, pad=9)
    sns.despine(ax=ax, left=True)
    fig.text(0.965, 0.025, '60 min + 15 s/move', ha='right', fontsize=10, color='#5d6465')
    for suffix in ['png', 'svg']:
        fig.savefig(Path('plots') / f'pal_css_2005_clock.{suffix}', dpi=220)
    plt.close(fig)


if __name__ == '__main__':
    main()
