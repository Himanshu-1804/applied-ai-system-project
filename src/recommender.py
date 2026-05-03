from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

@dataclass
class Song:
    """
    Represents a song and its attributes.
    Required by tests/test_recommender.py
    """
    id: int
    title: str
    artist: str
    genre: str
    mood: str
    energy: float
    tempo_bpm: float
    valence: float
    danceability: float
    acousticness: float

@dataclass
class UserProfile:
    """
    Represents a user's taste preferences.
    Required by tests/test_recommender.py
    """
    favorite_genre: str
    favorite_mood: str
    target_energy: float
    likes_acoustic: bool

def _song_to_dict(song: Song) -> Dict:
    return {
        "id": song.id, "title": song.title, "artist": song.artist,
        "genre": song.genre, "mood": song.mood, "energy": song.energy,
        "tempo_bpm": song.tempo_bpm, "valence": song.valence,
        "danceability": song.danceability, "acousticness": song.acousticness,
    }


def _profile_to_prefs(user: UserProfile) -> Dict:
    return {
        "genre": user.favorite_genre,
        "mood": user.favorite_mood,
        "energy": user.target_energy,
        "acousticness": 0.85 if user.likes_acoustic else 0.15,
    }


class Recommender:
    """
    OOP implementation of the recommendation logic.
    Required by tests/test_recommender.py
    """
    def __init__(self, songs: List[Song]):
        self.songs = songs

    def recommend(self, user: UserProfile, k: int = 5) -> List[Song]:
        prefs = _profile_to_prefs(user)
        scored = [
            (song, score_song(prefs, _song_to_dict(song))[0])
            for song in self.songs
        ]
        scored.sort(key=lambda x: x[1], reverse=True)
        return [song for song, _ in scored[:k]]

    def explain_recommendation(self, user: UserProfile, song: Song) -> str:
        score, reasons = score_song(_profile_to_prefs(user), _song_to_dict(song))
        return (
            f'Why "{song.title}" was recommended:\n'
            + "\n".join(f"  {r}" for r in reasons)
            + f"\n  Total score: {score:.2f} / 6.50"
        )

def load_songs(csv_path: str) -> List[Dict]:
    """
    Loads songs from a CSV file and returns them as a list of dictionaries.

    Accepts a relative or absolute path. Relative paths are resolved against
    the project root (one level above this file's src/ directory), so callers
    can pass 'data/songs.csv' regardless of the current working directory.

    Each dictionary contains the following keys:
        id (int), title (str), artist (str), genre (str), mood (str),
        energy (float), tempo_bpm (int), valence (float),
        danceability (float), acousticness (float)

    Args:
        csv_path: Path to the CSV file, relative to the project root or absolute.

    Returns:
        A list of song dictionaries with numeric fields cast to int or float.

    Raises:
        FileNotFoundError: If no file exists at the resolved path.
    """
    import csv
    from pathlib import Path

    path = Path(csv_path)
    if not path.is_absolute():
        path = Path(__file__).parent.parent / csv_path

    songs = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            songs.append({
                "id":           int(row["id"]),
                "title":        row["title"],
                "artist":       row["artist"],
                "genre":        row["genre"],
                "mood":         row["mood"],
                "energy":       float(row["energy"]),
                "tempo_bpm":    int(row["tempo_bpm"]),
                "valence":      float(row["valence"]),
                "danceability": float(row["danceability"]),
                "acousticness": float(row["acousticness"]),
            })
    return songs

def score_song(user_prefs: Dict, song: Dict) -> Tuple[float, List[str]]:
    """
    Scores a single song against a user preference profile.

    Applies a two-part scoring algorithm:

    Categorical matches (exact):
        genre match  → +1.0 points
        mood match   → +1.5 points

    Numeric proximity (weighted, each clamped to [0, 1]):
        energy       → weight 2.00  (highest priority)
        valence      → weight 0.75
        tempo_bpm    → weight 0.50  (normalized over a 100 BPM window)
        danceability → weight 0.50
        acousticness → weight 0.25  (lowest priority)

    Maximum possible score is 6.5. Numeric features are only scored when
    the corresponding key is present in user_prefs, so partial profiles
    (e.g. only genre, mood, and energy) are handled gracefully.

    Args:
        user_prefs: Dictionary of user preference values. Supported keys:
                    'genre', 'mood', 'energy', 'valence', 'tempo_bpm',
                    'danceability', 'acousticness'. Missing keys are skipped.
        song:       Dictionary representing a single song, as returned by
                    load_songs().

    Returns:
        A tuple of (score, reasons) where score is the total float score
        rounded to 2 decimal places, and reasons is a list of human-readable
        strings explaining each point contribution.
    """
    score = 0.0
    reasons = []

    # --- Categorical matches ---
    if user_prefs.get("genre") and song["genre"] == user_prefs["genre"]:
        score += 1.0
        reasons.append(f"Genre match ({song['genre']}): +1.0")

    if user_prefs.get("mood") and song["mood"] == user_prefs["mood"]:
        score += 1.5
        reasons.append(f"Mood match ({song['mood']}): +1.5")

    # --- Numeric proximity scores ---
    # Formula: points = weight * clamp(1 - abs(user_target - song_value), 0, 1)
    # All proximity values are explicitly clamped to [0, 1] so scores are
    # always non-negative and the maximum possible total score is 6.5.
    # BPM is first normalized over a 100 BPM window, then clamped.

    if "energy" in user_prefs:
        proximity = max(0.0, min(1.0, 1.0 - abs(user_prefs["energy"] - song["energy"])))
        points = round(proximity * 2.00, 2)
        score += points
        reasons.append(f"Energy proximity: +{points:.2f}")

    if "valence" in user_prefs:
        proximity = max(0.0, min(1.0, 1.0 - abs(user_prefs["valence"] - song["valence"])))
        points = round(proximity * 0.75, 2)
        score += points
        reasons.append(f"Valence proximity: +{points:.2f}")

    if "tempo_bpm" in user_prefs:
        proximity = max(0.0, min(1.0, 1.0 - abs(user_prefs["tempo_bpm"] - song["tempo_bpm"]) / 100.0))
        points = round(proximity * 0.50, 2)
        score += points
        reasons.append(f"Tempo proximity: +{points:.2f}")

    if "danceability" in user_prefs:
        proximity = max(0.0, min(1.0, 1.0 - abs(user_prefs["danceability"] - song["danceability"])))
        points = round(proximity * 0.50, 2)
        score += points
        reasons.append(f"Danceability proximity: +{points:.2f}")

    if "acousticness" in user_prefs:
        proximity = max(0.0, min(1.0, 1.0 - abs(user_prefs["acousticness"] - song["acousticness"])))
        points = round(proximity * 0.25, 2)
        score += points
        reasons.append(f"Acousticness proximity: +{points:.2f}")

    return round(score, 2), reasons

def recommend_songs(user_prefs: Dict, songs: List[Dict], k: int = 5) -> List[Tuple[Dict, float, str]]:
    """
    Scores every song in the catalog and returns the top k recommendations.

    Iterates over all songs, calls score_song() on each one to obtain a
    numeric score and explanation, then sorts the full list by score
    descending and slices the top k results.

    Args:
        user_prefs: Dictionary of user preference values passed directly
                    to score_song(). See score_song() for supported keys.
        songs:      Full list of song dictionaries, as returned by load_songs().
        k:          Number of top recommendations to return. Defaults to 5.

    Returns:
        A list of up to k tuples, each containing:
            (song dict, score float, explanation str)
        Sorted from highest score to lowest.
    """
    scored = [
        (song, score, "\n  ".join(reasons))
        for song in songs
        for score, reasons in [score_song(user_prefs, song)]
    ]
    return sorted(scored, key=lambda x: x[1], reverse=True)[:k]
