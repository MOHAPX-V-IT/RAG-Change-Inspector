import unittest
from rag_change_inspector.core import compare, render


def snapshot(sources, relevant=None):
    return {
        "questions": [
            {
                "id": "q1",
                "relevant_sources": ["a", "b"] if relevant is None else relevant,
                "results": [
                    {"source_id": source, "text": "<script>alert(1)</script>"}
                    for source in sources
                ],
            }
        ]
    }


class Tests(unittest.TestCase):
    def test_manual_metrics_and_duplicates(self):
        report = compare(
            snapshot(["x", "a", "a", "b"]), snapshot(["x", "a", "a", "b"]), k=3
        )
        self.assertEqual(report["aggregate"]["before"]["recall"], 0.5)
        self.assertEqual(report["aggregate"]["before"]["mrr"], 0.5)
        self.assertAlmostEqual(report["aggregate"]["before"]["precision"], 1 / 3)
        self.assertFalse(report["regression"])

    def test_regression_and_html(self):
        report = compare(snapshot(["a", "b"]), snapshot(["x", "y"]))
        self.assertTrue(report["regression"])
        self.assertNotIn("<script>alert(1)</script>", render(report))
        self.assertIn("&lt;script&gt;", render(report))

    def test_missing_unlabelled_and_empty(self):
        report = compare(snapshot([], []), snapshot([], []))
        self.assertEqual(report["unlabelled"], ["q1"])
        self.assertIsNone(report["aggregate"]["before"]["recall"])
        self.assertEqual(
            compare(snapshot([]), {"questions": []})["missing_after"], ["q1"]
        )

    def test_invalid_comparisons(self):
        bad = snapshot([])
        bad["questions"] *= 2
        for before, after in [
            (bad, snapshot([])),
            (snapshot([], ["a"]), snapshot([], ["b"])),
        ]:
            with self.assertRaises(ValueError):
                compare(before, after)
        with self.assertRaises(ValueError):
            compare(snapshot([]), snapshot([]), k=0)
