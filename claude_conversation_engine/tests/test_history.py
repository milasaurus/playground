from claude_conversation_engine.api.history import HistoryHandler, USER_ROLE, ASSISTANT_ROLE


def test_add_stores_message():
    history = HistoryHandler()
    history.add(USER_ROLE, "Hello")

    assert history.get_messages() == [
        {"role": USER_ROLE, "content": "Hello"}
    ]


def test_get_messages_returns_copy():
    history = HistoryHandler()
    history.add(USER_ROLE, "Hello")

    messages = history.get_messages()
    messages.clear()

    assert len(history.get_messages()) == 1


def test_clear_removes_all_messages():
    history = HistoryHandler()
    history.add(USER_ROLE, "Hello")
    history.add(ASSISTANT_ROLE, "Hi there!")
    history.clear()

    assert history.get_messages() == []


def test_multi_turn_history():
    history = HistoryHandler()
    history.add(USER_ROLE, "What is Python?")
    history.add(ASSISTANT_ROLE, "A programming language.")
    history.add(USER_ROLE, "What is it used for?")
    history.add(ASSISTANT_ROLE, "Web dev, data science, and more.")

    assert len(history.get_messages()) == 4
    assert history.get_messages()[0]["role"] == USER_ROLE
    assert history.get_messages()[1]["role"] == ASSISTANT_ROLE
