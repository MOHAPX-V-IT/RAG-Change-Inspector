# RAG Change Inspector guide

## Snapshot format

```json
{
  "version": 1,
  "questions": [{
    "id": "cancel-booking",
    "text": "How do I cancel a booking?",
    "relevant_sources": ["booking-policy"],
    "results": [{
      "source_id": "booking-policy",
      "chunk_id": "policy-12",
      "text": "Cancel before the booking starts."
    }]
  }]
}
```

`results` are ordered best-first. Source IDs are stable document identifiers; chunk IDs identify fragments. Question and source IDs must remain stable across snapshots. Question text (if present) and relevance labels must match exactly across versions. Renaming a question makes it missing/new rather than comparable.

Question text, chunk IDs and fragment text are optional. Text-change detection needs a stable `(source_id, chunk_id)` pair in both top-k lists. Different chunks from the same source are allowed; duplicate chunk IDs within that source are rejected. Scores from different embedding models are not compared.

## Metric definitions

All metrics use binary **source-level** relevance over the first k ranked **chunks**. Repeated hits from one source receive credit only once, at its earliest rank. This explicitly penalizes rankings crowded with duplicate-source fragments.

- Recall@K: unique relevant sources retrieved / all labelled relevant sources.
- Precision@K: unique relevant sources retrieved / K. Short rankings still use K as denominator.
- MRR@K: reciprocal rank of the first relevant chunk, or zero.
- NDCG@K: sum of `1/log2(rank+1)` for the first hit of each relevant source, divided by the ideal sum for `min(K, relevant-source-count)` sources.

Aggregate values are macro-averages over common questions with nonempty labels. Questions with no labels are reported as excluded. Missing questions, new questions and excluded questions are listed separately. These source-aware precision/NDCG definitions can differ from libraries that count each chunk independently.

## CLI

```shell
python -m rag_change_inspector validate before.json
python -m rag_change_inspector compare before.json after.json --k 5 --max-drop 0.02 --fail-on-question --html reports/diff.html --json reports/diff.json
```

The default gate fails when any aggregate metric drops by more than `--max-drop` (absolute metric points, not relative percent). `--fail-on-question` additionally fails if any individual question exceeds this threshold on any metric. The HTML regression filter uses the same per-question threshold regardless of whether that CI gate is enabled.

Exit codes: 0 pass; 1 metric regression or a question missing from the after snapshot; 2 invalid input or no common labelled questions. Newly added questions do not fail the gate. Inputs cannot be overwritten by report output paths. Reports overwrite previous reports at the requested destination.

## Offline HTML report

Open the file directly. Search matches question IDs/text, fragment text and source identifiers. Enable **Regressions only** and expand a question for side-by-side evidence. Mobile layout stacks the rankings. The report lists lost/gained sources, rank moves and changed chunk text. It has no remote fonts, scripts, telemetry or network calls.

The report does not prove why a result changed, assess generated answers or automatically tune a retriever. Snapshot comparisons alone cannot establish causation.

## Python API

```python
import json
from pathlib import Path
from rag_change_inspector import compare, render

before = json.loads(Path("examples/before.json").read_text())
after = json.loads(Path("examples/after.json").read_text())
report = compare(before, after, k=1, max_drop=0.02, fail_on_question=True)
Path("report.html").write_text(render(report), encoding="utf-8")
```

## Chroma adapter

`snapshot_chroma(collection, questions, k=5, query_embeddings=None)` accepts an existing Chroma collection. Every chunk must contain a stable `metadata.source_id`. Questions use the same `id`, `text` and `relevant_sources` fields as snapshots.

```python
from rag_change_inspector import snapshot_chroma

# collection is your configured Chroma collection.
# snapshot = snapshot_chroma(collection, questions, k=5,
#                            query_embeddings=question_embeddings)
```

Providing embeddings avoids invoking the collection's text embedding function. Without them, the adapter passes `query_texts`; the collection may call a remote embedding provider or download a model. The adapter queries the collection, but does not modify it. Comparing saved JSON remains fully offline.

The adapter is duck-typed and tested against the documented query response shape. Chroma is not installed or bundled by this package. See [Chroma collection API](https://docs.trychroma.com/reference/python/collection).

## Development

`python -m pip install -e ".[dev]"` then `python -m pytest`. Example snapshots are synthetic. Reports can contain full document fragments; distribute them according to the source data's access policy.
