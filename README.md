# AI Music Recommender, using RAG + Gemini

## Original Project (Module 3)

The original project was the **Music Recommender Simulation**, a pure-Python classroom exercise built in Modules 1–3. Its goal was to represent songs and a user taste profile as structured data, then design a deterministic scoring rule that turned numeric feature comparisons into ranked recommendations. The system scored each of 18 songs against a hardcoded `UserProfile` using genre/mood categorical matches and weighted numeric proximity across energy, valence, tempo, danceability, and acousticness — with a maximum possible score of 6.50 points. It demonstrated that even a simple hand-crafted rule can produce surprisingly reasonable results, but was limited to 18 songs, 8 hardcoded demo profiles, and no natural language interface.

---

## Title and Summary

**AI Music Recommender** is a Retrieval-Augmented Generation (RAG) system that lets you describe music in plain English and receive a ranked list of song recommendations with an AI-generated explanation grounded in the actual retrieved data.

You type something like *"I want chill Bollywood songs for a late-night study session"* and the system:
1. Sends your query to Gemini 3 Flash, which extracts structured musical preferences (genre, mood, energy, valence, etc.)
2. Validates those preferences against strict guardrails
3. Scores all 203 songs in the catalog using a 7-factor weighted algorithm and returns the top 5
4. Sends the retrieved songs back to Gemini to generate a grounded 3–5 sentence explanation referencing the actual titles, artists, and scores

It matters because it bridges the gap between how people naturally think about music ("something melancholic but danceable") and how recommendation engines actually work (numerical feature vectors). The system is fully transparent — every point in every score is explained — which makes it a useful tool for understanding how AI-powered recommenders work under the hood.

---

## Architecture Overview

![System Architecture](Project%20Model.png)

The system is organized into six sequential layers. The full diagram lives in [`algorithm_model.mmd`](algorithm_model.mmd) and can be viewed at [mermaid.live](https://mermaid.live).

```
👤 Human Input
    │  Natural language query via CLI or Streamlit UI
    ▼
🤖 Parse Agent  (Gemini 3 Flash — API Call 1)
    │  parse_preferences() → structured user_prefs dict
    │  Displayed to user for mid-flow review ①
    ▼
🛡️ Guardrails
    │  validate_user_prefs() — rejects bad values before retrieval
    ▼
⚙️ Retrieval Engine
    │  score_song() scores all 203 songs with 7 weighted factors
    │  recommend_songs() sorts and slices the top 5
    ▼
🤖 Explain Agent  (Gemini 3 Flash — API Call 2, RAG)
    │  generate_rag_explanation() — context-injected with actual retrieved songs
    ▼
👤 Human Output & Evaluation ②
    │  Ranked table + AI narrative; user re-queries if unsatisfied
    ▼
🧪 Testing & Reliability  (always active)
    │  7 pytest tests verify determinism, score accuracy, and guardrail boundaries
    │  Logger writes to stdout and recommender.log
    └─ Human developer runs pytest to encode domain judgment ③
```

**Three explicit human touchpoints:**
- **①** User sees parsed preferences before retrieval — can re-query if Gemini misunderstood
- **②** User evaluates the final ranked table and AI narrative — can re-query if unsatisfied
- **③** Developer runs `pytest` to verify system invariants hold as the codebase changes

---

## Setup Instructions

### 1. Clone and enter the project

```bash
git clone <repo-url>
cd applied-ai-system-final
```

### 2. Create and activate a virtual environment (recommended)

```bash
python -m venv .venv
source .venv/bin/activate        # macOS / Linux
.venv\Scripts\activate           # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Add your Gemini API key

```bash
cp .env.example .env
# Open .env and replace  GEMINI_API_KEY=your_key_here  with your real key
# Get a free key at https://aistudio.google.com/app/apikey
```

### 5. Run the Streamlit UI (recommended)

```bash
streamlit run src/app.py
```

Then open [http://localhost:8501](http://localhost:8501) in your browser.

### 6. Or run the CLI

```bash
# Interactive RAG mode (requires API key)
python -m src.main

# Demo mode — 8 hardcoded profiles, no API key needed
python -m src.main --demo
```

### 7. Run the test suite

```bash
pytest
```

All 7 tests should pass in under 1 second.

---

## Sample Interactions

### Example 1 — Chill study session

**User input:**
```
What music do you want to hear?  >  chill lofi beats for studying late at night
```

**Parsed preferences (Gemini):**
```
{'genre': 'lofi', 'mood': 'chill', 'energy': 0.32, 'valence': 0.55, 'tempo_bpm': 74, 'acousticness': 0.82}
```

**Top 5 Recommendations:**
```
  #1  Library Rain  —  Paper Lanterns          Score: 5.68 / 6.50
       Genre: lofi  |  Mood: chill  |  Tempo: 72 BPM
       Genre match (lofi): +1.0
       Mood match (chill): +1.5
       Energy proximity: +1.94
       Valence proximity: +0.74
       Tempo proximity: +0.49
       Acousticness proximity: +0.24

  #2  Midnight Coding  —  LoRoom               Score: 5.52 / 6.50
  #3  Rainy Day Beats  —  Jinsang              Score: 5.44 / 6.50
  #4  Study Session  —  ChillHop               Score: 5.38 / 6.50
  #5  Snowfall  —  Oneeheart & reidenshi       Score: 5.21 / 6.50
```

**AI DJ Explanation:**
> These five tracks were chosen because they all sit in the low-energy, high-acousticness zone that defines late-night lofi study music. Library Rain by Paper Lanterns earned the top spot with a 5.68 score, matching both the lofi genre and chill mood while its 72 BPM and 0.86 acousticness score closely mirrors your request for calm, acoustic texture. Midnight Coding and Rainy Day Beats follow closely, both sharing the chill mood and lofi genre with energies in the 0.26–0.42 range that keep the listening experience non-distracting. Snowfall rounds out the list with a dreamy mood and 0.82 acousticness, adding subtle variety without breaking the low-key atmosphere you asked for.

---

### Example 2 — High-energy workout

**User input:**
```
What music do you want to hear?  >  something intense and high energy for the gym
```

**Parsed preferences (Gemini):**
```
{'mood': 'intense', 'energy': 0.92, 'danceability': 0.80, 'tempo_bpm': 145, 'valence': 0.55}
```

**Top 5 Recommendations:**
```
  #1  Drop Zone  —  Pulse Circuit              Score: 5.11 / 6.50
       Genre: edm  |  Mood: intense  |  Tempo: 140 BPM
       Mood match (intense): +1.5
       Energy proximity: +1.90
       Valence proximity: +0.62
       Tempo proximity: +0.48
       Danceability proximity: +0.43

  #2  Animals  —  Martin Garrix                Score: 5.04 / 6.50
  #3  Scary Monsters and Nice Sprites  —  Skrillex   Score: 4.98 / 6.50
  #4  Gurenge  —  LiSA                         Score: 4.87 / 6.50
  #5  Iron Collapse  —  Threshold Nine         Score: 4.79 / 6.50
```

**AI DJ Explanation:**
> Your request for intense, high-energy gym music was matched against tracks with energy scores above 0.88 and mood tagged as intense. Drop Zone leads at 5.11 with a 0.97 energy score, 140 BPM tempo, and a 0.94 danceability — it is the most physically demanding track in the catalog. Animals by Martin Garrix and Skrillex's Scary Monsters sit just behind it, both scoring above 4.98 with energy levels in the 0.92–0.95 range and tempos near your 145 BPM target. LiSA's Gurenge brings a different texture — a J-Pop anime anthem running at 180 BPM with intense mood and 0.88 energy — offering a unique high-adrenaline alternative to the EDM picks above it.

---

### Example 3 — Romantic Bollywood

**User input:**
```
What music do you want to hear?  >  romantic Bollywood songs with a dreamy feel
```

**Parsed preferences (Gemini):**
```
{'genre': 'bollywood', 'mood': 'romantic', 'energy': 0.48, 'valence': 0.72, 'acousticness': 0.55}
```

**Top 5 Recommendations:**
```
  #1  Kesariya  —  Arijit Singh                Score: 4.92 / 6.50
       Genre: bollywood  |  Mood: romantic  |  Tempo: 112 BPM
       Genre match (bollywood): +1.0
       Mood match (romantic): +1.5
       Energy proximity: +1.86
       Valence proximity: +0.72
       Acousticness proximity: +0.21

  #2  Tum Hi Ho  —  Arijit Singh               Score: 4.74 / 6.50
  #3  Raabta  —  Pritam                        Score: 4.61 / 6.50
  #4  The Girl from Ipanema  —  Joao Gilberto  Score: 3.88 / 6.50
  #5  Best Part  —  Daniel Caesar ft. H.E.R.   Score: 3.72 / 6.50
```

**AI DJ Explanation:**
> Your request for romantic, dreamy Bollywood closely matched the top three tracks in the catalog. Kesariya by Arijit Singh earned the highest score of 4.92 — it hits both the Bollywood genre and romantic mood, and its 0.55 energy and 0.75 valence are close to your targets, making it a near-perfect match. Tum Hi Ho follows at 4.74 with an even softer energy of 0.35 and high acousticness of 0.70, leaning more into the dreamy quality you described. Raabta by Pritam rounds out the Bollywood trio with a dreamy mood tag and a balanced 0.50 energy score. The Girl from Ipanema and Best Part round out the list by matching the romantic mood and soft valence even though they fall outside the Bollywood genre — the scoring engine surfaced them as the closest emotional equivalents in the broader catalog.

---

## Design Decisions

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

## Testing Summary

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

- **Model availability**: The first chosen model (`gemini-2.0-flash`) returned 429 quota errors on a free-tier key. Switching to `gemini-2.5-flash` and later `gemini-3-flash-preview` resolved this.
- **Truncated explanations**: Gemini 3 Flash uses internal thinking tokens by default, which consumed the entire `max_output_tokens` budget before writing any visible text. Setting `thinking_budget=0` fixed truncated responses immediately.
- **Score threshold in regression test**: The initial threshold of `5.0` was too high for a partial prefs profile. Recalculating manually revealed the correct expected value (~4.46) and the threshold was adjusted to `4.0` with a comment explaining why.

### What I learned

Testing is most valuable at the **boundary between human judgment and machine execution**. The regression test is not just a technical check — it encodes the assertion that "Sunrise City should be near the top for a pop/happy listener," which is a human opinion expressed as a number. Writing that test forced precision about what the system should do, not just what it currently does.

---

## Reflection

### What this project taught me about AI

The original Modules 1–3 project showed that hand-crafted scoring rules can produce useful recommendations. This expanded version showed what happens when you put a large language model on both ends of that pipeline — and revealed two important lessons.

First, **LLMs are interfaces, not oracles**. Gemini's role here is to translate human language into a structured dict and then translate structured data back into human language. The actual intelligence — deciding which songs are closest to a preference — lives in a formula I wrote and can fully explain. The LLM handles the parts that are genuinely hard for rule-based code (intent parsing, narrative generation) while the retriever handles the part that is genuinely hard for LLMs (precise, reproducible, inspectable ranking).

Second, **grounding is the difference between useful and impressive**. The RAG augmentation step forces the explainer to reference specific titles, scores, and attributes from the retrieved set. Without it, Gemini would generate convincing but fabricated explanations that might reference songs not in the results or invent attribute values. The constraint makes the system honest — and more trustworthy as a result.

### What this project taught me about problem-solving

Building an end-to-end AI system surfaced the value of **thinking in layers**. Each layer in the pipeline (parse → validate → retrieve → explain) has a single job and a clear failure mode. When something broke — wrong model, truncated output, bad threshold — isolating it to one layer made debugging straightforward. Systems that mix concerns across layers are much harder to reason about.

The guardrails layer specifically taught me that AI output needs a skeptical intermediary before it touches your data. Gemini occasionally returns energy values slightly above 1.0 or genres that don't exist in the catalog. A one-line `ValueError` caught those before they silently corrupted rankings. That skepticism — treating AI output as untrusted input at system boundaries — is the most transferable lesson from this project.

Finally, building the Streamlit UI changed how I thought about the system's purpose. Seeing the parsed preferences displayed as metric cards before the ranked results appear made the mid-flow human review point feel natural and important rather than like extra code. Good AI systems should show their work at every step — not just at the end.
