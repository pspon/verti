import streamlit as st
import pandas as pd
import plotly.express as px

# Load the dataset
file_path = "2025-seeds.csv"
df = pd.read_csv(file_path)

# Convert date columns to datetime format
df["Start Indoors"] = pd.to_datetime(df["Start Indoors"], errors='coerce')
df["Transplant / Sow"] = pd.to_datetime(df["Transplant / Sow"], errors='coerce')

# Remove rows with missing dates
df = df.dropna(subset=["Start Indoors", "Transplant / Sow"])

# Melt data for visualization
df_melted = df.melt(id_vars=["Seed"], value_vars=["Start Indoors", "Transplant / Sow"],
                     var_name="Stage", value_name="Date")

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

# Plot timeline
fig = px.timeline(df_filtered, x_start="Date", x_end="Date", y="Seed", color="Stage",
                  title="Planting Schedule", labels={"Stage": "Planting Stage"})
fig.update_yaxes(categoryorder="total ascending")
fig.update_xaxes(range=[growing_season_start, growing_season_end])

st.plotly_chart(fig)
