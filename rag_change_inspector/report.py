"""Self-contained, offline report. Snapshot text is never executable HTML."""

import html

CSS = """
:root{color-scheme:dark;--bg:#09090c;--panel:#121216;--text:#ececf1;--dim:#aaa8b6;--line:#313039;--accent:#f2982d}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:16px/1.6 system-ui,sans-serif}main{max-width:1200px;margin:auto;padding:48px 28px}header{max-width:820px;margin-bottom:36px}.brand,.label{font:12px ui-monospace,monospace;letter-spacing:.13em;color:var(--accent)}h1{font-size:clamp(30px,5vw,54px);letter-spacing:-.04em;line-height:1.08;margin:20px 0}header p{color:var(--dim)}.metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:24px;border-block:1px solid var(--line);padding:24px 0}.metric strong{display:block;font:27px ui-monospace,monospace;margin-top:8px}.metric small{color:var(--dim)}.notice{color:var(--accent);overflow-wrap:anywhere}.tools{display:flex;gap:18px;align-items:center;flex-wrap:wrap;margin:28px 0}input[type=search]{background:var(--panel);color:var(--text);border:1px solid var(--line);border-radius:8px;padding:12px 14px;min-width:240px;font:inherit}input:focus-visible,summary:focus-visible{outline:2px solid var(--accent);outline-offset:3px}label{cursor:pointer}.question{border-top:1px solid var(--line);padding:24px 0;overflow-wrap:anywhere}.question h2{font-size:21px;margin:8px 0}.status{font:12px ui-monospace,monospace;color:var(--accent)}.delta{color:var(--dim);font:13px ui-monospace,monospace}summary{cursor:pointer;color:var(--accent);padding:12px 0}.columns{display:grid;grid-template-columns:1fr 1fr;gap:28px}.columns h3{font-size:14px;color:var(--dim)}.chunk{background:var(--panel);border-radius:8px;padding:16px;margin:10px 0}.chunk.relevant{border-left:3px solid var(--accent)}.chunk strong{font:13px ui-monospace,monospace}.chunk p{white-space:pre-wrap;margin:10px 0 0}.changes{font-size:14px;color:var(--dim)}footer{border-top:1px solid var(--line);padding-top:24px;color:var(--dim);font-size:13px}[hidden]{display:none!important}@media(max-width:680px){main{padding:28px 18px}.metrics{grid-template-columns:1fr 1fr}.columns{grid-template-columns:1fr}.tools{align-items:flex-start;flex-direction:column}input[type=search]{width:100%;min-width:0}}
"""
JS = """
const search = document.getElementById('search');
const regressions = document.getElementById('regressions');
function filter(){let visible=0;for(const row of document.querySelectorAll('.question')){row.hidden=!(row.textContent.toLowerCase().includes(search.value.toLowerCase())&&(!regressions.checked||row.dataset.regressed==='true'));if(!row.hidden)visible++}document.getElementById('empty').hidden=visible!==0;document.getElementById('count').textContent=visible+' questions shown'}
search.addEventListener('input',filter);regressions.addEventListener('change',filter);filter();
"""


def render(report):
    esc = lambda value: html.escape(str(value), quote=True)

    def ranking(results, relevant):
        if not results:
            return "<p>No results returned.</p>"
        return "".join(
            f'<div class="chunk {"relevant" if item["source_id"] in relevant else ""}"><strong>#{rank} / {esc(item["source_id"])} / {esc(item.get("chunk_id", ""))}</strong><p>{esc(item.get("text", "No text captured."))}</p></div>'
            for rank, item in enumerate(results, 1)
        )

    tiles = ""
    for metric in ("recall", "mrr", "precision", "ndcg"):
        before, after = (
            report["aggregate"]["before"][metric],
            report["aggregate"]["after"][metric],
        )
        value = "N/A" if after is None else f"{after:.3f}"
        delta = (
            "No labelled common questions"
            if before is None
            else f"{before:.3f} before / {after - before:+.3f}"
        )
        tiles += f'<div class="metric"><span class="label">{metric.upper()}@{report["k"]}</span><strong>{value}</strong><small>{delta}</small></div>'
    notices = "".join(
        f'<p class="notice">{label}: {esc(", ".join(report[key]))}</p>'
        for key, label in [
            ("missing_after", "Missing questions"),
            ("new_after", "New questions"),
            ("unlabelled", "Excluded without labels"),
        ]
        if report[key]
    )
    rows = ""
    for row in sorted(
        report["questions"],
        key=lambda r: (not r["regressed"], r["delta"]["recall"], r["id"]),
    ):
        changes = row["changes"]
        details = []
        if changes["lost_sources"]:
            details.append("Lost: " + ", ".join(changes["lost_sources"]))
        if changes["gained_sources"]:
            details.append("Gained: " + ", ".join(changes["gained_sources"]))
        for move in changes["rank_moves"]:
            details.append(f"{move['source']}: #{move['before']} to #{move['after']}")
        for chunk in changes["changed_chunks"]:
            details.append(f"Changed text: {chunk['source_id']}/{chunk['chunk_id']}")
        delta = " / ".join(
            f"{key.upper()} {value:+.3f}" for key, value in row["delta"].items()
        )
        rows += f'<article class="question" data-regressed="{str(row["regressed"]).lower()}"><span class="status">{"REGRESSION" if row["regressed"] else "NO REGRESSION"} / {esc(row["id"])}</span><h2>{esc(row["text"])}</h2><p class="delta">{delta}</p><p class="changes">{esc(" | ".join(details) or "No source or chunk-text changes in top-k.")}</p><details><summary>Inspect retrieved fragments</summary><div class="columns"><section><h3>BEFORE</h3>{ranking(row["before_results"], row["relevant_sources"])}</section><section><h3>AFTER</h3>{ranking(row["after_results"], row["relevant_sources"])}</section></div></details></article>'
    status = (
        "INSUFFICIENT DATA"
        if not report["evaluated"]
        else "REVIEW REQUIRED"
        if report["regression"] or report["missing_after"]
        else "CHECK PASSED"
    )
    return f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>RAG Change Inspector</title><style>{CSS}</style></head><body><main><header><p class="brand">MOHAPX-V-IT / RETRIEVAL QUALITY</p><h1>See what changed<br>in retrieval.</h1><p>Compare sources, ranks and fragments before your next release.</p><p class="status">{status} / {report["evaluated"]} evaluated questions</p></header><section class="metrics" aria-label="Aggregate metrics">{tiles}</section>{notices}<div class="tools"><label>Search questions <input id="search" type="search" placeholder="Question, source or fragment"></label><label><input id="regressions" type="checkbox"> Regressions only</label><span id="count" aria-live="polite"></span></div>{rows}<p id="empty" hidden>No questions match this filter.</p><footer>RAG Change Inspector / Source-level relevance. Duplicate source hits receive credit once. Scores describe this snapshot comparison, not the cause of a change. Offline report; no external resources.</footer></main><script>{JS}</script></body></html>'
