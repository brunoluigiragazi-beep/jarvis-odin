from unittest.mock import MagicMock

import pytest

from app.memory.supabase_memory import OdinMemory


@pytest.fixture
def memory():
    instance = OdinMemory.__new__(OdinMemory)
    instance.client = MagicMock()

    tables = {
        "odin_conversations": MagicMock(),
        "odin_messages": MagicMock()
    }

    instance.client.table.side_effect = lambda name: tables[name]

    return instance, tables


def test_get_or_create_conversation_creates_new(memory):
    instance, tables = memory
    table = tables["odin_conversations"]

    table.select.return_value = table
    table.eq.return_value = table
    table.limit.return_value = table
    table.execute.return_value.data = []
    table.insert.return_value.execute.return_value.data = [
        {"id": "conversation-1"}
    ]

    result = instance.get_or_create_conversation(
        thread_id="teste-001",
        title="Teste ODIN"
    )

    assert result == "conversation-1"

    table.insert.assert_called_once_with({
        "thread_id": "teste-001",
        "status": "active",
        "title": "Teste ODIN"
    })


def test_get_or_create_conversation_reuses_existing(memory):
    instance, tables = memory
    table = tables["odin_conversations"]

    table.select.return_value = table
    table.eq.return_value = table
    table.limit.return_value = table
    table.execute.return_value.data = [
        {"id": "conversation-existing"}
    ]

    result = instance.get_or_create_conversation(
        thread_id="teste-001"
    )

    assert result == "conversation-existing"
    table.insert.assert_not_called()


def test_save_message_success(memory):
    instance, tables = memory
    conversations = tables["odin_conversations"]
    messages = tables["odin_messages"]

    conversations.select.return_value = conversations
    conversations.eq.return_value = conversations
    conversations.limit.return_value = conversations
    conversations.execute.return_value.data = [
        {"id": "conversation-1"}
    ]

    expected = [{"id": "message-1", "role": "user"}]
    messages.insert.return_value.execute.return_value.data = expected

    result = instance.save_message(
        thread_id="teste-001",
        role="user",
        content="Olá ODIN"
    )

    assert result == expected

    messages.insert.assert_called_once_with({
        "conversation_id": "conversation-1",
        "role": "user",
        "content": "Olá ODIN",
        "metadata": {}
    })


def test_get_messages_returns_chronological_order(memory):
    instance, tables = memory
    conversations = tables["odin_conversations"]
    messages = tables["odin_messages"]

    conversations.select.return_value = conversations
    conversations.eq.return_value = conversations
    conversations.limit.return_value = conversations
    conversations.execute.return_value.data = [
        {"id": "conversation-1"}
    ]

    messages.select.return_value = messages
    messages.eq.return_value = messages
    messages.order.return_value = messages
    messages.limit.return_value = messages

    messages.execute.return_value.data = [
        {"id": "message-2", "role": "assistant"},
        {"id": "message-1", "role": "user"}
    ]

    result = instance.get_messages(
        thread_id="teste-001",
        limit=10
    )

    assert [message["id"] for message in result] == [
        "message-1",
        "message-2"
    ]


def test_save_message_rejects_invalid_role(memory):
    instance, tables = memory

    with pytest.raises(ValueError):
        instance.save_message(
            thread_id="teste-001",
            role="system",
            content="Teste"
        )

    instance.client.table.assert_not_called()
