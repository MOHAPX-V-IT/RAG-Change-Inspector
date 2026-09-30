import copy
import tempfile
import unittest
from pathlib import Path
from rag_change_inspector import compare, validate, snapshot_chroma
from rag_change_inspector.__main__ import main


def snap(order):
    return {
        "questions": [
            {
                "id": "q",
                "text": "Question",
                "relevant_sources": ["a"],
                "results": [{"source_id": s, "chunk_id": s, "text": s} for s in order],
            }
        ]
    }


class FeatureTests(unittest.TestCase):
    def test_ndcg_and_rank_changes(self):
        report = compare(snap(["a", "b"]), snap(["b", "a"]), k=2)
        self.assertEqual(report["aggregate"]["before"]["ndcg"], 1)
        self.assertAlmostEqual(
            report["aggregate"]["after"]["ndcg"], 1 / 1.584962500721156
        )
        self.assertEqual(
            report["questions"][0]["changes"]["rank_moves"][0],
            {"source": "a", "before": 1, "after": 2},
        )

    def test_changed_question_and_chunks(self):
        after = snap(["a"])
        after["questions"][0]["text"] = "Different"
        with self.assertRaises(ValueError):
            compare(snap(["a"]), after)
        after = snap(["a"])
        after["questions"][0]["results"][0]["text"] = "New policy"
        self.assertTrue(
            compare(snap(["a"]), after)["questions"][0]["changes"]["changed_chunks"]
        )

    def test_question_gate_catches_hidden_regression(self):
        before = snap(["a", "b"])
        after = snap(["b", "a"])
        b = copy.deepcopy(after["questions"][0])
        b["id"] = "q2"
        a = copy.deepcopy(before["questions"][0])
        a["id"] = "q2"
        before["questions"].append(b)
        after["questions"].append(a)
        self.assertFalse(compare(before, after, k=1)["regression"])
        self.assertTrue(
            compare(before, after, k=1, fail_on_question=True)["regression"]
        )

    def test_chroma_adapter(self):
        class Collection:
            def query(self, **kwargs):
                self.kwargs = kwargs
                return {
                    "ids": [["chunk"]],
                    "metadatas": [[{"source_id": "policy"}]],
                    "documents": [["text"]],
                }

        collection = Collection()
        result = snapshot_chroma(
            collection,
            [{"id": "q", "text": "Q", "relevant_sources": ["policy"]}],
            query_embeddings=[[1, 2]],
        )
        self.assertEqual(result["questions"][0]["results"][0]["source_id"], "policy")
        self.assertIn("query_embeddings", collection.kwargs)
        self.assertNotIn("query_texts", collection.kwargs)

    def test_cli_init_outputs_and_protection(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            self.assertEqual(main(["init", str(base)]), 0)
            self.assertEqual(
                main(
                    [
                        "compare",
                        str(base / "before.json"),
                        str(base / "after.json"),
                        "--k",
                        "1",
                        "--html",
                        str(base / "report.html"),
                    ]
                ),
                1,
            )
            self.assertTrue((base / "report.html").exists())
            with self.assertRaises(SystemExit):
                main(
                    [
                        "compare",
                        str(base / "before.json"),
                        str(base / "after.json"),
                        "--json",
                        str(base / "before.json"),
                    ]
                )
            with self.assertRaises(SystemExit):
                main(["init", str(base)])

    def test_bad_inputs(self):
        for data in [None, [], {"questions": [None]}, {"questions": [{"id": 1}]}]:
            with self.assertRaises(ValueError):
                validate(data)
