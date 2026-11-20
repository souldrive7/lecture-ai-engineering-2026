"""エージェントの配線テスト。

TestModel は実際のLLMを呼ばない偽モデルで、登録されたツールを全部呼んでから
ダミーの回答を返す。APIキーも利用枠も使わずに、
「ツールが登録され、呼ばれ、結果がモデルに戻るか」を確かめられる。
"""

import json

from pydantic_ai import DeferredToolRequests
from pydantic_ai.messages import ToolCallPart, ToolReturnPart
from pydantic_ai.models.test import TestModel

from app.agent import agent, build_lec03_agent

BASE_TOOLS = {"search_materials"}


def _parts(result, kind):
    return [p for m in result.all_messages() for p in m.parts if isinstance(p, kind)]


def test_base_tools_are_registered_and_called(monkeypatch):
    monkeypatch.setattr("app.retrieval.search", lambda *args, **kwargs: [])
    model = TestModel()
    with agent.override(model=model):
        result = agent.run_sync("LoRAとは？")

    offered = {t.name for t in model.last_model_request_parameters.function_tools}
    assert BASE_TOOLS <= offered  # 演習でツールを足しても壊れないよう「含む」で判定

    called = {p.tool_name for p in _parts(result, ToolCallPart)}
    assert BASE_TOOLS <= called
    # 承認が必要なツール（requires_approval=True）は、実行されずに承認待ちになるので戻り値が無い
    waiting = len(result.output.approvals) if isinstance(result.output, DeferredToolRequests) else 0
    assert len(_parts(result, ToolReturnPart)) + waiting == len(_parts(result, ToolCallPart))
    assert result.output


def test_material_result_reaches_the_model(monkeypatch):
    hit = {"page_id": "lec02-main-p052", "lecture": 2, "page": 52, "content": "元の重みは固定"}
    monkeypatch.setattr("app.retrieval.search", lambda *args, **kwargs: [hit])
    model = TestModel(call_tools=["search_materials"])
    with agent.override(model=model):
        result = agent.run_sync("RAGとは？")
    returns = _parts(result, ToolReturnPart)
    assert returns and returns[0].tool_name == "search_materials"
    assert json.loads(returns[0].content)["results"] == [hit]


# 第3回の宿題: 承認付きの学習記録ツール（第5回からは --lec03 のエージェントで使う）

def test_lec03_agent_offers_glossary_and_learning_log():
    model = TestModel(call_tools=[])
    build_lec03_agent().run_sync("ツール一覧", model=model)
    offered = {t.name for t in model.last_model_request_parameters.function_tools}
    assert offered == {"search_glossary", "get_lecture_summary", "save_learning_log"}


def test_learning_log_requires_approval_before_execution():
    lec03 = build_lec03_agent()
    model = TestModel(call_tools=["save_learning_log"])
    with lec03.override(model=model):
        result = lec03.run_sync("学習記録を保存して")

    assert isinstance(result.output, DeferredToolRequests)
    assert [call.tool_name for call in result.output.approvals] == ["save_learning_log"]
    assert not result.output.calls


def test_learning_log_can_resume_after_approval(tmp_path, monkeypatch):
    monkeypatch.setattr("app.tools.LEARNING_LOG_DIR", tmp_path)
    lec03 = build_lec03_agent()
    model = TestModel(call_tools=["save_learning_log"])
    with lec03.override(model=model):
        first = lec03.run_sync("学習記録を保存して")
        assert isinstance(first.output, DeferredToolRequests)
        resumed = lec03.run_sync(
            None,
            message_history=first.all_messages(),
            deferred_tool_results=first.output.build_results(approve_all=True),
        )

    assert isinstance(resumed.output, str)
    assert any(p.tool_name == "save_learning_log" for p in _parts(resumed, ToolReturnPart))
