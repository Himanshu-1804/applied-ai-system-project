"""
Music Recommender — Streamlit visual interface.

Run from the project root:
    streamlit run src/app.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st

from recommender import load_songs, recommend_songs, score_song
from guardrails import validate_user_prefs
from llm_client import parse_preferences, generate_rag_explanation

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="AI Music Recommender",
    page_icon="🎵",
    layout="wide",
)

# ── Load catalog once (cached) ────────────────────────────────────────────────

@st.cache_data
def _load_catalog():
    return load_songs("data/songs.csv")

songs = _load_catalog()

# ── Sidebar: catalog overview ─────────────────────────────────────────────────

genre_counts: dict = {}
for s in songs:
    genre_counts[s["genre"]] = genre_counts.get(s["genre"], 0) + 1

with st.sidebar:
    st.title("🎵 Catalog")
    st.metric("Total songs", len(songs))
    st.metric("Genres", len(genre_counts))
    st.divider()

    st.markdown("**Songs per genre**")
    for genre, count in sorted(genre_counts.items()):
        bar_pct = int(count / max(genre_counts.values()) * 100)
        st.markdown(
            f"`{genre:<12}` "
            + "█" * (count // 1)
            + f"  **{count}**",
        )

    st.divider()
    st.markdown(
        "**How it works**\n\n"
        "1. Gemini parses your request\n"
        "2. Scoring engine retrieves matches\n"
        "3. Gemini explains why they fit"
    )

# ── Main area ─────────────────────────────────────────────────────────────────

st.title("🎵 AI Music Recommender")
st.markdown(
    "Ask for music in plain English. Gemini parses your intent, "
    f"the scoring engine finds the best matches from **{len(songs)} songs across {len(genre_counts)} genres**, "
    "and Gemini writes a personalized explanation grounded in the actual song data."
)
st.divider()

query = st.text_input(
    "What music do you want to hear?",
    placeholder="e.g.  chill lofi to study to  |  energetic Bollywood for a workout  |  sad indie folk",
    help="Be as specific or vague as you like — Gemini will extract the relevant musical attributes.",
)

col_btn, col_hint = st.columns([1, 4])
run = col_btn.button("Find Songs 🎶", type="primary", disabled=not query.strip())
col_hint.markdown(
    "<small style='color:gray'>Requires a valid GEMINI_API_KEY in your .env file.</small>",
    unsafe_allow_html=True,
)

# ── Results ───────────────────────────────────────────────────────────────────

if run and query.strip():

    # ── Step 1: Parse ─────────────────────────────────────────────────────────
    with st.spinner("Parsing your request with Gemini…"):
        try:
            user_prefs = parse_preferences(query.strip())
        except EnvironmentError as e:
            st.error(f"**Setup error:** {e}")
            st.stop()
        except (RuntimeError, ValueError) as e:
            st.error(f"**API / parse error:** {e}")
            st.stop()

    st.subheader("Parsed preferences")
    if user_prefs:
        pref_cols = st.columns(min(len(user_prefs), 7))
        for i, (key, val) in enumerate(user_prefs.items()):
            label = key.replace("_", " ").title()
            if isinstance(val, float):
                display = f"{val:.2f}"
            elif isinstance(val, int):
                display = str(val)
            else:
                display = str(val)
            pref_cols[i % len(pref_cols)].metric(label, display)
    else:
        st.warning("Gemini could not extract any structured preferences. Try rephrasing.")
        st.stop()

    # ── Step 2: Validate guardrails ───────────────────────────────────────────
    try:
        user_prefs = validate_user_prefs(user_prefs)
    except ValueError as e:
        st.warning(f"**Guardrail:** {e}  \nProceeding with valid fields only.")
        safe_keys = ["genre", "mood", "energy", "valence",
                     "tempo_bpm", "danceability", "acousticness"]
        user_prefs = {k: v for k, v in user_prefs.items() if k in safe_keys}

    st.divider()

    # ── Step 3: Retrieve recommendations ─────────────────────────────────────
    recommendations = recommend_songs(user_prefs, songs, k=5)

    st.subheader("Top 5 Recommendations")

    MOOD_EMOJIS = {
        "happy": "😄", "chill": "😌", "intense": "🔥", "dreamy": "✨",
        "melancholic": "😢", "energetic": "⚡", "peaceful": "🕊️",
        "romantic": "💖", "nostalgic": "🌅", "angry": "😤",
        "uplifting": "🚀", "focused": "🎯", "relaxed": "🛋️", "moody": "🌧️",
    }

    for rank, (song, score, explanation) in enumerate(recommendations, start=1):
        mood_emoji = MOOD_EMOJIS.get(song["mood"], "🎵")
        match_pct = int(score / 6.5 * 100)

        with st.container(border=True):
            # Header row
            head_col, score_col = st.columns([5, 1])
            head_col.markdown(
                f"### #{rank} &nbsp; {song['title']} &nbsp;—&nbsp; *{song['artist']}*"
            )
            score_col.metric(
                "Match score",
                f"{score:.2f} / 6.50",
                delta=f"{match_pct}%",
                delta_color="off",
            )

            # Genre / mood / tempo tags
            st.markdown(
                f"`{song['genre'].upper()}` &nbsp; "
                f"{mood_emoji} `{song['mood']}` &nbsp; "
                f"🎼 `{song['tempo_bpm']} BPM`"
            )

            attr_col, breakdown_col = st.columns(2)

            with attr_col:
                st.markdown("**Audio attributes**")
                for attr, label in [
                    ("energy",       "Energy"),
                    ("valence",      "Valence (positivity)"),
                    ("danceability", "Danceability"),
                    ("acousticness", "Acousticness"),
                ]:
                    val = song[attr]
                    st.progress(val, text=f"{label}: {val:.2f}")

            with breakdown_col:
                st.markdown("**Score breakdown**")
                for line in explanation.split("\n  "):
                    line = line.strip()
                    if line:
                        st.markdown(f"- {line}")
                st.divider()
                st.progress(score / 6.5, text=f"Overall match: {match_pct}%")

    st.divider()

    # ── Step 4: RAG re-score for List[str] reasons ────────────────────────────
    rag_data = []
    for song, score, _ in recommendations:
        _, reasons_list = score_song(user_prefs, song)
        rag_data.append((song, score, reasons_list))

    # ── Step 5: Generate grounded narrative ───────────────────────────────────
    with st.spinner("Generating AI DJ explanation…"):
        try:
            narrative = generate_rag_explanation(query.strip(), rag_data)
        except RuntimeError as e:
            st.warning(f"Could not generate AI explanation: {e}")
            st.stop()

    st.subheader("AI DJ Explanation")
    st.info(narrative)

    st.caption(
        f"Query: *\"{query.strip()}\"*  ·  "
        f"{len(songs)} songs in catalog  ·  "
        f"Powered by Gemini 3 Flash"
    )
