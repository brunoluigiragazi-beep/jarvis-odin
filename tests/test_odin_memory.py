
from unittest.mock import MagicMock

import pytest

from app.memory.supabase_memory import OdinMemory


@pytest.fixture
def memory():
    instance = OdinMemory.__new__(OdinMemory)
    instance.client = MagicMock()

    table = instance.client.table.return_value
    table.select.return_value = table
    table.eq.return_value = table
    table.limit.return_value = table
    table.order.return_value = table

    return instance, table


def test_save_memory_success(memory):
    instance, table = memory

    table.execute.return_value.data = []
    expected = [{"id": "memory-1", "content": "Teste ODIN"}]
    table.insert.return_value.execute.return_value.data = expected

    result = instance.save_memory(
        content="Teste ODIN",
        category="general",
        importance=3
    )

    assert result == expected

    table.insert.assert_called_once_with({
        "content": "Teste ODIN",
        "category": "general",
        "importance": 3,
        "source": "jarvis",
        "is_active": True
    })


def test_save_memory_returns_existing(memory):
    instance, table = memory

    expected = [{"id": "memory-1", "content": "Teste ODIN"}]
    table.execute.return_value.data = expected

    result = instance.save_memory(
        content="Teste ODIN",
        category="general",
        importance=3
    )

    assert result == expected
    table.insert.assert_not_called()


def test_save_memory_rejects_empty_content(memory):
    instance, table = memory

    with pytest.raises(ValueError):
        instance.save_memory(content="   ")

    instance.client.table.assert_not_called()


def test_save_memory_rejects_invalid_importance(memory):
    instance, table = memory

    with pytest.raises(ValueError):
        instance.save_memory(
            content="Teste",
            importance=6
        )

    instance.client.table.assert_not_called()


def test_save_memory_rejects_invalid_category(memory):
    instance, table = memory

    with pytest.raises(ValueError):
        instance.save_memory(
            content="Teste",
            category="   "
        )

    instance.client.table.assert_not_called()


def test_search_memory_success(memory):
    instance, table = memory

    expected = [{"id": "memory-1", "content": "Teste ODIN"}]
    table.execute.return_value.data = expected

    result = instance.search_memory(
        category="identity",
        limit=5
    )

    assert result == expected
    table.select.assert_called_once_with("*")
    table.eq.assert_any_call("is_active", True)
    table.eq.assert_any_call("category", "identity")
    table.order.assert_called_once_with("created_at", desc=True)
    table.limit.assert_called_with(5)


def test_search_memory_rejects_invalid_limit(memory):
    instance, table = memory

    with pytest.raises(ValueError):
        instance.search_memory(limit=0)

    instance.client.table.assert_not_called()
