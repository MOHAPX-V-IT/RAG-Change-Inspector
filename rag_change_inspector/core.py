"""Source-level retrieval metrics over ranked chunk snapshots."""

import math

METRICS = ("recall", "mrr", "precision", "ndcg")


def validate(snapshot):
    if not isinstance(snapshot, dict) or not isinstance(
        snapshot.get("questions"), list
    ):
        raise ValueError("Snapshot must contain a questions array")
    if snapshot.get("version", 1) != 1:
        raise ValueError("Unsupported snapshot version")
    rows = {}
    for row in snapshot["questions"]:
        if not isinstance(row, dict):
            raise ValueError("Each question must be an object")
        identifier = row.get("id")
        if not isinstance(identifier, str) or not identifier or identifier in rows:
            raise ValueError("Question IDs must be nonempty and unique")
        if "text" in row and not isinstance(row["text"], str):
            raise ValueError("Question text must be a string")
        relevant = row.get("relevant_sources")
        if not isinstance(relevant, list) or any(
            not isinstance(x, str) or not x for x in relevant
        ):
            raise ValueError("relevant_sources must be a list of source IDs")
        if not isinstance(row.get("results"), list):
            raise ValueError("results must be an array")
        chunks = set()
        for result in row["results"]:
            if (
                not isinstance(result, dict)
                or not isinstance(result.get("source_id"), str)
                or not result["source_id"]
            ):
                raise ValueError("source_id must be a nonempty string")
            for field in ("chunk_id", "text"):
                if field in result and not isinstance(result[field], str):
                    raise ValueError(f"{field} must be a string")
            if "chunk_id" in result:
                identity = (result["source_id"], result["chunk_id"])
                if identity in chunks:
                    raise ValueError("Duplicate chunk in one ranking")
                chunks.add(identity)
        rows[identifier] = row
    return rows


def metrics(row, k):
    relevant = set(row["relevant_sources"])
    hits = [
        (i + 1, item["source_id"])
        for i, item in enumerate(row["results"][:k])
        if item["source_id"] in relevant
    ]
    unique = {source for _, source in hits}
    seen, dcg = set(), 0.0
    for rank, source in hits:
        if source not in seen:
            dcg += 1 / math.log2(rank + 1)
            seen.add(source)
    ideal = sum(1 / math.log2(rank + 1) for rank in range(1, min(k, len(relevant)) + 1))
    return {
        "recall": len(unique) / len(relevant),
        "mrr": 1 / hits[0][0] if hits else 0.0,
        "precision": len(unique) / k,
        "ndcg": dcg / ideal,
    }


def changes(a, b, k):
    def ranks(row):
        found = {}
        for rank, item in enumerate(row["results"][:k], 1):
            found.setdefault(item["source_id"], rank)
        return found

    left, right = ranks(a), ranks(b)
    before_text = {
        (r["source_id"], r.get("chunk_id")): r.get("text", "")
        for r in a["results"][:k]
        if r.get("chunk_id")
    }
    after_text = {
        (r["source_id"], r.get("chunk_id")): r.get("text", "")
        for r in b["results"][:k]
        if r.get("chunk_id")
    }
    return {
        "lost_sources": sorted(left.keys() - right.keys()),
        "gained_sources": sorted(right.keys() - left.keys()),
        "rank_moves": [
            {"source": source, "before": left[source], "after": right[source]}
            for source in sorted(left.keys() & right.keys())
            if left[source] != right[source]
        ],
        "changed_chunks": [
            {"source_id": key[0], "chunk_id": key[1]}
            for key in sorted(before_text.keys() & after_text.keys())
            if before_text[key] != after_text[key]
        ],
    }


def compare(before, after, k=5, max_drop=0.0, fail_on_question=False):
    if (
        type(k) is not int
        or k < 1
        or not isinstance(max_drop, (int, float))
        or not math.isfinite(max_drop)
        or not 0 <= max_drop <= 1
    ):
        raise ValueError("k must be positive; max_drop must be between 0 and 1")
    left, right = validate(before), validate(after)
    rows, unlabelled = [], []
    for identifier in sorted(left.keys() & right.keys()):
        a, b = left[identifier], right[identifier]
        if a.get("text") != b.get("text"):
            raise ValueError(f"Question text changed for {identifier}")
        if set(a["relevant_sources"]) != set(b["relevant_sources"]):
            raise ValueError(f"Ground truth changed for {identifier}")
        if not a["relevant_sources"]:
            unlabelled.append(identifier)
            continue
        ma, mb = metrics(a, k), metrics(b, k)
        delta = {key: mb[key] - ma[key] for key in ma}
        rows.append(
            {
                "id": identifier,
                "text": a.get("text", identifier),
                "relevant_sources": sorted(set(a["relevant_sources"])),
                "before": ma,
                "after": mb,
                "delta": delta,
                "regressed": any(value < -max_drop - 1e-12 for value in delta.values()),
                "before_results": a["results"][:k],
                "after_results": b["results"][:k],
                "changes": changes(a, b, k),
            }
        )
    aggregate = {
        side: {
            metric: sum(row[side][metric] for row in rows) / len(rows) if rows else None
            for metric in METRICS
        }
        for side in ("before", "after")
    }
    failed = (
        any(
            aggregate["before"][metric] - aggregate["after"][metric] > max_drop + 1e-12
            for metric in METRICS
        )
        if rows
        else False
    )
    if fail_on_question:
        failed = failed or any(row["regressed"] for row in rows)
    return {
        "version": 1,
        "k": k,
        "max_drop": max_drop,
        "fail_on_question": fail_on_question,
        "evaluated": len(rows),
        "aggregate": aggregate,
        "regression": failed,
        "missing_after": sorted(left.keys() - right.keys()),
        "new_after": sorted(right.keys() - left.keys()),
        "unlabelled": unlabelled,
        "questions": rows,
    }


def render(report):
    from .report import render as render_report

    return render_report(report)
