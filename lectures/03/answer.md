# 第3回 解答

## 演習

- 第1回（素のLLM）とエージェントの回答の違い：
- `--trace` で見えたツール呼び出し（ツール名と引数）：
- 1つの質問での LLM 呼び出し回数（`requests`）：
- 追加したツールと、docstring に書いた説明：

## 宿題

- 取り組んだレベル：発展(a)（完了）
- やったこと：`app/tools.py` に `save_learning_log(topic, reflection)` を追加した。学習内容を Markdown として `learning_log/` に保存し、空の題名・本文は保存しないようにした。`app/agent.py` では `requires_approval=True` を付けて登録し、出力型に `DeferredToolRequests` を加えた。さらに `adk_agent/glossary_agent/agent.py` を追加し、同じ `INSTRUCTIONS` と `search_glossary`・`get_lecture_summary` を Google ADK の `root_agent` として組み立てた。
- 結果：`uv run pytest -q` は 21 passed。TestModel で保存ツールを呼ぶと、最初の実行では `DeferredToolRequests` の `approvals` に `save_learning_log` が返り、保存処理は実行されなかった。承認結果で再開するとツールの結果が返り、Markdown ファイルが生成されることを確認した。ADK版は `uv run --with google-adk python -c ...` でロードでき、2つのツールが登録されることを確認した。さらに `uv run --with google-adk adk web --no-reload --port 8765 adk_agent` でADK Webサーバーが `http://127.0.0.1:8765` に起動することを確認した。
- 比較：Pydantic AI版は `Agent` にツールを登録し、`--trace` でターミナルにツール呼び出し・戻り値・使用量を表示する。ADK版は `root_agent = Agent(...)` に指示とツールを渡し、`adk web` のブラウザ画面でアプリ・セッション・イベントを追跡する構成である。前者はPython側で承認再開ループを明示的に実装し、後者はWeb UIとADKのイベント表示を利用する点が異なる。
- 制約：ADKの起動と構成比較は確認できたが、同じ質問を送る実API比較はGoogle APIの402（prepayment credits depleted）で実行できなかった。APIキーや回答本文を提出物へ保存せず、外部サービスの残高に依存する部分はこの制約として記録した。
- 気づき・疑問：`requires_approval=True` を付けるだけではCLIの確認処理までは自動化されず、`DeferredToolResults` と会話履歴を使った再開処理が必要になる。ADK版では `root_agent` を置く構成と、リポジトリ直下のツールを読むための `PYTHONPATH=.` が必要だった。Pydantic AIとADKは、同じ指示・ツールでもエージェントの組み立て方と観測UIが異なる。
