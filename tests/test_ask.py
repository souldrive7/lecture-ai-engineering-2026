"""ask.py のテスト（実APIもAPIキーも使わない）。"""

from types import SimpleNamespace

from app import ask as ask_module


class FakeChat:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.questions = []

    def send_message(self, question):
        self.questions.append(question)
        return next(self.responses)


class FakeChats:
    def __init__(self, chat):
        self.chat = chat
        self.created_models = []

    def create(self, *, model):
        self.created_models.append(model)
        return self.chat


class FakeClient:
    def __init__(self, chat):
        self.chats = FakeChats(chat)


def fake_response(text, usage=None):
    return SimpleNamespace(text=text, usage_metadata=usage)


def run_chat(monkeypatch, tmp_path, inputs, chat):
    client = FakeClient(chat)
    api_key = "test-api-key-must-not-be-saved"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(ask_module, "get_api_key", lambda: api_key)
    monkeypatch.setattr(
        ask_module.genai,
        "Client",
        lambda *, api_key: client,
    )
    monkeypatch.setattr("builtins.input", lambda _prompt: next(inputs))
    monkeypatch.setattr("sys.argv", ["app.ask", "--chat"])

    ask_module.main()
    return client, api_key


def test_chat_sends_questions_in_order_to_the_same_chat(monkeypatch, tmp_path, capsys):
    usage = SimpleNamespace(
        prompt_token_count=2,
        candidates_token_count=3,
        total_token_count=5,
    )
    chat = FakeChat(
        [
            fake_response("回答1", usage),
            fake_response("回答2", usage),
        ]
    )
    client, _ = run_chat(
        monkeypatch,
        tmp_path,
        iter(["質問1", "質問2", "/exit"]),
        chat,
    )

    assert client.chats.created_models == [ask_module.MODEL]
    assert chat.questions == ["質問1", "質問2"]
    output = capsys.readouterr().out
    assert output.count("[tokens] input=2 output=3 total=5") == 2
    assert "回答1" in output
    assert "回答2" in output


def test_empty_input_does_not_send_message(monkeypatch, tmp_path):
    chat = FakeChat([])
    run_chat(monkeypatch, tmp_path, iter(["", "   ", "/exit"]), chat)
    assert chat.questions == []


def test_exit_command_ends_chat(monkeypatch, tmp_path):
    chat = FakeChat([])
    run_chat(monkeypatch, tmp_path, iter(["/exit", "送られない質問"]), chat)
    assert chat.questions == []


def test_chat_does_not_save_api_key_or_response(monkeypatch, tmp_path):
    api_key = "test-api-key-must-not-be-saved"
    answer = "回答本文もファイルへ保存しない"
    chat = FakeChat([fake_response(answer)])
    run_chat(monkeypatch, tmp_path, iter(["質問", "/quit"]), chat)

    files = [path for path in tmp_path.rglob("*") if path.is_file()]
    assert files == []
    assert api_key not in "\n".join(path.read_text() for path in files)
    assert answer not in "\n".join(path.read_text() for path in files)


def test_api_error_is_reported_and_chat_continues(monkeypatch, tmp_path, capsys):
    error_messages = []
    monkeypatch.setattr(
        ask_module,
        "api_error_message",
        lambda code, message: error_messages.append((code, message))
        or f"API error {code}",
    )

    class RecoveringChat(FakeChat):
        def send_message(self, question):
            self.questions.append(question)
            if question == "失敗する質問":
                raise ask_module.errors.APIError(
                    code=503,
                    response_json={"error": {"message": "一時的なエラー"}},
                )
            return fake_response("次の回答")

    chat = RecoveringChat([])
    run_chat(
        monkeypatch,
        tmp_path,
        iter(["失敗する質問", "次の質問", "/exit"]),
        chat,
    )

    assert chat.questions == ["失敗する質問", "次の質問"]
    assert error_messages == [(503, "一時的なエラー")]
    output = capsys.readouterr().out
    assert "API error 503" in output
    assert "次の回答" in output


def test_single_question_mode_displays_tokens_and_answer(monkeypatch, capsys):
    usage = SimpleNamespace(
        prompt_token_count=None,
        candidates_token_count=4,
        total_token_count=None,
    )

    class FakeModels:
        def generate_content(self, *, model, contents):
            assert model == ask_module.MODEL
            assert contents == "単発質問"
            return fake_response("単発回答", usage)

    class SingleClient:
        models = FakeModels()

    monkeypatch.setattr(ask_module, "get_api_key", lambda: "test-key")
    monkeypatch.setattr(
        ask_module.genai,
        "Client",
        lambda *, api_key: SingleClient(),
    )

    assert ask_module.ask("単発質問") == "単発回答"
    output = capsys.readouterr().out
    assert "[tokens] input=None output=4 total=None" in output
