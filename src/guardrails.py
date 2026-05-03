import logging
import sys
from typing import Dict

VALID_GENRES = {
    "pop", "lofi", "rock", "folk", "ambient", "jazz",
    "synthwave", "indie pop", "hip-hop", "edm",
    "classical", "r&b", "country", "metal", "funk",
    "bollywood", "latin", "soul", "blues", "reggae", "k-pop",
    "afrobeats", "bossa nova", "disco", "gospel", "neo-soul",
    "trap", "j-pop", "indie rock", "dancehall",
}

VALID_MOODS = {
    "happy", "chill", "intense", "dreamy", "melancholic",
    "energetic", "peaceful", "romantic", "nostalgic",
    "angry", "uplifting", "focused", "relaxed", "moody",
}

_FLOAT_FIELDS = ["energy", "valence", "danceability", "acousticness"]


def validate_user_prefs(prefs: Dict) -> Dict:
    """
    Validates a user preference dictionary and returns it unchanged if valid.

    Raises ValueError with a descriptive message for:
      - Float fields (energy, valence, danceability, acousticness) outside [0.0, 1.0]
      - tempo_bpm outside [40, 220]
      - genre not in VALID_GENRES (if provided)
      - mood not in VALID_MOODS (if provided)
    """
    for field in _FLOAT_FIELDS:
        if field in prefs:
            val = prefs[field]
            if not isinstance(val, (int, float)):
                raise ValueError(
                    f"'{field}' must be a number, got {type(val).__name__}"
                )
            if not 0.0 <= float(val) <= 1.0:
                raise ValueError(
                    f"'{field}' must be between 0.0 and 1.0, got {val}"
                )

    if "tempo_bpm" in prefs:
        val = prefs["tempo_bpm"]
        if not isinstance(val, (int, float)):
            raise ValueError(
                f"'tempo_bpm' must be a number, got {type(val).__name__}"
            )
        if not 40 <= float(val) <= 220:
            raise ValueError(
                f"'tempo_bpm' must be between 40 and 220, got {val}"
            )

    if "genre" in prefs and prefs["genre"] not in VALID_GENRES:
        raise ValueError(
            f"'genre' '{prefs['genre']}' is not in the catalog. "
            f"Valid genres: {sorted(VALID_GENRES)}"
        )

    if "mood" in prefs and prefs["mood"] not in VALID_MOODS:
        raise ValueError(
            f"'mood' '{prefs['mood']}' is not in the catalog. "
            f"Valid moods: {sorted(VALID_MOODS)}"
        )

    return prefs


def setup_logging(log_file: str = "recommender.log") -> logging.Logger:
    """
    Configures and returns a logger that writes to both stdout and a log file.
    """
    logger = logging.getLogger("music_recommender")
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(logging.INFO)
    stream_handler.setFormatter(fmt)

    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(fmt)

    logger.addHandler(stream_handler)
    logger.addHandler(file_handler)

    return logger
