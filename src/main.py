"""
Music Recommender — CLI entry point.

Usage:
  python -m src.main           # interactive RAG mode (requires GEMINI_API_KEY)
  python -m src.main --demo    # runs 8 hardcoded profiles (no API key needed)
"""

import argparse
import os
import sys

# Allow bare imports (e.g. `from recommender import ...`) when invoked via
# `python -m src.main` from the project root.
sys.path.insert(0, os.path.dirname(__file__))

from recommender import load_songs, recommend_songs, score_song
from guardrails import validate_user_prefs, setup_logging
from llm_client import parse_preferences, generate_rag_explanation


def _print_recommendations(recommendations):
    for rank, (song, score, explanation) in enumerate(recommendations, start=1):
        print(f"\n  #{rank}  {song['title']}  —  {song['artist']}")
        print(f"       Score : {score:.2f} / 6.50")
        print(f"       Genre : {song['genre']}  |  Mood : {song['mood']}")
        print("       " + "-" * 40)
        for reason in explanation.split("\n  "):
            print(f"       {reason}")


def run_demo_mode(songs, logger) -> None:
    profiles = [
        ("Pop Happy", {
            "genre": "pop", "mood": "happy",
            "energy": 0.80, "valence": 0.82, "tempo_bpm": 120,
            "danceability": 0.80, "acousticness": 0.20,
        }),
        ("Chill Lofi", {
            "genre": "lofi", "mood": "chill",
            "energy": 0.38, "valence": 0.58, "tempo_bpm": 76,
            "danceability": 0.60, "acousticness": 0.78,
        }),
        ("Deep Intense Rock", {
            "genre": "rock", "mood": "intense",
            "energy": 0.91, "valence": 0.45, "tempo_bpm": 150,
            "danceability": 0.65, "acousticness": 0.10,
        }),
        ("Slow and Melodic", {
            "genre": "folk", "mood": "dreamy",
            "energy": 0.30, "valence": 0.70, "tempo_bpm": 82,
            "danceability": 0.45, "acousticness": 0.90,
        }),
        ("High Energy Melancholic", {
            "genre": "hip-hop", "mood": "melancholic",
            "energy": 0.95, "valence": 0.25, "tempo_bpm": 140,
            "danceability": 0.90, "acousticness": 0.05,
        }),
        ("Genre Not in Catalog", {
            "mood": "uplifting",
            "energy": 0.65, "valence": 0.80, "tempo_bpm": 95,
            "danceability": 0.78, "acousticness": 0.45,
        }),
        ("Acoustic Banger", {
            "genre": "folk", "mood": "intense",
            "energy": 0.97, "valence": 0.60, "tempo_bpm": 155,
            "danceability": 0.70, "acousticness": 0.95,
        }),
        ("Perfectly Neutral", {
            "energy": 0.50, "valence": 0.50, "tempo_bpm": 110,
            "danceability": 0.50, "acousticness": 0.50,
        }),
    ]

    for profile_name, user_prefs in profiles:
        validate_user_prefs(user_prefs)
        recommendations = recommend_songs(user_prefs, songs, k=5)
        logger.info(
            f"Demo profile '{profile_name}' top results: "
            f"{[r[0]['title'] for r in recommendations]}"
        )

        print()
        print("=" * 54)
        print(f"  Profile : {profile_name}")
        print("=" * 54)
        _print_recommendations(recommendations)
        print()
        print("=" * 54)


def run_interactive_mode(songs, logger) -> None:
    query = input("\nDescribe the music you want to hear: ").strip()
    if not query:
        print("No query entered. Exiting.")
        return

    logger.info(f"User query: {query!r}")

    # Step 1 — Parse natural language → structured prefs (Gemini API call #1)
    print("\nParsing your request...")
    try:
        user_prefs = parse_preferences(query)
    except EnvironmentError as e:
        print(f"\nSetup error: {e}")
        return
    except RuntimeError as e:
        print(f"\nAPI error: {e}")
        return
    print(f"Interpreted as: {user_prefs}")

    # Step 2 — Validate (guardrails)
    try:
        user_prefs = validate_user_prefs(user_prefs)
    except ValueError as e:
        print(f"\nGuardrail warning: {e}")
        print("Proceeding with the valid fields only.")
        # Strip any key that caused the error and continue
        safe_keys = ["genre", "mood", "energy", "valence",
                     "tempo_bpm", "danceability", "acousticness"]
        user_prefs = {k: v for k, v in user_prefs.items() if k in safe_keys}

    # Step 3 — Retrieve top K songs (the RETRIEVAL step — pure Python, no API)
    recommendations = recommend_songs(user_prefs, songs, k=5)
    logger.info(
        f"Top results for {query!r}: "
        f"{[r[0]['title'] for r in recommendations]}, "
        f"scores={[r[1] for r in recommendations]}"
    )

    # Step 4 — Print scored table
    print()
    print("=" * 54)
    print("  Top 5 Recommendations")
    print("=" * 54)
    _print_recommendations(recommendations)
    print()
    print("=" * 54)

    # Step 5 — Re-score top 5 to get List[str] reasons for RAG augmentation
    rag_data = []
    for song, score, _ in recommendations:
        _, reasons_list = score_song(user_prefs, song)
        rag_data.append((song, score, reasons_list))

    # Step 6 — Generate grounded explanation (Gemini API call #2)
    print("\nGenerating AI explanation...")
    try:
        narrative = generate_rag_explanation(query, rag_data)
    except RuntimeError as e:
        print(f"\nAPI error during explanation: {e}")
        print("(Scored table above is still valid.)")
        return
    print()
    print("  AI DJ Explanation")
    print("  " + "-" * 40)
    print(f"  {narrative}")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Music Recommender — RAG-powered song recommendations"
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run 8 hardcoded demo profiles instead of interactive mode",
    )
    args = parser.parse_args()

    logger = setup_logging()
    songs = load_songs("data/songs.csv")
    logger.info(f"Loaded {len(songs)} songs from catalog")

    if args.demo:
        run_demo_mode(songs, logger)
    else:
        run_interactive_mode(songs, logger)


if __name__ == "__main__":
    main()
