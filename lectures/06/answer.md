# 第6回 演習・宿題

## 演習

- **STEP 1 のツールの名前**: `glossary_search_glossary`
- **STEP 2 の `[tool call]`**:
  - `glossary_search_glossary({'query': '3レベル'})`
- **STEP 3 の `[tool call]`**:
  - `fetch_fetch({'url': 'https://modelcontextprotocol.io/'})`
  - `glossary_search_glossary({'query': 'MCP'})`
- **STEP 4 の `[tool call]`**:
  - `aws_aws___search_documentation({'topics': ['general'], 'search_phrase': 'Amazon S3 バージョニング 概要'})`
  - `aws_aws___search_documentation({'topics': ['general'], 'search_phrase': 'Using versioning Amazon S3'})`

## 宿題

- **取り組んだレベル**: 発展
- **やったこと**:
  Claude Code の公式ドキュメント（MCP設定ガイド）を参照し、MCPサーバーの設定方法（設定ファイルの場所、コマンド起動・URL接続の記述形式、有効範囲）を調査した上で、第6回演習で使用した `app/mcp_servers.json` との構造および仕様の違いを比較した。
  - 調査日: 2026年11月27日
  - 参照URL: https://code.claude.com/docs/en/mcp

- **結果**:
  演習の `app/mcp_servers.json` と Claude Code の設定方法の比較結果は以下の通り。

  | 比較項目 | 演習（`app/mcp_servers.json`） | Claude Code |
  | :--- | :--- | :--- |
  | **設定を書く場所** | プロジェクト内の `app/mcp_servers.json` を直接編集 | プロジェクト共有は `.mcp.json`、個人・全体設定は `~/.claude.json`。`claude mcp add` コマンドによる追加にも対応 |
  | **コマンドで起動する書き方** | `"command"` と `"args"` 配列を記述（`type` 指定なし） | `"type": "stdio"`（省略可）に加え、`"command"`, `"args"`, `"env"` を記述 |
  | **URLで接続する書き方** | `"url": "https://..."` のみを記述（キー名で自動判別） | `"type": "http"`（または `"sse"`）のトランスポート種別を明示した上で `"url"` を記述 |
  | **有効になる範囲** | この演習エージェント（`app/mcp_agent.py`）の実行時のみ | `local`（現在のプロジェクト・個人用）、`project`（`.mcp.json` でチーム共有）、`user`（全プロジェクト共通）の3段階で制御可能 |

- **気づき・疑問**:
  演習の `app/mcp_servers.json` は学習用に最小限のキー（`command` または `url`）だけで接続方式を自動判別するシンプルな設計になっている一方、実運用向けの Claude Code ではチーム共有と個人設定（認証情報やローカル環境依存パス）を分離するためのスコープ管理（`local` / `project` / `user`）や、通信プロトコル（`stdio` / `http`）の明示が重視されていることが分かった。また、演習の STEP 3 では `fetch` だけでなく既存の `glossary` もモデルが自律的に併用しており、複数サーバーを横断したツール選択の挙動も確認できた。
