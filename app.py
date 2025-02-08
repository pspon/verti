import streamlit as st
import pandas as pd
import plotly.express as px
import datetime

st.set_page_config(layout="wide")

# Load the dataset
file_path = "2025-seeds.csv"
df = pd.read_csv(file_path)

# Convert date columns to datetime format
df["Start Indoors"] = pd.to_datetime(df["Start Indoors"], errors='coerce')
df["Transplant / Sow"] = pd.to_datetime(df["Transplant / Sow"], errors='coerce')

# Rename columns for clarity
df = df.rename(columns={"Start Indoors": "Start Date", "Transplant / Sow": "End Date"})

# Create a combined seed name from Seed and Variant columns
df['Seed'] = df['Seed'].astype(str)
df['Variant'] = df['Variant'].astype(str)
df['Seed'] = df[['Seed', 'Variant']].agg(' '.join, axis=1)

# For Direct Sow, adjust the start date to be 3 days before the end date
indices = df[df["Planting Method"] == "Direct Sow"].index
df.loc[indices, "Start Date"] = df.loc[indices, "End Date"] - pd.Timedelta(days=3)

# -------------------------------
# Sidebar Filters
# -------------------------------
st.sidebar.header("Filters")

# Filter for Season (if the column exists)
if "Season" in df.columns:
    distinct_seasons = sorted(df["Season"].dropna().unique())
    selected_seasons = st.sidebar.multiselect("Select Seasons:", distinct_seasons, default=distinct_seasons)
else:
    selected_seasons = None

# Filter for Frost (if the column exists)
if "Frost" in df.columns:
    distinct_frost = sorted(df["Frost"].dropna().unique())
    selected_frost = st.sidebar.multiselect("Select Frost values:", distinct_frost, default=distinct_frost)
else:
    selected_frost = None

# Explicit filter for Planting Method (this filter controls which legend items appear)
distinct_methods = sorted(df["Planting Method"].dropna().unique())
selected_methods = st.sidebar.multiselect("Select Planting Methods:", distinct_methods, default=distinct_methods)

# Filter for Seeds (by full seed name)
distinct_seeds = sorted(df["Seed"].unique())
selected_seeds = st.sidebar.multiselect("Select Seeds to Display:", distinct_seeds, default=distinct_seeds)

# -------------------------------
# Data Filtering
# -------------------------------
df_filtered = df.copy()

if selected_seasons is not None and len(selected_seasons) > 0:
    df_filtered = df_filtered[df_filtered["Season"].isin(selected_seasons)]

if selected_frost is not None and len(selected_frost) > 0:
    df_filtered = df_filtered[df_filtered["Frost"].isin(selected_frost)]

if selected_methods is not None and len(selected_methods) > 0:
    df_filtered = df_filtered[df_filtered["Planting Method"].isin(selected_methods)]

if selected_seeds is not None and len(selected_seeds) > 0:
    df_filtered = df_filtered[df_filtered["Seed"].isin(selected_seeds)]

# -------------------------------
# Growing Season Range and Data Display
# -------------------------------
growing_season_start = "2025-01-01"
growing_season_end = "2025-10-13"

# -------------------------------
# Sorting Seeds by Start Date
# -------------------------------
ordered_seeds = (
    df_filtered.groupby("Seed")["Start Date"]
    .min()
    .sort_values()
    .index
    .tolist()
)

# -------------------------------
# Create Timeline Chart
# -------------------------------
fig = px.timeline(
    df_filtered, 
    x_start="Start Date", 
    x_end="End Date", 
    y="Seed", 
    color="Planting Method",
    title="Planting Schedule", 
    labels={"Planting Method": "Planting Stage"},
    category_orders={"Seed": ordered_seeds}  # orders y-axis by earliest start date
)

# Adjust the figure height based on the number of seeds (40px per seed, minimum 600px)
num_seeds = df_filtered["Seed"].nunique()
fig.update_layout(height=max(600, 40 * num_seeds))

# Increase left margin and enable automargin for long y-axis labels
fig.update_layout(
    margin=dict(l=200, r=20, t=50, b=20),
    yaxis=dict(automargin=True)
)

# Set x-axis range to cover the growing season
fig.update_xaxes(range=[growing_season_start, growing_season_end])

# -------------------------------------------
# Add vertical line for "today"
# -------------------------------------------
# Get the current date (if today is outside the growing season, the line may not be visible)
today = datetime.datetime.today().date()
fig.add_shape(
    dict(
         type="line",
         x0=today,
         y0=0,
         x1=today,
         y1=1,
         xref="x",
         yref="paper",
         line=dict(color="red", dash="dot", width=2)
    )
)

# -------------------------------------------
# Add week-by-week shaded regions
# -------------------------------------------
start_date = pd.to_datetime(growing_season_start)
end_date = pd.to_datetime(growing_season_end)
current_date = start_date
shade_week = True  # toggle for alternating shading

while current_date < end_date:
    week_end = current_date + pd.Timedelta(days=7)
    # Shade alternate weeks
    if shade_week:
         fig.add_vrect(
             x0=current_date,
             x1=week_end,
             fillcolor="LightGrey",
             opacity=0.2,
             layer="below",
             line_width=0,
         )
    shade_week = not shade_week
    current_date = week_end

# -------------------------------------------
# Add x-axis zoom bar (range slider)
# -------------------------------------------
fig.update_xaxes(rangeslider_visible=True)

st.plotly_chart(fig)
