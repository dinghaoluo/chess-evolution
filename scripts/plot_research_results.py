'''
Created on 16 October 2026

render the release bracket and January participation evidence

@author: Dinghao Luo
'''

#%% imports
import hashlib
import json
from pathlib import Path

from style import COLOURS, apply_style, save_figure
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.lines import Line2D
from matplotlib.patches import Patch


#%% release comparison
def nielsen() -> None:
    panel = json.loads(Path('panels/nielsen_releases.json').read_text())
    searches = panel['searches']
    engines = list(dict.fromkeys(row['engine'] for row in searches))
    budgets = [250000, 1000000, 4000000]
    classes = {'unavailable': 0, 'rejected': 1, 'near_equal': 2, 'selected': 3, 'search_reversal': 4, 'not_selected_gap_unknown': 5}
    lookup = {(row['case_id'], row['engine'], int(row['node_budget'])): row for row in searches}
    values, labels = [], []
    for case in panel['cases']:
        for budget in budgets:
            values.append([classes['not_selected_gap_unknown' if lookup[case['case_id'], engine, budget]['candidate_status'] == 'unavailable' and engine == 'fruit-2.1' else lookup[case['case_id'], engine, budget]['candidate_status']] for engine in engines])
            labels.append(('28.Re8+' if case['ply'] == 55 else '26...Rxb5') + f'    {budget / 1000000:g}M')
    fig, ax = plt.subplots(figsize=(11, 5.5))
    fig.subplots_adjust(left=0.23, right=0.97, top=0.87, bottom=0.27)
    fig.text(0.06, 0.96, panel['title'], fontsize=19, va='top')
    ax.imshow(values, cmap=ListedColormap(['#f2f2ed', '#d5d7d0', '#b8c8b8', '#96513e', '#becbd5', '#dfcfae']), vmin=0, vmax=5, aspect='auto')
    years = {row['engine']: row['release_year'] for row in searches}
    ax.set_xticks(range(len(engines)), [name.replace('stockfish-', 'SF ').replace('fruit-', 'Fruit ') + '\n' + str(years[name]) for name in engines])
    ax.set_yticks(range(6), labels)
    ax.axhline(2.5, color='#f2f2ed', linewidth=4)
    ax.tick_params(length=0, pad=8)
    for i, row in enumerate(values):
        for j, value in enumerate(row):
            ax.text(j, i, ['?', 'x', '~', '=', '!', '×'][value], color='white' if value == 3 else '#394747', ha='center', va='center', fontsize=14)
    handles = [Patch(facecolor=colour, label=label) for colour, label in
               [('#96513e', '= selected'), ('#b8c8b8', '~ within 20 cp'), ('#d5d7d0', 'x rejected'),
                ('#becbd5', '! search reversal'), ('#dfcfae', '× not selected; gap unknown')]]
    fig.legend(handles=handles, ncol=3, loc='lower center', bbox_to_anchor=(0.5, 0.02), frameon=False, fontsize=9)
    save_figure(fig, 'nielsen_releases')
    plt.close(fig)


#%% participation
def participation() -> None:
    panel = json.loads(Path('panels/rating_participation.json').read_text())
    rows = panel['series']
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.7))
    fig.subplots_adjust(left=0.08, right=0.98, top=0.79, bottom=0.24, wspace=0.32)
    fig.text(0.08, 0.96, 'FIDE standard-rated entries', fontsize=19, va='top')
    axes[0].plot([row['year'] for row in rows], [float('nan') if row['membership_2250'] is None else row['membership_2250'] for row in rows], color=COLOURS[0], linewidth=1.6)
    axes[0].set(title='Listed, 2250+', xlim=(1970, 2027), ylim=(0, None), xticks=[1980, 2000, 2020], ylabel='entries')
    for threshold, colour in [(2000, '#4c5d60'), (2250, COLOURS[0]), (2400, COLOURS[1])]:
        selected = [row for row in panel['threshold_series'] if row['threshold'] == threshold]
        baseline = selected[0]['active']
        axes[1].plot([row['year'] for row in selected], [100 * row['active'] / baseline for row in selected],
                     color=colour, label=str(threshold) + '+', linewidth=1.6)
    axes[1].set(title='Active, 2000+ / 2250+ / 2400+', xlim=(2000, 2027), xticks=[2000, 2010, 2020], ylabel='index (2000 = 100)', ylim=(0, None))
    axes[1].legend(frameon=False, fontsize=10, loc='lower left', ncol=3,
                   bbox_to_anchor=(0, 0.03), borderaxespad=0, columnspacing=1.0, handlelength=1.6)
    for ax in axes:
        for change in panel['floor_changes']:
            year = int(change['date'][:4]) + (int(change['date'][5:7]) - 1) / 12
            ax.axvline(year, color='#c6ccc7', linewidth=0.6, zorder=0)
        ax.axvline(2024 + 2 / 12, color=COLOURS[1], linestyle='--', linewidth=1)
        ax.grid(axis='y', color='#dde0dc', linewidth=0.6)
    axes[1].axvspan(2020 + 10 / 12, 2023, color='#d6ddda', alpha=0.7, zorder=0)
    handles = [Line2D([0], [0], color='#c6ccc7', linewidth=1, label='floor change'),
               Line2D([0], [0], color=COLOURS[1], linestyle='--', linewidth=1, label='March 2024'),
               Patch(facecolor='#d6ddda', label='24-month activity rule')]
    fig.legend(handles=handles, frameon=False, ncol=3, loc='lower center', bbox_to_anchor=(0.53, 0.02), fontsize=10)
    save_figure(fig, 'rating_participation')
    plt.close(fig)


#%% advice stability
def advice() -> None:
    panel = json.loads(Path('panels/advice_noise_floor.json').read_text())
    rows = panel['comparisons']
    fig, ax = plt.subplots(figsize=(9, 4.6))
    fig.subplots_adjust(left=0.18, right=0.97, top=0.84, bottom=0.24)
    fig.text(0.07, 0.96, panel['title'], fontsize=19, va='top')
    for i, row in enumerate(rows):
        ax.plot([100 * row['mean_budget_disagreement'], 100 * (1 - row['between_agreement_100000'])], [i, i], color='#c3c9c4', linewidth=1.5)
        ax.scatter(100 * row['mean_budget_disagreement'], i, color=COLOURS[1], s=45, marker='s', zorder=3)
        ax.scatter(100 * (1 - row['between_agreement_100000']), i, color=COLOURS[0], s=45, zorder=3)
    labels = [row['first'].replace('stockfish-', 'SF ') + ' / ' + row['second'].replace('stockfish-', 'SF ') for row in rows]
    ax.set(yticks=range(len(rows)), yticklabels=labels, xlabel='disagreement (%)', xlim=(0, 65), ylim=(len(rows)-.5, -.5))
    ax.grid(axis='x', color='#dde0dc', linewidth=.6)
    fig.legend(handles=[Line2D([], [], marker='s', color=COLOURS[1], linestyle='', label='mean within release: 100k / 400k'),
                        Line2D([], [], marker='o', color=COLOURS[0], linestyle='', label='between releases: 100k')],
               frameon=False, ncol=2, loc='lower center', bbox_to_anchor=(.53, .02), fontsize=10)
    save_figure(fig, 'advice_noise_floor')
    plt.close(fig)


#%% main
def main() -> None:
    apply_style()
    nielsen()
    participation()
    advice()
    inputs = [str(path) for path in sorted(Path('panels').glob('*.json'))]
    inputs += ['scripts/plot_panels.py', 'scripts/plot_research_results.py', 'scripts/style.py', 'plots/fonts/Piazzolla-Regular.ttf']
    outputs = [f'plots/{Path(name).stem}.{suffix}' for name in inputs if name.startswith('panels/') for suffix in ['png', 'svg']]
    config = {key: {name: hashlib.sha256(Path(name).read_bytes()).hexdigest() for name in names}
              for key, names in [('inputs_sha256', inputs), ('outputs_sha256', outputs)]}
    Path('data/derived/research_figures_config.json').write_text(json.dumps(config, indent=2) + '\n')


if __name__ == '__main__':
    main()
