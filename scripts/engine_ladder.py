'''
Created on 16 October 2026

compare documented decisions with five engine releases at fixed node budgets

@author: Dinghao Luo
'''

#%% imports
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
from zipfile import ZipFile

import chess
import chess.engine
import chess.pgn

from pal_css_2005_case import search


BUDGETS = [250_000, 1_000_000, 4_000_000]
NEAR_EQUAL_CP = 20


#%% positions
def decision_positions() -> list[dict]:
    frozen = {row['file']: row['sha256'] for row in json.loads(Path('data/curated/source_files.json').read_text())}
    with Path('data/derived/pal_css_2005_games.csv').open() as source:
        games = {row['source_ordinal']: row for row in csv.DictReader(source)}
    with Path('data/curated/pal_css_2005_decisions.csv').open() as source:
        cases = list(csv.DictReader(source))
    positions = []
    for case in cases:
        game = games[case['source_ordinal']]
        history = game['moves_uci'].split()[:int(case['ply']) - 1]
        positions.append({**case, 'initial_fen': game['initial_fen'], 'history_uci': ' '.join(history)})
    for case_id, filename, ordinal, ply in [
            ('nielsen_endgame_28', 'pal_2007_annotations.pgn', 1, 55),
            ('nielsen_prepared_exchange', 'pal_2007_final5.zip', 2, 52)]:
        raw = (Path('cache/sources') / filename).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == frozen[filename], filename
        if filename.endswith('.zip'):
            with ZipFile(io.BytesIO(raw)) as archive:
                raw = archive.read(next(name for name in archive.namelist() if name.lower().endswith('.pgn')))
        pgn = io.StringIO(raw.decode('latin-1'))
        source_games = list(iter(lambda: chess.pgn.read_game(pgn), None))
        game = source_games[ordinal - 1]
        assert not game.errors
        board = game.board()
        for move in list(game.mainline_moves())[:ply - 1]:
            board.push(move)
        move = list(game.mainline_moves())[ply - 1]
        positions.append({'case_id': case_id, 'ply': ply, 'move': board.san(move), 'move_uci': move.uci(),
                          'source_ordinal': ordinal, 'initial_fen': game.board().fen(),
                          'history_uci': ' '.join(m.uci() for m in board.move_stack), 'fen_before': board.fen(),
                          'reported_alternative_uci': '', 'decision_kind': 'reported historical engine difficulty',
                          'account': 'prepared exchange sacrifice' if ply == 52 else 'winning rook move found during earlier calculation',
                          'source_issue': '',
                          'source_url': 'https://en.chessbase.com/post/freestyle-che-teaching-an-engine-how-to-fly'})
    return positions


def position_board(case: dict) -> chess.Board:
    board = chess.Board(case['initial_fen'])
    for move in case['history_uci'].split():
        board.push_uci(move)
    assert board.fen() == case['fen_before'], case['case_id']
    assert board.parse_uci(case['move_uci']) in board.legal_moves
    return board


#%% candidate scores
def candidate_class(selected: bool, played: chess.engine.Score, reference: chess.engine.Score, tolerance: int) -> str:
    if selected:
        return 'selected'
    if played.score() is not None and reference.score() is not None:
        gap = reference.score() - played.score()
        if abs(gap) <= tolerance:
            return 'near_equal'
    elif played == reference:
        return 'near_equal'
    return 'rejected' if reference > played else 'search_reversal'


def score_candidates(build: dict, board: chess.Board, row: dict) -> dict:
    selected = bool(int(row['matches_played']))
    scores = {}
    for label in ['played', 'reference']:
        for field in ['cp', 'mate', 'depth', 'nodes']:
            row[label + '_forced_' + field] = ''
    row['candidate_gap_cp'] = ''
    row['candidate_status'] = 'selected' if selected else 'unavailable'
    row['candidate_search_status'] = 'same_move' if selected else 'unsupported_root_restriction'
    if selected:
        return row
    # Fruit 2.1's parser accepts searchmoves as a dummy token
    if build['name'] == 'fruit-2.1':
        return row
    for label, uci in [('played', row['played_uci']), ('reference', row['recommended_uci'])]:
        move = board.parse_uci(uci)
        with chess.engine.SimpleEngine.popen_uci(build['binary'], timeout=120) as engine:
            engine.configure(build['options'])
            info = search(engine, board, int(row['node_budget']), [move], 1)[0]
        assert info['pv'][0] == move, (build['name'], uci)
        score = info['score'].pov(board.turn)
        scores[label] = score
        row.update({label + '_forced_cp': score.score(), label + '_forced_mate': score.mate(),
                    label + '_forced_depth': info['depth'], label + '_forced_nodes': info['search_nodes']})
    if all(score.score() is not None for score in scores.values()):
        row['candidate_gap_cp'] = scores['reference'].score() - scores['played'].score()
    row['candidate_status'] = candidate_class(False, scores['played'], scores['reference'], NEAR_EQUAL_CP)
    row['candidate_search_status'] = 'separate_forced_roots'
    return row


def ladder_summary(cases: list[dict], rows: list[dict]) -> tuple[list[dict], list[dict]]:
    summary, stability = [], []
    engines = list(dict.fromkeys(row['engine'] for row in rows))
    for case in cases:
        for budget in BUDGETS:
            own = [row for row in rows if row['case_id'] == case['case_id'] and int(row['node_budget']) == budget]
            matches = [row for row in own if int(row['matches_played'])]
            first = min(matches, key=lambda row: int(row['release_year'])) if matches else None
            later = [row['engine'] for row in own if first and int(row['release_year']) > int(first['release_year'])
                     and not int(row['matches_played'])]
            summary.append({'case_id': case['case_id'], 'node_budget': budget,
                            'first_matching_tested_engine': first['engine'] if first else '',
                            'first_matching_tested_year': first['release_year'] if first else '',
                            'later_disagreements': ' '.join(later)})
        for name in engines:
            own = sorted([row for row in rows if row['case_id'] == case['case_id'] and row['engine'] == name],
                         key=lambda row: int(row['node_budget']))
            assert [int(row['node_budget']) for row in own] == BUDGETS
            statuses = [row['candidate_status'] for row in own]
            result = {'case_id': case['case_id'], 'decision_kind': case['decision_kind'], 'engine': name,
                      'classes_by_budget': ' '.join(statuses),
                      'same_class_all_budgets': int(len(set(statuses)) == 1),
                      'selected_all_budgets': int(all(int(row['matches_played']) for row in own)),
                      'selected_or_near_equal_all_budgets': int(all(status in ['selected', 'near_equal'] for status in statuses))}
            for tolerance in [10, 30]:
                sensitive = []
                for row in own:
                    if row['candidate_search_status'] != 'separate_forced_roots':
                        sensitive.append(row['candidate_status'])
                        continue
                    scores = {label: chess.engine.Cp(int(row[label + '_forced_cp']))
                              if row[label + '_forced_cp'] not in ['', None]
                              else chess.engine.Mate(int(row[label + '_forced_mate'])) for label in ['played', 'reference']}
                    sensitive.append(candidate_class(False, scores['played'], scores['reference'], tolerance))
                result[f'classes_by_budget_{tolerance}cp'] = ' '.join(sensitive)
                result[f'selected_or_near_equal_all_budgets_{tolerance}cp'] = int(all(
                    status in ['selected', 'near_equal'] for status in sensitive))
            stability.append(result)
    return summary, stability


#%% main
def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--reuse-selections', action='store_true')
    parser.add_argument('--summarise-only', action='store_true')
    args = parser.parse_args()
    folder = Path('data/derived')
    builds = json.loads((folder / 'engine_builds.json').read_text())
    cases = decision_positions()
    fields = ['case_id', 'ply', 'move', 'move_uci', 'source_ordinal', 'initial_fen', 'history_uci',
              'fen_before', 'reported_alternative_uci', 'decision_kind', 'account', 'source_issue', 'source_url']
    with (folder / 'decision_positions.csv').open('w', newline='') as destination:
        writer = csv.DictWriter(destination, fieldnames=fields, extrasaction='ignore', lineterminator='\n')
        writer.writeheader()
        writer.writerows(cases)
    paths = [Path('data/curated/pal_css_2005_decisions.csv'), folder / 'pal_css_2005_games.csv',
             Path('cache/sources/pal_2007_annotations.pgn'), Path('cache/sources/pal_2007_final5.zip')]
    inputs = {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
    previous = {}
    if args.reuse_selections or args.summarise_only:
        saved = json.loads((folder / 'engine_ladder_config.json').read_text())
        assert saved['inputs_sha256'] == inputs
        assert saved['budgets'] == BUDGETS
        assert saved['output_sha256'] == hashlib.sha256((folder / 'engine_ladder.csv').read_bytes()).hexdigest()
        assert [(build['name'], build['binary_sha256'], build['options']) for build in builds] == [
            (build['name'], build['binary_sha256'], build['options']) for build in saved['engines']]
        with (folder / 'engine_ladder.csv').open() as source:
            previous = {(row['case_id'], row['engine'], int(row['node_budget'])): row for row in csv.DictReader(source)}
        assert len(previous) == len(cases) * len(builds) * len(BUDGETS)
    results = []
    for build in builds:
        assert hashlib.sha256(Path(build['binary']).read_bytes()).hexdigest() == build['binary_sha256']
        for case in cases:
            board = position_board(case)
            for budget in BUDGETS:
                if args.summarise_only:
                    results.append(previous[case['case_id'], build['name'], budget])
                    continue
                if args.reuse_selections:
                    row = previous[case['case_id'], build['name'], budget]
                    results.append(score_candidates(build, board, row))
                    continue
                # a fresh process also clears engines whose ucinewgame keeps hash entries
                with chess.engine.SimpleEngine.popen_uci(build['binary'], timeout=120) as engine:
                    engine.configure(build['options'])
                    result = engine.play(board, chess.engine.Limit(nodes=budget), info=chess.engine.INFO_ALL)
                move = result.move
                info = result.info
                row = {'case_id': case['case_id'], 'engine': build['name'], 'release_year': build['year'],
                       'node_budget': budget, 'search_nodes': info['nodes'], 'depth': info['depth'],
                       'played_uci': case['move_uci'], 'recommended_uci': move.uci(),
                       'recommended_san': board.san(move), 'matches_played': int(move.uci() == case['move_uci']),
                       'mover_cp': info['score'].pov(board.turn).score(),
                       'mover_mate': info['score'].pov(board.turn).mate()}
                results.append(score_candidates(build, board, row))
        if not args.summarise_only:
            print(build['name'], 'checked', flush=True)
    with (folder / 'engine_ladder.csv').open('w', newline='') as destination:
        writer = csv.DictWriter(destination, fieldnames=list(results[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(results)
    summary, stability = ladder_summary(cases, results)
    for name, output in [('engine_ladder_summary', summary), ('engine_ladder_stability', stability)]:
        with (folder / (name + '.csv')).open('w', newline='') as destination:
            writer = csv.DictWriter(destination, fieldnames=list(output[0]), lineterminator='\n')
            writer.writeheader()
            writer.writerows(output)
    metadata = {'engines': builds, 'budgets': BUDGETS,
                'near_equal_cp': NEAR_EQUAL_CP,
                'near_equal_cp_sensitivities': [10, 20, 30],
                'candidate_scores': 'separate fresh-process single-root searches at the selection budget; signed gap retained; negative gaps beyond tolerance are search reversals',
                'unavailable': 'Fruit 2.1 ignores searchmoves; candidate gaps are unavailable for non-selected moves',
                'hash_policy': 'fresh process for every case and budget; full source-game history',
                'selection': 'sixteen curated 2005 decisions and two Nielsen moves; participant-selected examples',
                'interpretation': 'earliest tested release selecting the played move; sparse releases, non-monotone preferences, unequal node costs, and no historical hardware reconstruction',
                'inputs_sha256': inputs,
                'outputs': {name + '.csv': hashlib.sha256((folder / (name + '.csv')).read_bytes()).hexdigest()
                            for name in ['engine_ladder_summary', 'engine_ladder_stability']},
                'output_sha256': hashlib.sha256((folder / 'engine_ladder.csv').read_bytes()).hexdigest()}
    (folder / 'engine_ladder_config.json').write_text(json.dumps(metadata, indent=2) + '\n')


if __name__ == '__main__':
    main()
