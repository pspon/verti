import streamlit as st
import pandas as pd
import plotly.express as px

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

#st.dataframe(df_filtered)

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

st.plotly_chart(fig)
