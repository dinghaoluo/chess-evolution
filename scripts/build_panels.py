'''
Created on 16 October 2026

assemble the figure data and source limits for later interactive panels

@author: Dinghao Luo
'''

#%% imports
import csv
import hashlib
import json
from pathlib import Path


#%% inputs
def read_rows(path: str) -> list[dict]:
    with Path(path).open() as source:
        return list(csv.DictReader(source))


def write_panel(name: str, data: dict, inputs: list[str]) -> None:
    folder = Path('panels')
    folder.mkdir(exist_ok=True)
    data['inputs_sha256'] = {path: hashlib.sha256(Path(path).read_bytes()).hexdigest() for path in inputs}
    (folder / (name + '.json')).write_text(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False) + '\n')


#%% main
def main() -> None:
    derived = 'data/derived/'
    curated = 'data/curated/'
    clocks = read_rows(derived + 'pal_css_move_times.csv')
    cases = read_rows(curated + 'pal_css_2005_decisions.csv')
    trajectory = read_rows(derived + 'pal_css_2005_trajectory.csv')
    final = []
    for row in clocks:
        if row['game_id'] != 'pal_final:18':
            continue
        ply = int(row['ply'])
        final.append({'ply': ply, 'move': (ply + 1) // 2, 'san': row['move_san'],
                      'elapsed_seconds': float(row['elapsed_seconds']) if row['elapsed_seconds'] else None,
                      'white_clock_upper_minutes': float(row['white_clock_upper_seconds']) / 60,
                      'black_clock_upper_minutes': float(row['black_clock_upper_seconds']) / 60,
                      'white_missing_times': int(row['white_missing_times']),
                      'black_missing_times': int(row['black_missing_times']),
                      'notes': [{'account': case['account'], 'source_url': case['source_url']}
                                for case in cases if case['source_ordinal'] == '26' and int(case['ply']) == ply]})
    evaluations = [{'ply': int(row['ply']), 'white_expected_score': float(row['white_expected_score'])}
                   for row in trajectory if row['source_ordinal'] == '26']
    write_panel('pal_css_2005_clock', {'title': 'ZackS against Dobrov', 'date': '19 June 2005',
                'time_control': '60 min + 15 s/move', 'moves': final, 'evaluations': evaluations,
                'limits': ['Black has a missing move time at ply 30; subsequent clock values are upper bounds.',
                           'Evaluation is the modern engine estimate before each move at 1M nodes, with full game history.']},
                [derived + 'pal_css_move_times.csv', derived + 'pal_css_2005_trajectory.csv', curated + 'pal_css_2005_decisions.csv'])
    nielsen = []
    for row in clocks:
        if row['game_id'] != 'pal_2007_final5:2' or int(row['ply']) > 80:
            continue
        assert row['white_missing_times'] == row['black_missing_times'] == '0'
        nielsen.append({'ply': int(row['ply']), 'move': (int(row['ply']) + 1) // 2,
                        'san': row['move_san'], 'elapsed_seconds': float(row['elapsed_seconds']),
                        'rodo_elapsed_minutes': float(row['white_elapsed_lower_seconds']) / 60,
                        'nielsen_elapsed_minutes': float(row['black_elapsed_lower_seconds']) / 60})
    write_panel('prepared_long_think', {'title': 'Checking a prepared move', 'date': '23 March 2007',
                'moves': nielsen, 'prepared_exchange_move': 26, 'last_reported_prepared_move': 34,
                'source_url': 'https://en.chessbase.com/post/freestyle-che-teaching-an-engine-how-to-fly',
                'limits': ['Nielsen identifies 34...Nc7 as his last prepared move; the 26...Rxb5 sacrifice was prepared too.',
                           'Cumulative elapsed time excludes increment; all supplied move times are present; the game ends on move 37.']},
                [derived + 'pal_css_move_times.csv'])
    positions = read_rows(derived + 'decision_positions.csv')
    for case in positions:
        ply = int(case['ply'])
        case['move_label'] = str((ply + 1) // 2) + ('.' if ply % 2 else '...') + case['move'].split('.')[-1]
        kind = case['decision_kind']
        if case['source_issue']:
            case['decision_group'] = 'unresolved account'
        elif 'prepar' in kind or 'opening' in kind or case['case_id'] == 'nielsen_prepared_exchange':
            case['decision_group'] = 'opening and preparation'
        elif kind in ['opponent plan', 'evaluation disagreement']:
            case['decision_group'] = 'opponent moves'
        elif kind.startswith('retrospective'):
            case['decision_group'] = 'retrospective claims'
        else:
            case['decision_group'] = 'choices during play'
    groups = ['opening and preparation', 'choices during play', 'opponent moves', 'retrospective claims', 'unresolved account']
    positions.sort(key=lambda case: groups.index(case['decision_group']))
    ladder = read_rows(derived + 'engine_ladder.csv')
    for row in ladder:
        for key in ['release_year', 'node_budget', 'search_nodes', 'depth', 'matches_played']:
            row[key] = int(row[key])
    builds = json.loads(Path(derived + 'engine_builds.json').read_text())
    summary = read_rows(derived + 'engine_ladder_summary.csv')
    stability = read_rows(derived + 'engine_ladder_stability.csv')
    write_panel('engine_ladder', {'title': 'Which releases select the documented move?', 'node_budget': 1000000,
                'engines': [{'name': build['name'], 'year': build['year']} for build in builds],
                'excluded_engines': json.loads(Path(curated + 'engine_exclusions.json').read_text()),
                'cases': positions, 'searches': ladder, 'first_matches': summary, 'budget_stability': stability,
                'near_equal_cp': 20,
                'limits': ['Requested node budgets, with actual searched nodes retained for each run.',
                           'Earliest matching tested release; move preferences can reverse in later releases.',
                           'Centipawn scores are engine-specific and are not calibrated across releases.',
                           'Near-equal means an absolute forced-candidate gap within 20 centipawns in that engine; separate searches can reverse the unrestricted ranking.',
                           'Fruit ignores searchmoves, so its non-selected candidate gaps remain unavailable.',
                           'The ladder uses unrestricted single-PV play; shared candidate searches can rank moves differently.',
                           'The documented positions include opponents’ moves and retrospective claims; a mismatch does not establish a beneficial human intervention.',
                           'Sparse engine generations, selected decisions, and unequal costs per node prevent a historical crossover date.']},
                [derived + name for name in ['decision_positions.csv', 'engine_ladder.csv', 'engine_ladder_summary.csv', 'engine_ladder_stability.csv', 'engine_builds.json']]
                + [curated + 'engine_exclusions.json'])
    paired = {'pal_2005': read_rows(derived + 'pal_css_2005_case.csv'),
              'clock_cases': read_rows(derived + 'clock_case_evaluations.csv')}
    reference = read_rows(derived + 'reference_comparisons.csv')
    write_panel('decision_explorer', {'title': 'Documented decisions and automatic searches', 'cases': positions,
                'modern_comparisons': paired, 'historical_searches': ladder, 'time_scenarios': reference,
                'time_scenario_status': 'uncalibrated archival scenarios; excluded from the essay',
                'limits': ['Participant-selected decisions; reports sometimes disagree with the saved game.',
                           'Fruit is a reference engine; nominal search speeds do not reconstruct the team hardware, pondering, or preparation.']},
                [derived + name for name in ['decision_positions.csv', 'pal_css_2005_case.csv', 'clock_case_evaluations.csv', 'engine_ladder.csv', 'reference_comparisons.csv']])
    accounts = read_rows(curated + 'preparation_accounts.csv')
    checks = read_rows(derived + 'preparation_clock_checks.csv')
    endpoints = []
    for account in accounts:
        if account['claim_type'] not in ['first_unprepared_move', 'unprepared_by', 'known_through', 'last_prepared_move']:
            continue
        check = next(row for row in checks if row['case_id'] == account['case_id'])
        endpoints.append({**account, 'account_move': (int(account['ply']) + 1) // 2,
                          'first_long_think_move': (int(check['first_qualifying_think_ply']) + 1) // 2 if check['first_qualifying_think_ply'] else None,
                          'threshold_seconds': float(check['threshold_seconds'])})
    write_panel('preparation_accounts', {'title': 'Preparation accounts and first long thinks', 'cases': endpoints,
                'limits': ['Known-through and unprepared-by claims are bounds; a long think does not identify the preparation endpoint.',
                           'PAL/CSS threshold: five percent of the starting clock; classical threshold: five minutes.']},
                [curated + 'preparation_accounts.csv', derived + 'preparation_clock_checks.csv'])
    write_panel('freestyle_history', {'title': 'Freestyle winners and reported entry types',
                'events': read_rows(derived + 'freestyle_events.csv'), 'hydra': read_rows(derived + 'hydra_results.csv'),
                'comparisons': read_rows(derived + 'freestyle_comparisons.csv'),
                'limits': ['Hydra results are against the field; opponent modes are unclassified, and Ares01 had human intervention.',
                           'The 2014 comparison is an interim report after eighteen rounds, with a 54–42 colour imbalance.',
                           'Entrants could change mode between games; no complete centaur-versus-engine census is inferred.']},
                [derived + name for name in ['freestyle_events.csv', 'hydra_results.csv', 'freestyle_comparisons.csv']])
    iccf = read_rows(curated + 'iccf_finals.csv')
    decisive = read_rows(curated + 'iccf_32_decisive_games.csv')
    for row in iccf:
        assert int(row['draws']) + int(row['decisive_recorded']) == int(row['games'])
        if row['edition'] == '32':
            assert len(decisive) == int(row['decisive_recorded'])
            row['outcome_categories'] = {category: sum(game['outcome_category'] == category for game in decisive)
                                         for category in dict.fromkeys(game['outcome_category'] for game in decisive)}
        else:
            row['outcome_categories'] = {'administrative_award': int(row['administrative_decisive'])}
    write_panel('iccf_outcomes', {'title': 'Recorded outcomes in two ICCF finals', 'finals': iccf, 'final_32_decisive_games': decisive,
                'final_32_players': read_rows(curated + 'iccf_32_players.csv'),
                'limits': ['All ten decisive scores in final 33 followed Dronov’s death; they are administrative outcomes.',
                           'Edwards reports thirteen batch resignations by Bock in final 32 and disputes another resignation; these are participant reports, not formal administrative awards.',
                           'Edwards describes an input error, a mating blunder, and a board win for the other three results. Formal termination codes were unavailable.',
                           'Counts come from official crosstables; bulk PGN retrieval was unavailable.']},
                [curated + 'iccf_finals.csv', curated + 'iccf_32_decisive_games.csv', curated + 'iccf_32_players.csv'])


if __name__ == '__main__':
    main()
