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
df = df.rename(columns={"Start Indoors": "Start Date", "Transplant / Sow": "End Date"})

# Create full name
df['Seed'] = df['Seed'].astype(str)
df['Variant'] = df['Variant'].astype(str)
df['Seed'] = df[['Seed', 'Variant']].agg(' '.join, axis=1)

# Create span for direct sow
indices = df[df["Planting Method"] == "Direct Sow"].index
df.loc[indices, "Start Date"] = df.loc[indices, "End Date"] - pd.Timedelta(days=3)

# Streamlit App
st.title("Seed Planting Timeline for 2025")

# Dropdown filter
distinct_seeds = sorted(df["Seed"].unique())
selected_seeds = st.multiselect("Select Seeds to Display:", distinct_seeds, default=distinct_seeds)

# Filter data based on selection
df_filtered = df[df["Seed"].isin(selected_seeds)]

# Define growing season range
growing_season_start = "2025-01-01"
growing_season_end = "2025-12-31"

st.dataframe(df_filtered)

# Plot timeline
fig = px.timeline(
    df_filtered, 
    x_start="Start Date", 
    x_end="End Date", 
    y="Seed", 
    color="Planting Method",
    title="Planting Schedule", 
    labels={"Planting Method": "Planting Stage"}
)

# Ensure the y-axis shows all labels:
fig.update_yaxes(categoryorder="total ascending")

# Optionally, adjust figure height based on the number of seeds
num_seeds = df_filtered["Seed"].nunique()
# Adjust the height per item (e.g., 40 pixels per seed) with a minimum height of 600
fig.update_layout(height=max(600, 40 * num_seeds))

# Expand left margin and enable automargin so that long labels are fully visible
fig.update_layout(
    margin=dict(l=200, r=20, t=50, b=20),
    yaxis=dict(automargin=True)
)

# Set the x-axis range to the growing season dates
fig.update_xaxes(range=[growing_season_start, growing_season_end])

st.plotly_chart(fig)
