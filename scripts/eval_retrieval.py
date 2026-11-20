"""第5回 宿題（発展）: 取得だけを比べる。回答は生成しない。

同じ質問文をそのまま検索語にして、ベクトル検索・既存Graph・ハイブリッドが返すページに
根拠ページが含まれるか（再現率）と、モデルに渡す量（文字数）を数える。
質問の埋め込みは1回だけ計算し、3つの方式で共有する（GEMINI_API_KEY が必要）。

    uv run python -m scripts.eval_retrieval
"""

import json
import sys
from functools import cache
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import retrieval as r  # noqa: E402

# 根拠ページ。内側のリストはどれか1つあればよい（同じ内容を説明する別ページ）
QUESTIONS = [
    {"id": "Q1", "kind": "単一ページ",
     "question": "第2回の説明では、LoRAは何を固定し何を学習しますか？ QLoRAは何を加えますか？",
     "gold": [["lec02-main-p052"]]},
    {"id": "Q2", "kind": "章をまたぐ",
     "question": "第3回の例では、コンパクションとセッションをまたぐメモリはどう違いますか。日々のメモはすべて長期メモリに入りますか",
     "gold": [["lec03-main-p013"], ["lec03-main-p039"], ["lec03-main-p040"]]},
    {"id": "Q3", "kind": "回をまたぐ",
     "question": "第1回の例題チャットボットはなぜRAGで作るのですか。第2回では、知識の追加にファインチューニングよりRAGが効きやすい根拠をどう説明していますか",
     "gold": [["lec01-main-p049", "lec01-main-p019"], ["lec02-main-p047"]]},
]

OUT = Path(__file__).resolve().parents[1] / "lectures/05/homework/retrieval_eval.json"


def covered(gold: list[list[str]], page_ids: set[str]) -> int:
    return sum(any(p in page_ids for p in group) for group in gold)


def summarize(name: str, items: list[dict], gold) -> dict:
    full = {i["page_id"] for i in items if "content" in i}
    shown = {i["page_id"] for i in items}
    return {
        "method": name, "pages": len(items), "full_text_pages": len(full),
        "gold_in_full_text": covered(gold, full), "gold_shown": covered(gold, shown),
        "gold_total": len(gold),
        "chars_to_model": len(json.dumps(items, ensure_ascii=False)),
        "page_ids": [i["page_id"] for i in items],
    }


def main() -> None:
    embed = cache(r.embed_text)
    r.embed_text = embed  # 3方式で同じ質問ベクトルを共有する（API呼び出しは質問ごとに1回）
    report = []
    for q in QUESTIONS:
        vector = embed(q["question"], "RETRIEVAL_QUERY")
        with r.open_index(r.RAG_DB) as db:
            ranking = [row["page_id"] for row in r._nearest(db, vector, 1000)]
        gold_rank = {p: ranking.index(p) + 1 for group in q["gold"] for p in group}
        graph = r.search_graph(q["question"])
        hybrid = r.search_hybrid(q["question"])
        rows = [
            summarize("vector(top5)", r.search(q["question"]), q["gold"]),
            summarize("graph", graph["seeds"] + graph["expanded"], q["gold"]),
            summarize("hybrid", hybrid["results"], q["gold"]),
        ]
        report.append({**q, "gold_vector_rank": gold_rank, "query_terms": hybrid["query_terms"],
                       "hybrid_reasons": {i["page_id"]: i["reasons"] for i in hybrid["results"]},
                       "results": rows})
        print(f"\n## {q['id']}（{q['kind']}） 根拠ページの全体順位（ベクトル距離）: {gold_rank}")
        print(f"質問に出た用語: {hybrid['query_terms']}")
        print("| 方式 | 返すページ | うち全文 | 根拠（全文で） | 根拠（候補に表示） | 渡す文字数 |")
        print("|---|---|---|---|---|---|")
        for row in rows:
            print(f"| {row['method']} | {row['pages']} | {row['full_text_pages']} | "
                  f"{row['gold_in_full_text']}/{row['gold_total']} | {row['gold_shown']}/{row['gold_total']} | "
                  f"{row['chars_to_model']:,} |")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n保存: {OUT}")


if __name__ == "__main__":
    main()
