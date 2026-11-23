# DocuBot Model Card

## 1. System Overview

DocuBot helps developers explore a small collection of documentation and
compare ungrounded generation, retrieval, and retrieval-augmented generation
(RAG). The documents describe a sample application; they are not themselves a
running backend.

Inputs are a question, Markdown or text files in the docs folder, and, for LLM
modes, a Gemini API key. Outputs are generated answers, retrieved passages with
filenames, or a refusal when retrieval finds no qualifying passage.

## 2. Retrieval Design

DocuBot builds an inverted index from normalized words to filenames. It
lowercases words, removes common filler words, splits identifier components,
and applies simple suffix normalization. Candidate documents must contain all
meaningful query words.

Documents are split into paragraphs. A paragraph and its headings must match
at least half the query words and at least two when the query has two or more;
at least one word must match the paragraph itself. Results are ranked by
overlap, heading matches, and word specificity. Retrieval-only mode returns
one paragraph by default; RAG uses up to three.

This design is simple and requires no embedding model, but lexical matching
can miss synonyms or select text that shares words without answering the
question.

## 3. Use of the LLM (Gemini)

- **Naive mode:** Calls Gemini with the question only. Despite the mode name,
  the current implementation ignores the supplied documentation text.
- **Retrieval only:** Returns a source paragraph without calling Gemini.
- **RAG:** Retrieves passages and calls Gemini only if there are matches.
  The prompt asks it to use only those passages, refuse when evidence is
  insufficient, and mention source files.

The configured model is `gemini-3.1-flash-lite`. Prompt instructions and
citations improve traceability but do not guarantee a correct answer.

## 4. Experiments and Comparisons

The following observations are from [NOTES.md](NOTES.md). Not every question
was tested in every mode; differently worded questions are identified.

| Question | Naive mode | Retrieval only | RAG |
|---|---|---|---|
| Where is the auth token generated? | Asked for context and gave general advice; missed the documented function. | Returned the token-generation paragraph from `AUTH.md`. | Named `generate_access_token` in `auth_utils.py` and cited `AUTH.md`. |
| Where can I pay for groceries? | Not tested. | Said it did not know. | Not tested with this exact wording; "Where can I buy groceries?" received the same refusal. |
| Where is the logic for payment processing? | Not tested. | Not tested. | Said it did not know. |
| Which fields are stored in the users table? | Not tested. | Retrieval found no qualifying passage in the sample evaluation. | Not tested; the same retrieval result would cause a refusal before the model is called. |

Naive mode sounded helpful but was not grounded in the docs. Retrieval-only
returned direct evidence, while RAG produced a more concise answer with a
source for the auth question. These examples do not establish that RAG is
always correct.

## 5. Failure Cases and Guardrails

- **Auth token, naive mode:** The answer suggested generic places to search
  rather than the documented function. A grounded answer should identify
  `generate_access_token` in `auth_utils.py`.
- **Users-table fields, retrieval:** The sample evaluation found no passage,
  even though the database guide lists the fields. It should retrieve the
  relevant table; RAG inherits the same failure.

The assistant should refuse when the docs contain no relevant information,
such as the grocery or payment questions, or when retrieved passages do not
provide enough evidence. Retrieval applies matching thresholds and limits the
number of passages; RAG also instructs the model to refuse unsupported answers.
These guardrails are heuristic and can both reject valid answers and allow
irrelevant passages through.

## 6. Limitations and Future Improvements

**Limitations**

1. Naive mode does not include documentation in its prompt.
2. Exact-ish word matching can miss relevant passages with different wording.
3. RAG depends on retrieved evidence and can still misinterpret it or generate
   unsupported claims.
4. The evaluation checks filenames, not answer correctness, and counts
   questions without expected filenames as misses.

**Future improvements**

1. Improve retrieval for synonyms and structured content such as tables.
2. Evaluate answer quality and correct refusals, not just retrieved filenames.
3. Compare the same questions across all modes, including more failure cases.

## 7. Responsible Use

Incorrect or unsupported guidance about authentication, configuration, or
data handling could lead developers to make unsafe changes. Sample documents
may also differ from the actual application being examined.

- Verify answers and citations against the original documentation and code.
- Treat refusals as uncertainty, not proof that information does not exist.
- Do not rely on generated guidance alone for security-sensitive decisions.
