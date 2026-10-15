'''
Created on 15 October 2026

compare novelty trends with fixed and growing championship references

@author: Dinghao Luo
'''

#%% imports
import csv
from collections import defaultdict
from pathlib import Path
from statistics import median

import numpy as np
from statsmodels.regression.linear_model import OLS


#%% medians and trends
def departure_median(rows: list[dict], field: str = 'first_novelty_ply') -> float:
    lower = [int(row[field]) if row[field] else int(row['plies']) + 1 for row in rows]
    upper = [int(row[field]) if row[field] else np.inf for row in rows]
    # a game without a departure gives only a lower bound
    assert median(lower) == median(upper), 'censoring leaves the median unidentified'
    return median(lower)


def fit_trend(years: list[int], values: list[float], lag: int) -> dict:
    years = np.asarray(years)
    values = np.asarray(values)
    design = np.column_stack((np.ones(len(years)), (years - years.mean()) / 100))
    # newey-west with bartlett weights; lags count observed championship years
    model = OLS(values, design)
    fit = model.fit(cov_type='HAC', cov_kwds={'maxlags': lag, 'use_correction': True}, use_t=True)
    low, high = fit.conf_int()[1]
    return {
        'start_year': int(years.min()),
        'end_year': int(years.max()),
        'years': len(years),
        'slope_plies_per_century': fit.params[1],
        'hac_lag': lag,
        'ci95_low': low,
        'ci95_high': high,
        'hac_p': fit.pvalues[1],
        'ordinary_p': model.fit().pvalues[1],
    }


#%% load
DATA = Path('data')
by_year = defaultdict(list)
with (DATA / 'novelty.csv').open() as source:
    for row in csv.DictReader(source):
        # use the first match to initialise the archive
        if row['event_id'] != 'world_1886':
            by_year[int(row['year'])].append(row)
sampled = defaultdict(list)
with (DATA / 'novelty_sensitivity.csv').open() as source:
    for row in csv.DictReader(source):
        sampled[int(row['year']), int(row['seed'])].append(row)
years = sorted(by_year)
seeds = sorted({seed for _, seed in sampled})
# compare the same games in both references
matched_years = [year for year in years if all(int(row['reference_games']) >= 100 for row in by_year[year])]
summary = []
for year in years:
    sample_medians = [departure_median(sampled[year, seed]) for seed in seeds] if year in matched_years else []
    summary.append({
        'year': year,
        'games': len(by_year[year]),
        'censored_games': sum(int(row['censored']) for row in by_year[year]),
        'growing_archive_median': departure_median(by_year[year]),
        'earlier_events_median': departure_median(by_year[year], 'earlier_event_novelty_ply'),
        'fixed_100_median': median(sample_medians) if sample_medians else '',
        'fixed_100_p10': np.percentile(sample_medians, 10) if sample_medians else '',
        'fixed_100_p90': np.percentile(sample_medians, 90) if sample_medians else '',
    })


#%% archive and chronology sensitivity
trends = []
for field in ['growing_archive_median', 'earlier_events_median', 'fixed_100_median']:
    for window, selected in [('all_years', summary), ('matched_years', [row for row in summary if row['year'] in matched_years])]:
        if field == 'fixed_100_median' and window == 'all_years':
            continue
        for lag in [0, 1, 3, 5]:
            trend = fit_trend([row['year'] for row in selected], [row[field] for row in selected], lag)
            trends.append({'measure': field, 'window': window, **trend})
# spread across samples of the same archive
for seed in seeds:
    trend = fit_trend(matched_years, [departure_median(sampled[year, seed]) for year in matched_years], 3)
    trends.append({'measure': f'fixed_100_seed_{seed}', 'window': 'matched_years', **trend})


#%% write
for name, rows in [('novelty_year_summary.csv', summary), ('novelty_trends.csv', trends)]:
    with (DATA / name).open('w', newline='') as destination:
        writer = csv.DictWriter(destination, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
for row in trends:
    if row['hac_lag'] == 3 and row['measure'] in ['growing_archive_median', 'fixed_100_median']:
        measure, window = row['measure'], row['window']
        slope, low, high, p = (row[key] for key in ['slope_plies_per_century', 'ci95_low', 'ci95_high', 'hac_p'])
        print(f'{measure}, {window}: {slope:+.2f} plies/century; 95% interval [{low:.2f}, {high:.2f}], p={p:.3g}')
