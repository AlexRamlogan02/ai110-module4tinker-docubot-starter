"""
Core DocuBot class responsible for:
- Loading documents from the docs/ folder
- Building a simple retrieval index (Phase 1)
- Retrieving relevant snippets (Phase 1)
- Supporting retrieval only answers
- Supporting RAG answers when paired with Gemini (Phase 2)
"""

import os
import glob
import re


_STOP_WORDS = {
    "a", "all", "an", "and", "any", "are", "as", "at", "be", "by", "can", "do",
    "docs", "does", "for", "from", "how", "i", "in", "is", "it", "mention", "of",
    "on", "or", "that", "the", "these", "there", "this", "to", "what",
    "when", "where", "which", "who", "with",
}


def _words(text):
    words = set()
    for word in re.findall(r"[^\W_]+", text.lower()):
        if word in _STOP_WORDS:
            continue
        if len(word) > 5 and word.endswith(("ing", "ion")):
            word = word[:-3]
        elif len(word) > 4 and word.endswith("ed"):
            word = word[:-2]
        elif len(word) > 3 and word.endswith("s") and not word.endswith(("ss", "us", "is")):
            word = word[:-1]
        if len(word) > 4 and word.endswith("e"):
            word = word[:-1]
        words.add(word)
    return words


class DocuBot:
    def __init__(self, docs_folder="docs", llm_client=None):
        """
        docs_folder: directory containing project documentation files
        llm_client: optional Gemini client for LLM based answers
        """
        self.docs_folder = docs_folder
        self.llm_client = llm_client

        # Load documents into memory
        self.documents = self.load_documents()  # List of (filename, text)

        # Build a retrieval index (implemented in Phase 1)
        self.index = self.build_index(self.documents)

    # -----------------------------------------------------------
    # Document Loading
    # -----------------------------------------------------------

    def load_documents(self):
        """
        Loads all .md and .txt files inside docs_folder.
        Returns a list of tuples: (filename, text)
        """
        docs = []
        pattern = os.path.join(self.docs_folder, "*.*")
        for path in glob.glob(pattern):
            if path.endswith(".md") or path.endswith(".txt"):
                with open(path, "r", encoding="utf8") as f:
                    text = f.read()
                filename = os.path.basename(path)
                docs.append((filename, text))
        return docs

    # -----------------------------------------------------------
    # Index Construction (Phase 1)
    # -----------------------------------------------------------

    def build_index(self, documents):
        """
        Build a tiny inverted index mapping lowercase words to the documents
        they appear in.

        Example structure:
        {
            "token": ["AUTH.md", "API_REFERENCE.md"],
            "database": ["DATABASE.md"]
        }

        Words are case insensitive, common filler words are omitted, and
        underscores separate identifier components.
        """
        index = {}
        for filename, text in documents:
            for word in _words(text):
                index.setdefault(word, []).append(filename)
        return index

    # -----------------------------------------------------------
    # Scoring and Retrieval (Phase 1)
    # -----------------------------------------------------------

    def score_document(self, query, text):
        """
        Return a simple relevance score for how well the text matches the query.

        Count distinct query words that appear in the document.
        """
        return len(_words(query) & _words(text))

    def retrieve(self, query, top_k=3):
        """
        Use the index and scoring function to select up to top_k paragraphs.

        Return (filename, paragraph) pairs sorted by score descending. Require
        all meaningful query words in the document and at least half in the
        paragraph or its headings, including a match in the paragraph itself.
        """
        if top_k < 0:
            raise ValueError("top_k must be non-negative")

        query_words = _words(query)
        if not query_words:
            return []

        candidates = None
        for word in query_words:
            matches = set(self.index.get(word, ()))
            candidates = matches if candidates is None else candidates & matches

        results = []
        for filename, text in self.documents:
            if filename not in candidates:
                continue
            headings = {}
            for paragraph in re.split(r"\n\s*\n", text.strip()):
                paragraph = paragraph.strip()
                if not paragraph:
                    continue
                heading = re.fullmatch(r"(#{1,6})\s+(.+)", paragraph)
                if heading:
                    level = len(heading.group(1))
                    headings = {key: value for key, value in headings.items() if key < level}
                    headings[level] = paragraph
                    continue
                if not self.score_document(query, paragraph):
                    continue
                context = "\n".join([*headings.values(), paragraph])
                score = self.score_document(query, context)
                if score >= min(2, len(query_words)) and score * 2 >= len(query_words):
                    snippet = f"{headings[max(headings)]}\n\n{paragraph}" if headings else paragraph
                    heading_score = self.score_document(query, "\n".join(headings.values()))
                    specificity = sum(
                        1 / len(self.index[word])
                        for word in query_words & _words(context)
                    )
                    results.append((score, heading_score, specificity, filename, snippet))

        results.sort(key=lambda result: result[:3], reverse=True)
        return [(filename, text) for _, _, _, filename, text in results[:top_k]]

    # -----------------------------------------------------------
    # Answering Modes
    # -----------------------------------------------------------

    def answer_retrieval_only(self, query, top_k=1):
        """
        Phase 1 retrieval only mode.
        Returns raw snippets and filenames with no LLM involved.
        """
        snippets = self.retrieve(query, top_k=top_k)

        if not snippets:
            return "I do not know based on these docs."

        formatted = []
        for filename, text in snippets:
            formatted.append(f"[{filename}]\n{text}\n")

        return "\n---\n".join(formatted)

    def answer_rag(self, query, top_k=3):
        """
        Phase 2 RAG mode.
        Uses student retrieval to select snippets, then asks Gemini
        to generate an answer using only those snippets.
        """
        if self.llm_client is None:
            raise RuntimeError(
                "RAG mode requires an LLM client. Provide a GeminiClient instance."
            )

        snippets = self.retrieve(query, top_k=top_k)

        if not snippets:
            return "I do not know based on these docs."

        return self.llm_client.answer_from_snippets(query, snippets)

    # -----------------------------------------------------------
    # Bonus Helper: concatenated docs for naive generation mode
    # -----------------------------------------------------------

    def full_corpus_text(self):
        """
        Returns all documents concatenated into a single string.
        This is used in Phase 0 for naive 'generation only' baselines.
        """
        return "\n\n".join(text for _, text in self.documents)
