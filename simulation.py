import pandas as pd
import numpy as np
from datetime import datetime


def seasonal_factor(day_of_year, min_mult=1, max_mult=2):
    """
    Calculates a seasonal multiplier based on the day of the year.
    """
    amplitude = (max_mult - min_mult) / 2
    midpoint = (max_mult + min_mult) / 2
    return midpoint + amplitude * np.cos(2 * np.pi * (day_of_year - 180) / 365)


def calc_liters_by_category(daily_guests, drink_types):
    """
    Calculates liters consumed for each drink category.
    """
    liters_sum_by_category = {'light': 0, 'heavy': 0}
    for drink, info in drink_types.items():
        drink_guests = daily_guests * info['share']
        drinks = drink_guests * info['avg_drinks']
        liters = drinks * info['volume']
        liters_sum_by_category[info['category']] += liters
    return {
        'light_liters': liters_sum_by_category['light'],
        'heavy_liters': liters_sum_by_category['heavy']
    }


def simulate_flow_based(capacity, year, drink_types):
    """
    Runs the full alcohol consumption simulation for one year.
    """
    start_date = datetime(year - 1, 6, 1)
    end_date = datetime(year, 6, 1)
    date_range = pd.date_range(start=start_date, end=end_date, freq='D')

    DOW_FACTOR = {0: 0.17, 1: 0.19, 2: 0.15, 3: 0.16, 4: 0.22, 5: 0.32, 6: 0.18}
    hourly_occupancy_percent = {
        6: 0, 7: 0, 8: 0, 9: 18, 10: 57, 11: 29,
        12: 34, 13: 41, 14: 45, 15: 47, 16: 48, 17: 52,
        18: 58, 19: 63, 20: 70, 21: 73, 22: 73, 23: 62,
        0: 45, 1: 30, 2: 15, 3: 0, 4: 0, 5: 0
    }
    records = []

    for date in date_range:
        day_of_year = date.timetuple().tm_yday
        dow = date.weekday()
        seasonal_mult = seasonal_factor(day_of_year)
        dow_mult = DOW_FACTOR[dow]

        prev_occ = None
        daily_guests = 0
        for hour in range(24):
            occ_percent = hourly_occupancy_percent.get(hour, 0) / 100.0
            occ_people = capacity * occ_percent * seasonal_mult
            if prev_occ is not None:
                change = occ_people - prev_occ
                if change > 0:
                    daily_guests += change
            prev_occ = occ_people
        daily_guests *= dow_mult

        liters = calc_liters_by_category(daily_guests, drink_types)
        total_drinks = sum(
            daily_guests * info['avg_drinks'] * info['share'] for info in drink_types.values()
        )
        records.append({
            'date': date,
            'guests': daily_guests,
            'drinks': total_drinks,
            'light_liters': liters['light_liters'],
            'heavy_liters': liters['heavy_liters'],
            'total_liters': liters['light_liters'] + liters['heavy_liters']
        })
    return pd.DataFrame(records)