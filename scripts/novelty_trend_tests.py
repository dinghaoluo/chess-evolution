'''
Created on 15 October 2026

test yearly novelty trends

@author: Dinghao Luo
'''

#%% imports
import csv
from pathlib import Path

import numpy as np
from statsmodels.regression.linear_model import OLS


#%% calendar-year uncertainty
def calendar_trend(years: np.ndarray, values: np.ndarray, bandwidth: int) -> dict:
    # one observation per year; slope in plies per century
    design = np.column_stack((np.ones(len(years)), (years - years.mean()) / 100))
    fit = OLS(values, design).fit()
    scores = design * fit.resid[:, None]
    # use calendar gaps: title matches were not held at regular intervals
    distances = abs(years[:, None] - years[None, :])
    weights = np.maximum(1 - distances / (bandwidth + 1), 0)
    xtx_inverse = fit.normalized_cov_params
    covariance = xtx_inverse @ (scores.T @ weights @ scores) @ xtx_inverse
    covariance *= len(years) / fit.df_resid
    test = fit.t_test([0, 1], cov_p=covariance, use_t=True)
    low, high = test.conf_int()[0]
    return {
        'start_year': int(years.min()), 'end_year': int(years.max()), 'years': len(years),
        'bandwidth_years': bandwidth, 'slope_plies_per_century': fit.params[1],
        'ci95_low': low, 'ci95_high': high, 'two_sided_p': float(test.pvalue),
    }


#%% annual comparisons
DATA = Path('data')


def main() -> None:
    with (DATA / 'master_novelty_years.csv').open() as source:
        full = list(csv.DictReader(source))
    with (DATA / 'master_novelty_sampling_years.csv').open() as source:
        sampled = {row['year']: row for row in csv.DictReader(source)}
    assert all(row['prior_year_first_new_ply_median_lower'] == row['prior_year_first_new_ply_median_upper']
               for row in full)
    years = np.array([int(row['year']) for row in full])
    full_values = np.array([float(row['prior_year_first_new_ply_median']) for row in full])
    fixed_values = np.array([float(sampled[row['year']]['median_of_sample_medians']) for row in full])
    results = []
    # test the difference between trends on the same years
    for measure, values in [('full_reference', full_values), ('fixed_1000', fixed_values),
                            ('full_minus_fixed_1000', full_values - fixed_values)]:
        for since in [1886, 1970]:
            selected = years >= since
            # decade-scale dependence, checked with shorter and longer windows
            for bandwidth in [5, 10, 20]:
                results.append({'measure': measure,
                                **calendar_trend(years[selected], values[selected], bandwidth)})

    with (DATA / 'novelty_trend_tests.csv').open('w', newline='') as destination:
        writer = csv.DictWriter(destination, fieldnames=list(results[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(results)


if __name__ == '__main__':
    main()
