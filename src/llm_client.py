import json
import logging
import os
from typing import Dict, List, Tuple

from google import genai
from google.genai import types
from google.genai.errors import ClientError
from dotenv import load_dotenv

logger = logging.getLogger("music_recommender")

_MODEL = "gemini-2.5-flash"

_PARSE_SYSTEM = """\
You are a music preference parser. Your only job is to convert a natural \
language music request into a structured JSON object.

Valid genres: pop, lofi, rock, folk, ambient, jazz, synthwave, indie pop, \
hip-hop, edm, classical, r&b, country, metal, funk

Valid moods: happy, chill, intense, dreamy, melancholic, energetic, peaceful, \
romantic, nostalgic, angry, uplifting, focused, relaxed, moody

Return ONLY a JSON object with any of these keys that you can confidently \
infer from the request:
{
  "genre": "<one of the valid genres above, or omit if unclear>",
  "mood": "<one of the valid moods above, or omit if unclear>",
  "energy": <float 0.0-1.0, where 0=very calm, 1=very high energy>,
  "valence": <float 0.0-1.0, where 0=sad/negative, 1=joyful/positive>,
  "tempo_bpm": <integer 40-220>,
  "danceability": <float 0.0-1.0>,
  "acousticness": <float 0.0-1.0, where 0=electronic, 1=fully acoustic>
}

Omit any key you are not confident about. Do not include explanation, \
markdown, or extra text. Return only the JSON object.\
"""

_EXPLAIN_SYSTEM = """\
You are a music DJ assistant. Explain why specific songs from a catalog were \
recommended to a user. Ground every claim in the actual song data provided — \
reference specific titles, artists, genres, moods, energy levels, or scores. \
Do not give generic music advice and do not mention songs not in the list.\
"""


def _get_client() -> genai.Client:
    load_dotenv()
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "GEMINI_API_KEY not set. "
            "Copy .env.example to .env and add your key."
        )
    return genai.Client(api_key=api_key)


def parse_preferences(query: str) -> Dict:
    """
    Uses Gemini to parse a natural language music query into a structured
    user_prefs dict using only genres and moods present in the catalog.

    Raises ValueError if the API response is not valid JSON.
    """
    client = _get_client()
    logger.debug(f"Parsing preferences for query: {query!r}")

    try:
        response = client.models.generate_content(
            model=_MODEL,
            contents=query,
            config=types.GenerateContentConfig(
                system_instruction=_PARSE_SYSTEM,
                max_output_tokens=300,
                thinking_config=types.ThinkingConfig(thinking_budget=0),
            ),
        )
    except ClientError as e:
        if e.code == 429:
            raise RuntimeError(
                "Gemini API quota exceeded. "
                "Wait a moment and try again, or check your usage at "
                "https://ai.dev/rate-limit"
            ) from e
        raise RuntimeError(f"Gemini API error: {e}") from e

    raw = response.text.strip()
    logger.debug(f"Raw parse response: {raw}")

    # Gemini sometimes wraps JSON in markdown code fences — strip them
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    try:
        prefs = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"Gemini returned non-JSON response: {raw!r}"
        ) from e

    logger.info(f"Parsed preferences: {prefs}")
    return prefs


def generate_rag_explanation(
    query: str,
    recommendations: List[Tuple[Dict, float, List[str]]],
) -> str:
    """
    Uses Gemini to generate a grounded natural language explanation of the
    top recommendations.

    The prompt includes each retrieved song's title, artist, genre, mood,
    energy, score, and score breakdown so Gemini's response is anchored to
    actual catalog data rather than generic music knowledge.

    Args:
        query:           The original natural language query from the user.
        recommendations: List of (song_dict, score_float, reasons_list) tuples.
    """
    client = _get_client()

    songs_block = ""
    for i, (song, score, reasons) in enumerate(recommendations, 1):
        breakdown = "\n      ".join(reasons)
        songs_block += (
            f"\n#{i}. \"{song['title']}\" by {song['artist']}"
            f"\n   Genre: {song['genre']} | Mood: {song['mood']}"
            f"\n   Energy: {song['energy']} | Valence: {song['valence']}"
            f"\n   Tempo: {song['tempo_bpm']} BPM"
            f"\n   Score: {score:.2f} / 6.50"
            f"\n   Breakdown:\n      {breakdown}\n"
        )

    user_message = (
        f'A user asked for: "{query}"\n\n'
        f"Here are the top {len(recommendations)} songs retrieved from the "
        f"catalog, ranked by compatibility score:\n"
        f"{songs_block}\n"
        f"Write a 3-5 sentence explanation of why these songs match what the "
        f"user asked for. Reference specific song titles, artists, and "
        f"attributes from the data above."
    )

    logger.debug(f"Generating RAG explanation for query: {query!r}")

    try:
        response = client.models.generate_content(
            model=_MODEL,
            contents=user_message,
            config=types.GenerateContentConfig(
                system_instruction=_EXPLAIN_SYSTEM,
                max_output_tokens=400,
                thinking_config=types.ThinkingConfig(thinking_budget=0),
            ),
        )
    except ClientError as e:
        if e.code == 429:
            raise RuntimeError(
                "Gemini API quota exceeded while generating explanation. "
                "Wait a moment and try again."
            ) from e
        raise RuntimeError(f"Gemini API error: {e}") from e

    narrative = response.text.strip()
    logger.info(f"RAG explanation generated ({len(narrative)} chars)")
    return narrative
