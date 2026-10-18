'''
Created on 16 October 2026

render the static figures from the same JSON used by the interactive panels

@author: Dinghao Luo
'''

#%% imports
import json
from pathlib import Path

from style import COLOURS, apply_style, save_figure
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch, Rectangle


#%% figures
def main() -> None:
    apply_style()
    panels = {path.stem: json.loads(path.read_text()) for path in Path('panels').glob('*.json')}
    panel = panels['pal_css_2005_clock']
    fig, axes = plt.subplots(2, 1, figsize=(9, 6.4), sharex=True, height_ratios=[3, 1.2])
    fig.subplots_adjust(left=0.09, right=0.97, top=0.89, bottom=0.15, hspace=0.18)
    fig.text(0.09, 0.96, panel['title'], fontsize=19, va='top')
    rows = panel['moves']
    for side, colour, label in [('white', COLOURS[0], 'ZackS'), ('black', COLOURS[1], 'Dobrov')]:
        own = [row for row in rows if row['ply'] % 2 == (side == 'white')]
        exact = [row for row in own if row[side + '_missing_times'] == 0]
        axes[0].plot([0] + [row['move'] for row in exact], [60] + [row[side + '_clock_upper_minutes'] for row in exact], color=colour, label=label)
        bounds = [row for row in own if row[side + '_missing_times'] > 0]
        if bounds:
            join = [exact[-1]] + bounds
            axes[0].plot([row['move'] for row in join], [row[side + '_clock_upper_minutes'] for row in join], color=colour,
                         linestyle='--', label=label + ': upper bound after missing time')
    for move, label in [(18, '18.Qf4'), (23, '23.Qe3')]:
        row = next(row for row in rows if row['ply'] == 2 * move - 1)
        value = row['white_clock_upper_minutes']
        axes[0].scatter(move, value, color=COLOURS[0], s=18)
        axes[0].annotate(label, (move, value), xytext=(5, 9), textcoords='offset points', fontsize=10)
    error = next(row for row in rows if row['ply'] == 66)
    axes[0].scatter(33, error['black_clock_upper_minutes'], color=COLOURS[1], s=18)
    axes[0].annotate('33...Qc6', (33, error['black_clock_upper_minutes']), xytext=(12, 12),
                     textcoords='offset points', fontsize=10)
    axes[0].set(ylabel='minutes remaining', ylim=(0, 67), xlim=(0, 59))
    axes[0].legend(frameon=False, fontsize=9, loc='lower left')
    evaluation = panel['evaluations']
    axes[1].plot([(row['ply'] - 1) / 2 for row in evaluation], [row['white_expected_score'] for row in evaluation], color=COLOURS[0], linewidth=1.2)
    axes[1].axhline(0.5, color='#aeb4b0', linewidth=0.7)
    axes[1].set(ylabel='White score\n(engine estimate)', xlabel='move number', ylim=(-0.05, 1.05), yticks=[0, 0.5, 1])
    for ax in axes:
        ax.grid(axis='y', color='#dde0dc', linewidth=0.6)
    save_figure(fig, 'pal_css_2005_clock')
    plt.close(fig)

    panel = panels['prepared_long_think']
    fig, ax = plt.subplots(figsize=(9, 4.8))
    fig.subplots_adjust(left=0.09, right=0.97, top=0.87, bottom=0.17)
    fig.text(0.09, 0.96, panel['title'], fontsize=19, va='top')
    rows = panel['moves']
    for parity, key, label, colour in [(1, 'rodo_elapsed_minutes', 'Rodo (White)', COLOURS[1]), (0, 'nielsen_elapsed_minutes', 'Nielsen (Black)', COLOURS[0])]:
        own = [row for row in rows if row['ply'] % 2 == parity]
        ax.plot([0] + [row['move'] for row in own], [0] + [row[key] for row in own], label=label, color=colour)
    ax.axvline(34, color='#9fa8a3', linestyle='--', linewidth=0.8)
    row = next(row for row in rows if row['ply'] == 68)
    ax.annotate('34...Nc7\nlast reported prepared move', (34, row['nielsen_elapsed_minutes']), xytext=(21, 53), fontsize=10,
                arrowprops={'arrowstyle': '-', 'color': '#96513e', 'linewidth': 0.7})
    ax.set(xlim=(0, 40), ylim=(0, 72), xlabel='move number', ylabel='cumulative minutes spent')
    ax.legend(frameon=False, fontsize=10, loc='upper left')
    ax.grid(axis='y', color='#dde0dc', linewidth=0.6)
    save_figure(fig, 'prepared_long_think')
    plt.close(fig)

    panel = panels['engine_ladder']
    cases, engines = panel['cases'], panel['engines']
    searches = {(row['case_id'], row['engine']): row for row in panel['searches'] if int(row['node_budget']) == panel['node_budget']}
    classes = {'unavailable': 0, 'rejected': 1, 'near_equal': 2, 'selected': 3, 'search_reversal': 4, 'not_selected_gap_unknown': 5}
    values = [[classes['not_selected_gap_unknown' if searches[case['case_id'], engine['name']]['candidate_status'] == 'unavailable' and engine['name'] == 'fruit-2.1' else searches[case['case_id'], engine['name']]['candidate_status']] for engine in engines] for case in cases]
    fig, ax = plt.subplots(figsize=(10, 9))
    fig.subplots_adjust(left=0.32, right=0.83, top=0.89, bottom=0.20)
    fig.text(0.08, 0.96, 'Engine preferences at 1M nodes', fontsize=18, va='top')
    ax.imshow(values, cmap=ListedColormap(['#f2f2ed', '#d5d7d0', '#b8c8b8', '#96513e', '#becbd5', '#dfcfae']), vmin=0, vmax=5, aspect='auto')
    ax.set_xticks(range(len(engines)), [engine['name'].replace('stockfish-', 'SF ') + '\n' + str(engine['year']) for engine in engines])
    labels = []
    for case in cases:
        who = 'Nielsen' if case['case_id'].startswith('nielsen') else 'game ' + case['source_ordinal']
        labels.append(who + ': ' + case['move_label'] + (' (disputed)' if case['source_issue'] else ''))
    ax.set_yticks(range(len(cases)), labels)
    for group in dict.fromkeys(case['decision_group'] for case in cases):
        indices = [i for i, case in enumerate(cases) if case['decision_group'] == group]
        if indices[0]:
            ax.axhline(indices[0] - 0.5, color='#f2f2ed', linewidth=3)
        ax.text(len(engines) - 0.43, sum(indices) / len(indices), group.replace(' and ', '\nand ').replace(' during ', '\nduring '),
                va='center', fontsize=9)
    ax.tick_params(length=0, pad=8)
    for i, row in enumerate(values):
        for j, value in enumerate(row):
            ax.text(j, i, ['?', 'x', '~', '=', '!', '×'][value], color='white' if value == 3 else '#394747', ha='center', va='center', fontsize=12)
    handles = [Patch(facecolor=colour, label=label) for colour, label in
               [('#96513e', '= selected'), ('#b8c8b8', '~ within 20 cp'), ('#d5d7d0', 'x rejected'),
                ('#becbd5', '! search reversal'), ('#dfcfae', '× not selected; gap unknown')]]
    fig.legend(handles=handles, ncol=3, loc='lower center', bbox_to_anchor=(0.5, 0.02), frameon=False, fontsize=9)
    save_figure(fig, 'engine_ladder')
    plt.close(fig)

    panel = panels['decision_explorer']
    lookup = {(row['case_id'], row['engine']): row for row in panel['historical_searches'] if row['node_budget'] == 1000000}
    cells = [[('Nielsen' if case['case_id'].startswith('nielsen') else 'game ' + case['source_ordinal']),
              case['move_label'] + (' (disputed)' if case['source_issue'] else ''),
              lookup[case['case_id'], 'fruit-2.1']['recommended_san'], lookup[case['case_id'], 'stockfish-17.1']['recommended_san']]
             for case in panel['cases']]
    fig, ax = plt.subplots(figsize=(8.5, 7.5))
    fig.subplots_adjust(left=0.1, right=0.94, top=0.89, bottom=0.06)
    ax.axis('off')
    fig.text(0.1, 0.96, 'Played moves and two automatic references', fontsize=18, va='top')
    table = ax.table(cellText=cells, colLabels=['game', 'played', 'Fruit 2.1', 'Stockfish 17.1'],
                     colWidths=[0.18, 0.25, 0.25, 0.32], cellLoc='center', loc='center', bbox=[0, 0, 1, 1])
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    for cell in table.get_celld().values():
        cell.set_edgecolor('#d4d8d2')
        cell.set_linewidth(0.4)
        cell.set_facecolor('#f2f2ed')
    save_figure(fig, 'decision_explorer')
    plt.close(fig)

    panel = panels['preparation_accounts']
    fig, ax = plt.subplots(figsize=(11, 5.7))
    fig.subplots_adjust(left=0.06, right=0.97, top=0.88, bottom=0.06)
    fig.text(0.08, 0.96, panel['title'], fontsize=18, va='top')
    ax.axis('off')
    cells = [[row['label'], str(row['account_move']), row['claim_type'].replace('_', ' '),
              str(row['first_long_think_move']) if row['first_long_think_move'] is not None else 'unavailable']
             for row in panel['cases']]
    table = ax.table(cellText=cells, colLabels=['account', 'reported move', 'claim', 'first long think'],
                     colWidths=[0.43, 0.15, 0.23, 0.19], cellLoc='left', bbox=[0, 0, 1, 1])
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    for cell in table.get_celld().values():
        cell.set_edgecolor('#d4d8d2')
        cell.set_linewidth(0.4)
        cell.set_facecolor('#f2f2ed')
    save_figure(fig, 'preparation_accounts')
    plt.close(fig)

    panel = panels['freestyle_history']
    fig, ax = plt.subplots(figsize=(11, 6))
    fig.subplots_adjust(left=0.06, right=0.98, top=0.88, bottom=0.06)
    ax.axis('off')
    fig.text(0.06, 0.96, panel['title'], fontsize=19, va='top')
    rows = [[row['year'], 'PAL/CSS ' + row['edition'] if row['edition'] else 'Infinity', row['winner'] or 'unverified',
             row['entry_type'].replace('_', ' '), row['winner_points'] or ''] for row in panel['events']]
    table = ax.table(cellText=rows, colLabels=['year', 'event', 'winner', 'reported entry type', 'points'],
                     colWidths=[0.07, 0.16, 0.23, 0.38, 0.08], cellLoc='left', bbox=[0, 0, 1, 1])
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    for cell in table.get_celld().values():
        cell.set_edgecolor('#d4d8d2')
        cell.set_linewidth(0.4)
        cell.set_facecolor('#f2f2ed')
    save_figure(fig, 'freestyle_history')
    plt.close(fig)

    panel = panels['iccf_outcomes']
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.7))
    fig.subplots_adjust(left=0.07, right=0.97, top=0.78, bottom=0.24, wspace=0.12)
    fig.text(0.07, 0.96, 'ICCF World Championship finals', fontsize=19, va='top')
    categories = [('reported_mating_blunder', '#96513e', 'board result'),
                  ('reported_board_win', '#96513e', 'board result'),
                  ('participant_contested_resignation', '#b89b76', 'contested'),
                  ('reported_input_error', '#697272', 'input error'),
                  ('reported_batch_resignation', '#c3b5a3', 'batch resignation'),
                  ('administrative_award', '#617b83', 'award after death')]
    for ax, row in zip(axes, panel['finals']):
        colours = []
        for category, colour, _ in categories:
            colours += [colour] * int(row['outcome_categories'].get(category, 0))
        colours += ['#dde0dc'] * (int(row['games']) - len(colours))
        assert len(colours) == 136
        for index, colour in enumerate(colours):
            ax.add_patch(Rectangle((index % 17, 7 - index // 17), .88, .88, facecolor=colour, linewidth=0))
        ax.set(xlim=(-.1, 17), ylim=(-.1, 8), aspect='equal')
        ax.set_title('final ' + str(row['edition']), fontsize=13, loc='left', pad=10)
        ax.set_axis_off()
    legend = dict((label, colour) for _, colour, label in categories)
    legend['draw'] = '#dde0dc'
    fig.legend(handles=[Patch(facecolor=colour, label=label) for label, colour in legend.items()],
               frameon=False, ncol=3, loc='lower center', bbox_to_anchor=(.52, .02), fontsize=10)
    save_figure(fig, 'iccf_outcomes')
    plt.close(fig)


if __name__ == '__main__':
    main()
