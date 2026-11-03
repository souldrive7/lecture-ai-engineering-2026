# 第3回 解答

## 演習

- 第1回（素のLLM）とエージェントの回答の違い：
- `--trace` で見えたツール呼び出し（ツール名と引数）：
- 1つの質問での LLM 呼び出し回数（`requests`）：
- 追加したツールと、docstring に書いた説明：

## 宿題

- 取り組んだレベル：発展（a）（実装レベルも実施）
- やったこと：`app/tools.py` に `save_learning_log(topic, reflection)` を追加した。学習内容を Markdown として `learning_log/` に保存し、空の題名・本文は保存しないようにした。`app/agent.py` では `requires_approval=True` を付けて登録し、出力型に `DeferredToolRequests` を加えた。さらに `adk_agent/glossary_agent/agent.py` を追加し、同じ `INSTRUCTIONS` と `search_glossary`・`get_lecture_summary` を Google ADK の `root_agent` として組み立てた。
- 結果：`uv run pytest -q` は 15 passed。TestModel で保存ツールを呼ぶと、最初の実行では `DeferredToolRequests` の `approvals` に `save_learning_log` が返り、保存処理は実行されなかった。承認結果で再開するとツールの結果が返り、Markdown ファイルが生成されることを確認した。ADK版は `uv run --with google-adk python -c ...` でロードでき、2つのツールが登録されることを確認した。課題指定の `PYTHONPATH=. uv run --with google-adk adk run adk_agent/glossary_agent` も、環境変数を付けることでエージェント起動まで進んだが、実行時はGoogle APIの402（prepayment credits depleted）で停止したため、同じ質問への回答比較は未実施である。
- 気づき・疑問：`requires_approval=True` を付けるだけではCLIの確認処理までは自動化されず、`DeferredToolResults` と会話履歴を使った再開処理が必要になる。ADK版では `root_agent` を置く構成と、リポジトリ直下のツールを読むための `PYTHONPATH=.` が必要だった。Pydantic AIとADKは、同じ指示・ツールでもエージェントの組み立て方と起動方法が異なる。API残高を回復したら、同じ質問で回答・ツール呼び出し・呼び出し回数を比較する。
