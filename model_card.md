# 🎧 Model Card: AI Music Recommender (RAG + Gemini)

## 1. Model Name

**AI Music Recommender v2.0** — a Retrieval-Augmented Generation (RAG) system combining a deterministic scoring engine with Google Gemini 3 Flash for natural language understanding and explanation.

---

## 2. Intended Use

- This system lets users describe what music they want in plain English and returns a ranked list of song recommendations with an AI-generated explanation
- It is designed for educational use as a demonstration of RAG architecture and human-in-the-loop AI design
- It is not intended for production deployment, commercial music services, or recommendations at scale
- It should not be used to make decisions about music promotion, artist visibility, or playlist curation for real audiences

---

## 3. How the Model Works

The system makes exactly two calls to Google Gemini 3 Flash:

**Call 1 — Parse Agent:**
- The user's natural language query is sent to Gemini, which extracts a structured preference dict (genre, mood, energy, valence, tempo_bpm, danceability, acousticness)
- The parsed preferences are shown to the user before retrieval so they can catch and correct misinterpretations

**Guardrails (between the two calls):**
- `validate_user_prefs()` checks every field against strict boundaries (e.g. energy must be 0.0–1.0, genre must be in the known catalog)
- Invalid fields are stripped and a warning is shown; the system halts cleanly rather than passing malformed data to the retriever

**Retrieval Engine (no LLM):**
- `score_song()` scores all 203 songs using a 7-factor weighted formula:
  - Genre match: +1.0 (exact match only)
  - Mood match: +1.5 (exact match only)
  - Energy proximity: up to +2.0 (largest weight)
  - Valence proximity: up to +1.0
  - Tempo proximity: up to +0.5
  - Danceability proximity: up to +0.25
  - Acousticness proximity: up to +0.25
- Maximum possible score: 6.50 points
- `recommend_songs()` sorts all 203 songs by score and returns the top 5

**Call 2 — Explain Agent (RAG):**
- The top 5 retrieved songs (titles, artists, scores, and attributes) are injected into the prompt as context
- Gemini generates a 3–5 sentence explanation grounded in the actual retrieved results
- `thinking_budget=0` is set to prevent internal reasoning tokens from consuming the output budget

**Three explicit human touchpoints:**
- **①** User sees parsed preferences before retrieval — can re-query if Gemini misunderstood
- **②** User evaluates the final ranked table and AI narrative — can re-query if unsatisfied
- **③** Developer runs `pytest` to verify system invariants hold as the codebase changes

---

## 4. Data

- The catalog contains 203 songs spanning multiple genres (lofi, pop, bollywood, edm, jazz, classical, hip-hop, and more) and moods (chill, happy, intense, romantic, dreamy, melancholic, and more)
- Each song has 7 numeric and categorical features: genre, mood, energy (0–1), valence (0–1), tempo_bpm, danceability (0–1), acousticness (0–1)
- The catalog does not capture lyrics, language, cultural context, artist popularity, release date, or streaming data
- No user feedback or behavioral data is collected or used; the system has no memory between sessions
- The dataset was expanded from the original 18-song Module 3 catalog using AI-assisted generation; all AI-generated entries were manually reviewed for consistency with the feature schema

---

## 5. Strengths

- Every point in every score has a labeled reason — the system is fully inspectable and explainable
- The two-call LLM architecture cleanly separates intent parsing from retrieval, making each stage independently testable
- Guardrails prevent malformed LLM output from silently corrupting rankings
- The mid-flow preference display gives users a concrete review point to catch Gemini misinterpretations before retrieval runs
- `thinking_budget=0` eliminates token waste and prevents truncated explanations on the free-tier API
- 7 pytest tests verify determinism, score accuracy, and guardrail boundaries — the system's behavior is encoded as executable assertions
- RAG grounding forces the explanation to reference real retrieved titles, scores, and attributes — the system cannot hallucinate songs that weren't returned

---

## 6. Limitations and Bias

1. **Energy dominance:** The energy weight (2.0) is 4× larger than valence and 8× larger than danceability or acousticness. A 0.50 energy mismatch fully cancels the genre bonus, creating an inescapable filter bubble for users with unusual energy preferences.

2. **Sparse genre and mood coverage:** While the catalog has 203 songs, some genres and moods remain underrepresented. When the closest matching song on genre or mood scores poorly on energy, the categorical bonuses effectively vanish.

3. **No artist diversity:** The same artist can appear multiple times in the top 5 if they have several songs close to the user's preference vector, making results feel repetitive.

4. **Fixed weights:** The 7-factor formula uses hand-chosen weights that do not adapt to user feedback, cultural context, or listening history. What feels "correct" for one user population may be wrong for another.

5. **English-only parsing:** Gemini's intent extraction works best for English queries. Queries in other languages or with highly regional music terminology may be misparsed or produce empty preference dicts.

6. **LLM hallucination risk in explanations:** Although RAG grounds the explanation in retrieved song data, Gemini may occasionally misstate a score or attribute. The explanation is informational, not authoritative — the ranked table is the ground truth.

---

## 7. Design Decisions

### RAG over fine-tuning
The explainer uses Retrieval-Augmented Generation rather than a fine-tuned model because the explanation must be grounded in real-time retrieval results. A fine-tuned model would generate plausible-sounding but hallucinated song descriptions; RAG forces every claim to reference a title, score, or attribute that was actually retrieved in this session.

### Deterministic retrieval, not semantic search
The retriever (`score_song`) uses a hand-crafted weighted formula rather than embedding-based similarity. This makes the system fully inspectable — every point in every score has a labeled reason — and avoids embedding infrastructure cost. The trade-off is that the weights are fixed and do not learn from user feedback.

### Two-call LLM architecture
The system makes exactly two Gemini API calls: one to parse intent and one to explain results. Parsing is kept separate from retrieval so that structured validation (guardrails) can sit between them. If the parse call fails, the system halts cleanly before touching the catalog.

### `thinking_budget=0` on Gemini 3 Flash
Gemini 3 Flash allocates a token budget for internal reasoning ("thinking tokens") by default. For both tasks in this system — JSON extraction and short-form narrative — thinking is unnecessary overhead that consumes output tokens and can cause `MAX_TOKENS` truncation before the visible response is complete. Setting `thinking_budget=0` eliminates this without affecting output quality.

### Guardrails as a hard gate
`validate_user_prefs()` runs before any catalog access. This prevents malformed LLM output (e.g. `energy: 1.8` or an unrecognized genre) from reaching the scoring engine, which would silently produce meaningless rankings. Invalid fields are stripped and a warning is surfaced to the user rather than crashing.

### Streamlit as the primary interface
The Streamlit UI was added to make the full RAG pipeline accessible without the terminal. All parsed preferences are shown as metric cards before retrieval runs, giving the user a clear mid-flow review point to catch and correct misinterpretations.

### Trade-offs made

| Decision | Upside | Cost |
|---|---|---|
| Deterministic scoring | Fully explainable, zero inference cost | Weights don't adapt to feedback |
| Fixed 7-factor formula | Predictable, testable | Ignores lyrics, language, popularity |
| Two separate Gemini calls | Clean separation, easier to test | Two round-trip latencies per query |
| `thinking_budget=0` | No token waste, faster responses | Loses step-by-step reasoning on hard queries |

---

## 8. Evaluation

### What the test suite covers

| Test | What it verifies |
|---|---|
| `test_consistency_same_input_same_output` | Running the retriever 3× on identical prefs produces identical ranked ID lists — no hidden randomness |
| `test_score_regression_pop_happy_high_energy` | Sunrise City scores ≥ 4.0 against a pop/happy/energy=0.80 profile — catches silent formula regressions |
| `test_validate_rejects_energy_out_of_range` | `energy: 1.5` raises `ValueError` — guardrail boundary is enforced |
| `test_validate_rejects_valence_out_of_range` | `valence: -0.1` raises `ValueError` — negative values are caught |
| `test_validate_accepts_valid_prefs` | A well-formed dict is returned unchanged — guardrails don't over-reject |
| `test_recommender_returns_k_results` | OOP `Recommender.recommend()` returns exactly `k` results for any k |
| `test_recommender_ranks_by_score` | The first result always outscores the second — sort order is correct |

### What worked

The consistency and regression tests caught two real bugs during development. The regression threshold was initially set at `5.0`, which failed because the actual score for Sunrise City against a partial prefs dict (missing valence, danceability, etc.) is ~4.46 — the test itself forced a careful re-read of the scoring formula. The guardrail tests also caught an early version of the validator that used `status_code` instead of `code` on the Gemini `ClientError`, surfacing the API error rather than swallowing it.

### What didn't work initially

- **Model availability:** The first chosen model (`gemini-2.0-flash`) returned 429 quota errors on a free-tier key. Switching to `gemini-2.5-flash` and later `gemini-3-flash-preview` resolved this.
- **Truncated explanations:** Gemini 3 Flash uses internal thinking tokens by default, which consumed the entire `max_output_tokens` budget before writing any visible text. Setting `thinking_budget=0` fixed truncated responses immediately.
- **Score threshold in regression test:** The initial threshold of `5.0` was too high for a partial prefs profile. Recalculating manually revealed the correct expected value (~4.46) and the threshold was adjusted to `4.0`.

### What I learned

Testing is most valuable at the **boundary between human judgment and machine execution**. The regression test is not just a technical check — it encodes the assertion that "Sunrise City should be near the top for a pop/happy listener," which is a human opinion expressed as a number. Writing that test forced precision about what the system should do, not just what it currently does.

---

## 9. Future Work

- Add artist diversity enforcement so no single artist appears more than once in the top 5
- Replace fixed weights with a learned ranking model trained on user feedback
- Expand catalog coverage to ensure every genre and mood has at least 5–10 representative songs
- Fix BPM normalization to use the actual range of the catalog instead of a fixed window
- Support multilingual queries by detecting the input language and adjusting the parse prompt accordingly
- Add a voice-based AI DJ layer that reads the explanation aloud — giving the recommendation system an audio interface and a genuine "voice"
- Integrate real-time catalog data from a public music API (e.g. Spotify Web API) to replace the static CSV, drawing on their official documentation for which song features matter most

---

## 10. Personal Reflection

### What this project taught me about AI

The original Modules 1–3 project showed that hand-crafted scoring rules can produce useful recommendations. This expanded version showed what happens when you put a large language model on both ends of that pipeline — and revealed two important lessons.

First, **LLMs are interfaces, not oracles.** Gemini's role here is to translate human language into a structured dict and then translate structured data back into human language. The actual intelligence — deciding which songs are closest to a preference — lives in a formula I wrote and can fully explain. The LLM handles the parts that are genuinely hard for rule-based code (intent parsing, narrative generation) while the retriever handles the part that is genuinely hard for LLMs (precise, reproducible, inspectable ranking).

Second, **grounding is the difference between useful and impressive.** The RAG augmentation step forces the explainer to reference specific titles, scores, and attributes from the retrieved set. Without it, Gemini would generate convincing but fabricated explanations that might reference songs not in the results or invent attribute values. The constraint makes the system honest — and more trustworthy as a result.

### What this project taught me about problem-solving

Building an end-to-end AI system surfaced the value of **thinking in layers.** Each layer in the pipeline (parse → validate → retrieve → explain) has a single job and a clear failure mode. When something broke — wrong model, truncated output, bad threshold — isolating it to one layer made debugging straightforward. Systems that mix concerns across layers are much harder to reason about.

The guardrails layer specifically taught me that AI output needs a skeptical intermediary before it touches your data. Gemini occasionally returns energy values slightly above 1.0 or genres that don't exist in the catalog. A one-line `ValueError` caught those before they silently corrupted rankings. That skepticism — treating AI output as untrusted input at system boundaries — is the most transferable lesson from this project.

Finally, building the Streamlit UI changed how I thought about the system's purpose. Seeing the parsed preferences displayed as metric cards before the ranked results appear made the mid-flow human review point feel natural and important rather than like extra code. Good AI systems should show their work at every step — not just at the end.

### Personal takeaways

My biggest learning moment was understanding the mathematics behind the recommendation system. I am an avid math geek and building this showed me how the weighted proximity formulas I had always seen in textbooks are actually implemented in large-scale recommenders. The biggest surprise was how much a single weight change — doubling the energy factor — shifted almost every ranking across all profiles.

Using AI tools throughout this project helped significantly. I was able to brainstorm system design, identify weaknesses in the scoring formula, and expand the song catalog. Some instances where I had to double-check AI's work were developing specific user preference profiles — initially the generated profiles were too vague, and I had to provide my own preferences as an example to improve the output quality.

It made me realize that real apps like Spotify probably have hundreds of these weights, all carefully tuned behind the scenes using massive amounts of behavioral data. If I were to extend this project further, I would make the recommendation engine more robust by researching the official documentation from platforms like Spotify and Apple Music to understand which song characteristics matter most — and ultimately build an enhanced AI DJ with a synthesized voice, giving the recommendation system a literal voice of its own.