"""第1回: 素のLLMへ単発または対話形式で質問するスクリプト。

使い方:
    uv run python -m app.ask "LoRAとは何ですか？"
    uv run python -m app.ask            # 質問を省略すると、講座に固有の質問をする
    uv run python -m app.ask --chat     # 会話履歴を保持して対話する

ツールを持たない「素の」呼び出し。対話モードでは同じチャットセッションを使い、
会話履歴を次の質問へ引き継ぐ。
講座に固有のことを聞くと、「分からない」と答えるか、一般論でもっともらしく答える
（講座の実際とは違う）ことを確かめよう。
（第3回で、用語集を検索できるエージェントにして改善する）
"""

import argparse

from google import genai
from google.genai import errors

from app.config import MODEL, api_error_message, get_api_key

# 講座に固有の質問。正しい答えは data/glossary.json の homework-levels にある
DEFAULT_QUESTION = "AIE2026の講座の宿題にある「3レベル」とは何ですか？"


def print_token_usage(response: object) -> None:
    usage = getattr(response, "usage_metadata", None)
    if usage is None:
        return

    input_tokens = getattr(usage, "prompt_token_count", None)
    output_tokens = getattr(usage, "candidates_token_count", None)
    total_tokens = getattr(usage, "total_token_count", None)
    print(
        f"[tokens] input={input_tokens} output={output_tokens} "
        f"total={total_tokens}"
    )


def ask(question: str) -> str:
    client = genai.Client(api_key=get_api_key())
    response = client.models.generate_content(model=MODEL, contents=question)
    print_token_usage(response)
    return response.text


def chat() -> None:
    client = genai.Client(api_key=get_api_key())
    conversation = client.chats.create(model=MODEL)

    while True:
        try:
            question = input("質問> ")
        except (EOFError, KeyboardInterrupt):
            print()
            return

        if question in ("/exit", "/quit"):
            return
        if not question.strip():
            continue

        try:
            response = conversation.send_message(question)
        except KeyboardInterrupt:
            print()
            return
        except errors.APIError as e:
            print(api_error_message(e.code, e.message))
            continue

        print_token_usage(response)
        print(response.text)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="素のLLMへ単発または対話形式で質問する"
    )
    parser.add_argument("question", nargs="?", default=DEFAULT_QUESTION)
    parser.add_argument(
        "--chat",
        action="store_true",
        help="会話履歴を保持する対話モードを開始する",
    )
    args = parser.parse_args()

    print(f"[model] {MODEL}")
    if args.chat:
        chat()
        return

    print(f"[質問] {args.question}\n")
    try:
        print(ask(args.question))
    except errors.APIError as e:
        print(api_error_message(e.code, e.message))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
