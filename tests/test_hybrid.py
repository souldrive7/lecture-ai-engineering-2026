"""第5回 宿題（発展）: ハイブリッド取得を、実SQLiteと固定ベクトルで確かめる。APIは呼ばない。"""

import json

import pytest

from app import retrieval, tools
from scripts.build_rag_index import build_index

# 質問ベクトルは [1, 0, 0]。距離（cosine）は p1=0, p5≒0.3, p2=0.4, p4=0.5, p3=1
VECTORS = {
    "本文1": [1, 0, 0],
    "本文2": [0.6, 0.8, 0],
    "本文3": [0, 1, 0],
    "本文4 LoRA": [0.5, 0, 0.866],
    "本文5": [0.7, 0, 0.714],
    "対象外": [1, 0, 0],
}


def page(n, content):
    return {"id": f"lec01-main-p{n:03d}", "title": f"ページ{n}", "page": n, "content": content}


@pytest.fixture
def corpus(tmp_path, monkeypatch):
    source = tmp_path / "lectures.json"
    source.write_text(json.dumps([
        {"id": "lec01-main", "title": "講義1", "content": [
            {"section": "章A", "content": [page(1, "本文1。続き"), page(2, "本文2"), page(3, "本文3")]},
            {"section": "章B", "content": [page(4, "本文4 LoRA"), page(5, "本文5")]}]},
        {"id": "lec05-main", "title": "講義5", "content": [
            {"section": "章", "content": [{"id": "lec05-main-p001", "title": "対象外",
                                          "page": 1, "content": "対象外"}]}]},
    ], ensure_ascii=False), encoding="utf-8")
    graph = tmp_path / "graph.json"
    graph.write_text(json.dumps({
        "nodes": [{"id": "term:lora", "kind": "term", "title": "LoRA", "aliases": ["LoRA"]}],
        "edges": [
            {"source": "lec01-main-p001", "target": "lec01-main-p002", "relation": "next_page"},
            {"source": "lec01-main-p002", "target": "lec01-main-p003", "relation": "next_page"},
            {"source": "lec01-main-p004", "target": "term:lora", "relation": "mentions"},
            {"source": "lec05-main-p001", "target": "term:lora", "relation": "mentions"},
        ]}, ensure_ascii=False), encoding="utf-8")
    database = tmp_path / "index.sqlite3"

    def embed(text, task):
        return next(v for key, v in VECTORS.items() if key in text)

    build_index(source, database, embedder=embed)
    for name, value in {"RAG_SOURCE": source, "RAG_GRAPH": graph, "RAG_DB": database,
                        "HYBRID_SEED_K": 1, "HYBRID_MAX_RESULTS": 3, "HYBRID_FULL_K": 1}.items():
        monkeypatch.setattr(retrieval, name, value)
    monkeypatch.setattr(retrieval, "embed_text", lambda *_: [1, 0, 0])


def test_hybrid_expands_by_structure_and_ranks_by_distance(corpus):
    found = retrieval.search_hybrid("LoRAの説明")
    ids = [r["page_id"] for r in found["results"]]
    # p5 は質問に近いが、入口とも質問の用語ともつながらないので候補に入らない
    assert ids == ["lec01-main-p001", "lec01-main-p002", "lec01-main-p004"]
    assert found["query_terms"] == ["LoRA"]
    assert found["candidates_considered"] == 4  # p1, p2, p3, p4（対象外の資料は数えない）
    first, second, third = found["results"]
    assert first["reasons"] == ["vector#1"] and first["content"] == "本文1。続き"
    assert second["reasons"] == ["same_section(p.1)", "next_page(p.1)"]
    assert "content" not in second and second["preview"] == "本文2"
    assert third["reasons"] == ["term(LoRA)"]
    assert first["distance"] < second["distance"] < third["distance"]


def test_hybrid_never_returns_duplicates_or_other_documents(corpus, monkeypatch):
    monkeypatch.setattr(retrieval, "HYBRID_MAX_RESULTS", 10)
    ids = [r["page_id"] for r in retrieval.search_hybrid("LoRA")["results"]]
    assert len(ids) == len(set(ids)) == 4
    assert all(i.startswith("lec01-main") for i in ids)


def test_read_pages_limits_and_errors(corpus):
    assert [p["page"] for p in retrieval.read_pages(["lec01-main-p004", "lec01-main-p004"])] == [4]
    with pytest.raises(ValueError, match="見つかりません"):
        retrieval.read_pages(["lec05-main-p001"])
    with pytest.raises(ValueError, match="4ページまで"):
        retrieval.read_pages([f"lec01-main-p00{n}" for n in range(1, 6)])
    assert json.loads(tools.read_pages([]))["error"]


def test_hybrid_tool_reports_empty_query_as_error(corpus):
    assert json.loads(tools.search_hybrid("  "))["error"] == "検索語が空です。"
