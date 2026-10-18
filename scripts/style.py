'''
Created on 16 October 2026

use the existing Piazzolla figure style throughout the essay figures

@author: Dinghao Luo
'''

#%% imports
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
from matplotlib import font_manager


#%% style
COLOURS = ['#96513e', '#617b83']


def apply_style() -> None:
    font_manager.fontManager.addfont('plots/fonts/Piazzolla-Regular.ttf')
    matplotlib.rcParams.update({
        'font.family': 'Piazzolla', 'font.size': 11, 'axes.labelsize': 11,
        'xtick.labelsize': 10, 'ytick.labelsize': 10, 'axes.edgecolor': '#cfd3d0',
        'axes.linewidth': 0.6, 'text.color': '#2c3133', 'axes.labelcolor': '#5d6465',
        'xtick.color': '#5d6465', 'ytick.color': '#5d6465',
        'figure.facecolor': '#f2f2ed', 'axes.facecolor': '#f2f2ed',
        'savefig.facecolor': '#f2f2ed', 'svg.fonttype': 'path',
        'axes.spines.top': False, 'axes.spines.right': False,
    })


def save_figure(fig, name: str) -> None:
    Path('plots').mkdir(exist_ok=True)
    for suffix in ['png', 'svg']:
        path = Path('plots') / f'{name}.{suffix}'
        fig.savefig(path, dpi=180)
        if suffix == 'svg':
            path.write_text('\n'.join(line.rstrip() for line in path.read_text().splitlines()) + '\n')
