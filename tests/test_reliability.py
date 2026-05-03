import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.recommender import load_songs, recommend_songs, score_song
from src.guardrails import validate_user_prefs


def test_consistency_same_input_same_output():
    songs = load_songs("data/songs.csv")
    prefs = {"genre": "pop", "mood": "happy", "energy": 0.82, "valence": 0.84}

    run1 = [r[0]["id"] for r in recommend_songs(prefs, songs, k=5)]
    run2 = [r[0]["id"] for r in recommend_songs(prefs, songs, k=5)]
    run3 = [r[0]["id"] for r in recommend_songs(prefs, songs, k=5)]

    assert run1 == run2 == run3


def test_score_regression_pop_happy_high_energy():
    songs = load_songs("data/songs.csv")
    sunrise = next(s for s in songs if s["title"] == "Sunrise City")
    prefs = {"genre": "pop", "mood": "happy", "energy": 0.80}

    score, _ = score_song(prefs, sunrise)

    # genre +1.0, mood +1.5, energy proximity 0.98 × 2.00 = 1.96 → total ~4.46
    assert score >= 4.0, f"Expected Sunrise City to score >= 4.0, got {score}"


def test_validate_rejects_energy_out_of_range():
    with pytest.raises(ValueError, match="energy"):
        validate_user_prefs({"energy": 1.5})


def test_validate_rejects_valence_out_of_range():
    with pytest.raises(ValueError, match="valence"):
        validate_user_prefs({"valence": -0.1})


def test_validate_accepts_valid_prefs():
    prefs = {"genre": "pop", "energy": 0.8, "tempo_bpm": 120}
    result = validate_user_prefs(prefs)
    assert result == prefs
