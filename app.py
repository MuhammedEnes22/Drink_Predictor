import streamlit as st
import pandas as pd
import plotly.express as px
import matplotlib.pyplot as plt
from io import BytesIO
import zipfile

# Import the simulation function
from simulation import simulate_flow_based

# --- Streamlit UI ---
st.set_page_config(page_title="Alcohol Consumption Simulator", layout="wide")
st.title("Alcohol Consumption Simulator")

# Use a sidebar for general, high-level parameters
st.sidebar.header("General Parameters")
year = st.sidebar.number_input("Year for simulation", min_value=2000, max_value=2100, value=2025, key="sim_year")
capacity = st.sidebar.number_input("Venue Capacity", min_value=1, max_value=1000, value=100, key="sim_capacity")

# Use the main page for the more detailed drink editor
st.header("Drink Customization")
st.markdown(
    "Edit the parameters for each drink type in the table below. You can add new drinks or remove existing ones.")

# Define the default DataFrame
default_drinks_df = pd.DataFrame([
    {'drink': 'beer', 'category': 'light', 'avg_drinks': 2.5, 'volume': 0.5, 'share': 0.4},
    {'drink': 'wine', 'category': 'light', 'avg_drinks': 2, 'volume': 0.15, 'share': 0.3},
    {'drink': 'cocktail', 'category': 'heavy', 'avg_drinks': 2, 'volume': 0.2, 'share': 0.2},
    {'drink': 'rakı', 'category': 'heavy', 'avg_drinks': 1, 'volume': 0.1, 'share': 0.1},
])

edited_df = st.data_editor(
    default_drinks_df,
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "share": st.column_config.NumberColumn(
            "Share", help="Proportion of guests choosing this drink", min_value=0.0, max_value=1.0, step=0.01,
            format="%.2f",
        ),
        "avg_drinks": st.column_config.NumberColumn(
            "Avg Drinks", help="Average number of drinks per guest", min_value=0.0, max_value=10.0, step=0.1,
            format="%.1f",
        ),
        "volume": st.column_config.NumberColumn(
            "Volume (L)", help="Volume per drink in liters", min_value=0.0, max_value=10.0, step=0.01,
            format="%.2f",
        ),
    }
)

total_share = edited_df['share'].sum()
if total_share == 0:
    st.error("Total share cannot be zero. Please adjust shares.")
    st.session_state['can_run'] = False
else:
    edited_df['share'] = edited_df['share'] / total_share
    st.session_state['can_run'] = True

if st.button("Run Simulation", use_container_width=True, type="primary",
             disabled=not st.session_state.get('can_run', False)):
    with st.spinner("Running simulation..."):
        # Convert DataFrame to dictionary format for the simulation function
        drink_types = {row['drink']: row[1:].to_dict() for index, row in edited_df.iterrows()}
        # Call the simulation function from the imported file
        df = simulate_flow_based(capacity, year, drink_types)

        # Store results in session_state
        st.session_state['simulation_results_df'] = df
        st.session_state['simulation_drinks_df'] = edited_df

# --- Display Results and Download Options ---
if 'simulation_results_df' in st.session_state:
    df = st.session_state['simulation_results_df']
    edited_df = st.session_state['simulation_drinks_df']

    st.subheader("Simulation Results")

    # Plotting with Plotly for interactivity (view-only)
    df['date_only'] = df['date'].dt.date
    daily_totals_df = df.groupby('date_only')[['light_liters', 'heavy_liters', 'total_liters']].sum().reset_index()

    fig_plotly = px.line(
        daily_totals_df,
        x='date_only',
        y=['light_liters', 'heavy_liters', 'total_liters'],
        title="Estimated Daily Alcohol Consumption (Liters) Over One Year",
        labels={'value': 'Liters Consumed', 'variable': 'Drink Category', 'date_only': 'Date'},
        color_discrete_map={'light_liters': 'skyblue', 'heavy_liters': 'orange', 'total_liters': 'green'}
    )
    st.plotly_chart(fig_plotly, use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        yearly_totals = df[['guests', 'drinks', 'light_liters', 'heavy_liters', 'total_liters']].sum().round(2)
        st.subheader("Yearly Totals")
        st.dataframe(yearly_totals.to_frame(name='Total'), use_container_width=True)

    with col2:
        df['month'] = df['date'].dt.month
        monthly_totals = df.groupby('month')[
            ['guests', 'drinks', 'light_liters', 'heavy_liters', 'total_liters']].sum().round(2)
        st.subheader("Monthly Totals")
        st.dataframe(monthly_totals, use_container_width=True)

    st.markdown("---")
    st.header("Download Results")
    download_col1, download_col2, download_col3, download_col4 = st.columns(4)

    # Prepare matplotlib plot for download
    fig_mpl, ax = plt.subplots(figsize=(14, 7))
    ax.plot(daily_totals_df['date_only'], daily_totals_df['light_liters'], label='Light Drinks', color='skyblue')
    ax.plot(daily_totals_df['date_only'], daily_totals_df['heavy_liters'], label='Heavy Drinks', color='orange')
    ax.plot(daily_totals_df['date_only'], daily_totals_df['total_liters'], label='Total Drinks', color='green',
            linestyle='--')
    ax.set_title('Estimated Daily Alcohol Consumption (Liters) Over One Year')
    ax.set_xlabel('Date')
    ax.set_ylabel('Liters Consumed')
    ax.legend()
    ax.grid(True)

    img_buffer_mpl = BytesIO()
    fig_mpl.savefig(img_buffer_mpl, format='png')
    img_buffer_mpl.seek(0)
    plt.close(fig_mpl)  # Crucial to close the figure to prevent memory leaks

    with download_col1:
        # Prepare ZIP in memory
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zf:
            yearly_csv = yearly_totals.to_csv(index=True)
            zf.writestr("yearly_totals.csv", yearly_csv)

            monthly_csv = monthly_totals.to_csv(index=True)
            zf.writestr("monthly_totals.csv", monthly_csv)

            # Add the matplotlib plot to the zip
            zf.writestr("consumption_plot.png", img_buffer_mpl.getvalue())

        zip_buffer.seek(0)
        st.download_button(
            label="Download All as ZIP",
            data=zip_buffer,
            file_name="simulation_results.zip",
            mime="application/zip",
            use_container_width=True
        )

    with download_col2:
        csv = yearly_totals.to_csv(index=True).encode('utf-8')
        st.download_button(
            label="Download Yearly Totals",
            data=csv,
            file_name="yearly_totals.csv",
            mime="text/csv",
            use_container_width=True
        )

    with download_col3:
        csv = monthly_totals.to_csv(index=True).encode('utf-8')
        st.download_button(
            label="Download Monthly Totals",
            data=csv,
            file_name="monthly_totals.csv",
            mime="text/csv",
            use_container_width=True
        )

    with download_col4:
        st.download_button(
            label="Download Plot as PNG",
            data=img_buffer_mpl,
            file_name="consumption_plot.png",
            mime="image/png",
            use_container_width=True
        )
