'''
Created on 16 October 2026

run the archive readers, searches, panels, and checks in dependency order

@author: Dinghao Luo
'''

#%% imports
import argparse
import subprocess
import sys
from pathlib import Path


#%% stages
STAGES = {
    'sources': ['prepare_sources.py'],
    'build-engines': ['prepare_engines.py'],
    'check-builds': ['check_engine_builds.py'],
    'build-nielsen': ['prepare_nielsen_engines.py'],
    'corpus': ['restore_archive.py'],
    'tables': ['read_pal_css_2005.py', 'read_pal_css_clocks.py', 'read_championship_clocks.py',
               'summarise_clocks.py', 'freestyle_results.py'],
    'searches': ['pal_css_2005_case.py', 'pal_css_2005_turning_points.py', 'check_clock_cases.py',
                 'engine_ladder.py'],
    'archival-scenarios': ['compare_reference.py'],
    'nielsen': ['nielsen_releases.py'],
    'rating-sources': ['fetch_rating_lists.py'],
    'participation': ['rating_participation.py'],
    'twic-2014': ['audit_freestyle_2014.py'],
    'learning-sources': ['fetch_learning_corpus.py'],
    'learning-audit': ['audit_learning_corpus.py'],
    'learning-sample': ['sample_learning_pilot.py', 'join_pilot_birth_years.py'],
    'learning-score': ['score_learning_pilot.py'],
    'pawn-patterns': ['count_pawn_patterns.py'],
    'advice': ['compare_advice.py', 'summarise_advice.py', 'advice_noise_floor.py'],
    'panels': ['build_panels.py', 'advice_noise_floor.py', 'plot_panels.py', 'plot_research_results.py'],
    'check': ['check_engine_repeatability.py', 'check_reference.py', 'check_pawn_patterns.py',
              'check_learning_pilot.py'],
}


#%% main
def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('stages', nargs='+', choices=[*STAGES, 'all'])
    args = parser.parse_args()
    # the retired local archive is optional and is not available in a fresh checkout
    selected = set(STAGES) - {'corpus', 'learning-sources', 'learning-audit', 'learning-sample', 'learning-score', 'pawn-patterns', 'advice', 'archival-scenarios'} if 'all' in args.stages else set(args.stages)
    root = Path(__file__).resolve().parents[1]
    (root / 'data/derived').mkdir(exist_ok=True)
    if (root / 'cache').is_symlink() and not (root / 'cache').exists():
        (root / 'cache').resolve().mkdir(parents=True, exist_ok=True)
    elif not (root / 'cache').exists():
        cache = Path.home() / 'Library/Caches/chess-evolution'
        cache.mkdir(parents=True, exist_ok=True)
        (root / 'cache').symlink_to(cache, target_is_directory=True)
    for stage, scripts in STAGES.items():
        if stage not in selected:
            continue
        for script in scripts:
            print(script, flush=True)
            subprocess.run([sys.executable, str(root / 'scripts' / script)], cwd=root, check=True)


if __name__ == '__main__':
    main()
