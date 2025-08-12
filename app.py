import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import matplotlib.pyplot as plt

# Your existing functions (seasonal_factor, calc_liters_by_category, simulate_flow_based)
# but slightly adapted to take drink_types as input


def seasonal_factor(day_of_year, min_mult=1, max_mult=2):
    amplitude = (max_mult - min_mult) / 2
    midpoint = (max_mult + min_mult) / 2
    return midpoint + amplitude * np.cos(2 * np.pi * (day_of_year - 180) / 365)

def calc_liters_by_category(daily_guests, drink_types):
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

# Streamlit UI

st.title("Alcohol Consumption Simulator")

year = st.number_input("Year for simulation", min_value=2000, max_value=2100, value=2025)

capacity = st.number_input("Venue Capacity", min_value=1, max_value=1000, value=100)

# Define default drink_types for user editing
default_drinks = {
    'beer': {'category': 'light', 'avg_drinks': 3, 'volume': 0.5, 'share': 0.4},
    'wine': {'category': 'light', 'avg_drinks': 2, 'volume': 0.15, 'share': 0.3},
    'cocktail': {'category': 'heavy', 'avg_drinks': 2, 'volume': 0.2, 'share': 0.2},
    'raki': {'category': 'heavy', 'avg_drinks': 1, 'volume': 0.1, 'share': 0.1},
}

st.write("### Adjust Drink Parameters")

drink_types = {}
for drink, params in default_drinks.items():
    st.write(f"**{drink.capitalize()}** ({params['category']})")

    avg_drinks = st.number_input(
        f"Avg drinks per guest for {drink}",
        min_value=0.0,
        max_value=10.0,
        value=float(params['avg_drinks']),
        step=0.1,
        format="%.2f",
        key=f"{drink}_avg_drinks"
    )

    volume = st.number_input(
        f"Volume per drink (liters) for {drink}",
        min_value=0.0,
        max_value=5.0,
        value=float(params['volume']),
        step=0.01,
        format="%.3f",
        key=f"{drink}_volume"
    )

    share = st.number_input(
        f"Share of guests choosing {drink}",
        min_value=0.0,
        max_value=1.0,
        value=float(params['share']),
        step=0.01,
        format="%.2f",
        key=f"{drink}_share"
    )

    drink_types[drink] = {
        'category': params['category'],
        'avg_drinks': avg_drinks,
        'volume': volume,
        'share': share
    }

total_share = sum(d['share'] for d in drink_types.values())
if total_share == 0:
    st.error("Total share cannot be zero. Please adjust shares.")
else:
    # Normalize shares so they sum to 1
    for d in drink_types.values():
        d['share'] /= total_share

    if st.button("Run Simulation"):
        df = simulate_flow_based(capacity=capacity, year=year, drink_types=drink_types)

        # Plotting
        df['date_only'] = df['date'].dt.date
        daily_totals = df.groupby('date_only')[['light_liters', 'heavy_liters', 'total_liters']].sum()

        st.subheader("Estimated Daily Alcohol Consumption (Liters) Over One Year")
        fig, ax = plt.subplots(figsize=(14, 7))
        ax.plot(daily_totals.index, daily_totals['light_liters'], label='Light Drinks', color='skyblue')
        ax.plot(daily_totals.index, daily_totals['heavy_liters'], label='Heavy Drinks', color='orange')
        ax.plot(daily_totals.index, daily_totals['total_liters'], label='Total Drinks', color='green', linestyle='--')
        ax.set_title('Estimated Daily Alcohol Consumption (Liters) Over One Year')
        ax.set_xlabel('Date')
        ax.set_ylabel('Liters Consumed')
        ax.legend()
        ax.grid(True)
        st.pyplot(fig)

        # Yearly totals
        yearly_totals = df[['guests', 'drinks', 'light_liters', 'heavy_liters', 'total_liters']].sum().round(2)
        st.subheader("Yearly Totals")
        st.dataframe(yearly_totals.to_frame(name='Total'))

        # Monthly totals
        df['month'] = df['date'].dt.month
        monthly_totals = df.groupby('month')[
            ['guests', 'drinks', 'light_liters', 'heavy_liters', 'total_liters']].sum().round(2)
        st.subheader("Monthly Totals")
        st.dataframe(monthly_totals)

