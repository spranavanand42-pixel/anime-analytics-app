import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import sqlite3

# -----------------------------
# PAGE CONFIG
# -----------------------------
st.set_page_config(
    page_title="Anime Analytics",
    layout="wide"
)

# -----------------------------
# DATABASE SETUP
# -----------------------------
conn = sqlite3.connect("anime.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS anime (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    Anime TEXT,
    Genre TEXT,
    MAL REAL,
    Your_Rating REAL
)
""")
conn.commit()

# -----------------------------
# LOAD DATA FROM DATABASE
# -----------------------------
@st.cache_data
def load_data():
    df = pd.read_sql_query("SELECT * FROM anime", conn)
    if not df.empty:
        df["Bias"] = df["Your_Rating"] - df["MAL"]
        df.rename(columns={"Your_Rating": "Your Rating"}, inplace=True)
    return df

df = load_data()

# -----------------------------
# FETCH POSTER + MAL LINK
# -----------------------------
@st.cache_data
def get_anime_data(title):
    url = f"https://api.jikan.moe/v4/anime?q={title}&limit=1"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data["data"]:
                anime = data["data"][0]
                return {
                    "image": anime["images"]["jpg"]["large_image_url"],
                    "mal_url": anime["url"]
                }
    except:
        pass
    return None

# -----------------------------
# ADD NEW ANIME SECTION
# -----------------------------
st.sidebar.title("➕ Add Anime")

with st.sidebar.form("add_anime"):
    name = st.text_input("Anime Name")
    genre = st.text_input("Genre")
    mal_rating = st.number_input("MAL Rating", 0.0, 10.0, step=0.01)
    your_rating = st.number_input("Your Rating", 0.0, 10.0, step=0.5)

    submitted = st.form_submit_button("Add")

    if submitted and name:
        cursor.execute(
            "INSERT INTO anime (Anime, Genre, MAL, Your_Rating) VALUES (?, ?, ?, ?)",
            (name, genre, mal_rating, your_rating)
        )
        conn.commit()
        st.cache_data.clear()
        st.rerun()

# -----------------------------
# SIDEBAR FILTERS
# -----------------------------
st.sidebar.title("Filters")

if not df.empty:
    genre_options = df["Genre"].unique()

    selected_genres = st.sidebar.multiselect(
        "Select Genre",
        options=genre_options,
        default=genre_options
    )

    min_rating = st.sidebar.slider(
        "Minimum Your Rating",
        min_value=1,
        max_value=10,
        value=1
    )

    filtered_df = df[
        (df["Genre"].isin(selected_genres)) &
        (df["Your Rating"] >= min_rating)
    ]
else:
    filtered_df = df

# -----------------------------
# TITLE
# -----------------------------
st.title("🎬 Anime Analytics Dashboard")

if not filtered_df.empty:

    # -----------------------------
    # METRICS
    # -----------------------------
    col1, col2, col3 = st.columns(3)

    col1.metric("Average Your Rating", round(filtered_df["Your Rating"].mean(), 2))
    col2.metric("Average MAL Rating", round(filtered_df["MAL"].mean(), 2))
    col3.metric("Average Bias", round(filtered_df["Bias"].mean(), 2))

    st.divider()

    # -----------------------------
    # SCATTER PLOT
    # -----------------------------
    fig_scatter = px.scatter(
        filtered_df,
        x="MAL",
        y="Your Rating",
        hover_name="Anime",
        title="MAL vs Your Rating"
    )

    fig_scatter.update_layout(height=500)
    st.plotly_chart(fig_scatter, use_container_width=True)

    # -----------------------------
    # BIAS CHART
    # -----------------------------
    fig_bias = px.bar(
        filtered_df.sort_values("Bias", ascending=False),
        x="Anime",
        y="Bias",
        title="Bias (Your Rating - MAL)"
    )

    fig_bias.update_layout(
        height=450,
        xaxis=dict(tickangle=-45)
    )

    st.plotly_chart(fig_bias, use_container_width=True)

    st.divider()

    # -----------------------------
    # ANIME LIBRARY
    # -----------------------------
    st.subheader("Anime Library")

    for _, row in filtered_df.iterrows():
        col1, col2 = st.columns([1, 3])

        anime_data = get_anime_data(row["Anime"])

        if anime_data:
            col1.image(anime_data["image"], width=220)
            col2.markdown(f"### [{row['Anime']}]({anime_data['mal_url']})")
        else:
            col1.write("No Image Found")
            col2.markdown(f"### {row['Anime']}")

        col2.write(f"**Genre:** {row['Genre']}")
        col2.write(
            f"**MAL:** {row['MAL']} | "
            f"**Your Rating:** {row['Your Rating']} | "
            f"**Bias:** {round(row['Bias'], 2)}"
        )

        st.divider()

    # -----------------------------
    # DATA TABLE
    # -----------------------------
    st.subheader("Full Data Table")
    st.dataframe(filtered_df, use_container_width=True)

else:
    st.info("No anime in database yet.")