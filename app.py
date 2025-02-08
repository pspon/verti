import streamlit as st
import pandas as pd
import plotly.express as px

# Load the dataset
file_path = "2025-seeds.csv"
df = pd.read_csv(file_path)

# Convert date columns to datetime format
df["Start Indoors"] = pd.to_datetime(df["Start Indoors"], errors='coerce')
df["Transplant / Sow"] = pd.to_datetime(df["Transplant / Sow"], errors='coerce')

# Modify column names
df.rename(columns={"Start Indoors": "Start Date", "Transplant / Sow": "End Date"})

# Remove rows with missing dates
df = df.dropna(subset=["Start Indoors", "Transplant / Sow"])

# Melt data for visualization
df_melted = df.copy()

# Streamlit App
st.title("Seed Planting Timeline for 2025")

# Dropdown filter
distinct_seeds = sorted(df["Seed"].unique())
selected_seeds = st.multiselect("Select Seeds to Display:", distinct_seeds, default=distinct_seeds)

# Filter data based on selection
df_filtered = df_melted[df_melted["Seed"].isin(selected_seeds)]

# Define growing season range
growing_season_start = "2025-01-01"
growing_season_end = "2025-12-31"

st.dataframe(df_filtered)

# Plot timeline
fig = px.timeline(df_filtered, x_start="Start Date", x_end="End Date", y="Seed",
                  title="Planting Schedule")
fig.update_yaxes(categoryorder="total ascending")
fig.update_xaxes(range=[growing_season_start, growing_season_end])

st.plotly_chart(fig)
