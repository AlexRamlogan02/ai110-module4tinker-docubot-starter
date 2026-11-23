# DocuBot

DocuBot is a small documentation assistant that helps answer developer questions about a codebase.  
It can operate in three different modes:

1. **Naive LLM mode**  
   Sends the question to a Gemini model without documentation context. Its
   answers may be general and are not grounded in the local docs.

2. **Retrieval only mode**  
   Uses a simple indexing and scoring system to retrieve relevant snippets without calling an LLM.

3. **RAG mode (Retrieval Augmented Generation)**  
   Retrieves relevant snippets, then asks Gemini to answer using only those snippets.

Retrieval normalizes words, removes common filler words, and ranks paragraphs
using query-word matches and headings. Retrieval-only mode returns the best
paragraph, while RAG receives up to three. A document must contain all
meaningful query words; a paragraph and its headings must match at least half
of them and at least two when the query has two or more. At least one word must
match the paragraph itself. If none qualify, the assistant says it does not
know.

These are lexical heuristics, not a guarantee that a passage answers the
question. They can also miss answers expressed using different words. For
example, retrieval missed the documented users-table fields for the sample
question about them; RAG shares this limitation.

The docs folder contains realistic developer documents (API reference, authentication notes, database notes), but these files are **just text**. They support retrieval experiments and do not require students to set up any backend systems.

---

## Setup

### 1. Install Python dependencies

    pip install -r requirements.txt

### 2. Configure environment variables

Copy the example file:

    cp .env.example .env

Then edit `.env` to include your Gemini API key:

    GEMINI_API_KEY=your_api_key_here

If you do not set a Gemini key, you can still run retrieval only mode.

---

## Running DocuBot

Start the program:

    python main.py

Choose a mode:

- **1**: Naive LLM (question only; no documentation context)
- **2**: Retrieval only (no LLM)  
- **3**: RAG (retrieval + Gemini)

You can use built in sample queries or type your own.

---

## Running Retrieval Evaluation (optional)

    python evaluation.py

This prints simple retrieval hit rates for sample queries.
The evaluation counts a hit when any expected filename is retrieved; queries
without an expected filename are counted as misses even if refusal is correct.

See [NOTES.md](NOTES.md) for observed responses and [model_card.md](model_card.md)
for the system's design, comparisons, and limitations.

---

## Modifying the Project

You will primarily work in:

- `docubot.py`  
  Implement or improve the retrieval index, scoring, and snippet selection.

- `llm_client.py`  
  Adjust the prompts and behavior of LLM responses.

- `dataset.py`  
  Add or change sample queries for testing.

---

## Requirements

- Python 3.9+
- A Gemini API key for LLM features (only needed for modes 1 and 3)
- No database, no server setup, no external services besides LLM calls
