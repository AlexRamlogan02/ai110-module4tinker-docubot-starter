import unittest
from pathlib import Path
from unittest.mock import patch

from docubot import DocuBot


class DocuBotRetrievalTests(unittest.TestCase):
    def setUp(self):
        documents = [
            ("auth.md", "Auth token, token generation."),
            ("api.md", "API token refresh."),
            ("other.md", "Database connection."),
        ]
        with patch.object(DocuBot, "load_documents", return_value=documents):
            self.bot = DocuBot()

    def test_index_and_score_use_distinct_case_insensitive_words(self):
        self.assertEqual(self.bot.index["token"], ["auth.md", "api.md"])
        self.assertEqual(self.bot.score_document("TOKEN token, Auth!", "auth token"), 2)
        self.assertEqual(self.bot.score_document("cat", "concatenate"), 0)

    def test_retrieve_ranks_matches_and_respects_limit(self):
        results = self.bot.retrieve("TOKEN, auth?", top_k=1)
        self.assertEqual(results, [("auth.md", "Auth token, token generation.")])
        self.assertEqual(
            [name for name, _ in self.bot.retrieve("token")],
            ["auth.md", "api.md"],
        )
        self.assertEqual(self.bot.retrieve("token", top_k=0), [])
        with self.assertRaises(ValueError):
            self.bot.retrieve("token", top_k=-1)

    def test_no_match_and_rag_receive_retrieved_documents(self):
        self.assertEqual(self.bot.retrieve("missing"), [])
        self.assertEqual(
            self.bot.answer_retrieval_only("missing"),
            "I do not know based on these docs.",
        )

        class FakeClient:
            def answer_from_snippets(self, query, snippets):
                return query, snippets

        self.bot.llm_client = FakeClient()
        self.assertEqual(
            self.bot.answer_rag("auth", top_k=1),
            ("auth", [("auth.md", "Auth token, token generation.")]),
        )

    def test_returns_matching_paragraph_instead_of_entire_document(self):
        documents = [
            ("auth.md", "Unrelated setup instructions.\n\nTokens are signed by auth_utils.\n\nOther details."),
        ]
        with patch.object(DocuBot, "load_documents", return_value=documents):
            bot = DocuBot()
        self.assertEqual(
            bot.answer_retrieval_only("Where are auth tokens signed?"),
            "[auth.md]\nTokens are signed by auth_utils.\n",
        )

    def test_refuses_incidental_and_filler_only_matches(self):
        for query in ("Where is the payment processing token?", "What is in the docs?", ""):
            with self.subTest(query=query):
                self.assertEqual(
                    self.bot.answer_retrieval_only(query),
                    "I do not know based on these docs.",
                )

    def test_auth_question_finds_generation_paragraph(self):
        docs = Path(__file__).resolve().parents[1] / "docs"
        bot = DocuBot(docs_folder=str(docs))
        answer = bot.answer_retrieval_only("Where is the auth token generated?")
        self.assertIn("[AUTH.md]", answer)
        self.assertIn("generate_access_token", answer)
        self.assertNotIn("## Client Workflow", answer)
        self.assertEqual(
            bot.answer_retrieval_only("Is there any mention of payment processing in these docs?"),
            "I do not know based on these docs.",
        )
        self.assertEqual(
            bot.answer_retrieval_only("Where is the auth token generated for payment processing?"),
            "I do not know based on these docs.",
        )

    def test_headings_and_specific_words_select_relevant_paragraph(self):
        docs = Path(__file__).resolve().parents[1] / "docs"
        bot = DocuBot(docs_folder=str(docs))
        project = bot.answer_retrieval_only(
            "What does the /api/projects/<project_id> route return?"
        )
        self.assertIn("### GET /api/projects/<project_id>", project)
        self.assertIn("detailed information", project)
        refresh = bot.answer_retrieval_only("How does a client refresh an access token?")
        self.assertIn("/api/refresh", refresh)


if __name__ == "__main__":
    unittest.main()
