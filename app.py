import streamlit as st
import pandas as pd
import plotly.express as px

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

# Streamlit App Title
st.title("Seed Planting Timeline for 2025")

# Dropdown filter for seeds
distinct_seeds = sorted(df["Seed"].unique())
selected_seeds = st.multiselect("Select Seeds to Display:", distinct_seeds, default=distinct_seeds)

# Filter the DataFrame based on selection
df_filtered = df[df["Seed"].isin(selected_seeds)]

# Define the growing season range for the x-axis
growing_season_start = "2025-01-01"
growing_season_end = "2025-12-31"

st.dataframe(df_filtered)

# Determine the ordering of seeds by their earliest start date
ordered_seeds = (
    df_filtered.groupby("Seed")["Start Date"]
    .min()
    .sort_values()
    .index
    .tolist()
)

# Create the timeline chart and specify the ordering of the y-axis
fig = px.timeline(
    df_filtered, 
    x_start="Start Date", 
    x_end="End Date", 
    y="Seed", 
    color="Planting Method",
    title="Planting Schedule", 
    labels={"Planting Method": "Planting Stage"},
    category_orders={"Seed": ordered_seeds}  # This orders the y-axis by start date
)

# Optionally, adjust figure height based on the number of seeds
num_seeds = df_filtered["Seed"].nunique()
fig.update_layout(height=max(600, 40 * num_seeds))

# Expand left margin and enable automargin so that long labels are fully visible
fig.update_layout(
    margin=dict(l=200, r=20, t=50, b=20),
    yaxis=dict(automargin=True)
)

# Set the x-axis range to the growing season dates
fig.update_xaxes(range=[growing_season_start, growing_season_end])

st.plotly_chart(fig)
