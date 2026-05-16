import json

from safeclaw.sessions import (
    edit_memory,
    forget_memory,
    list_memory,
    memory_json_path,
    memory_path,
    recall,
    remember,
    reset_session,
    search_memory,
)


def test_remember_rejects_blank_notes():
    assert remember("blank-memory", "   ") == "No memory note provided."
    assert list_memory("blank-memory") == []
    assert recall("blank-memory") == "No memory saved for this session."


def test_memory_entries_increment_ids_and_trim_notes():
    session = "id-memory"

    assert remember(session, " first note ") == "Memory saved as #1."
    assert remember(session, "second note") == "Memory saved as #2."

    entries = list_memory(session)
    assert [entry["id"] for entry in entries] == [1, 2]
    assert entries[0]["note"] == "first note"
    assert entries[1]["note"] == "second note"
    assert entries[0]["created_at"]
    assert entries[0]["updated_at"] is None


def test_recall_formats_updated_memory():
    session = "recall-updated-memory"
    remember(session, "old note")
    assert edit_memory(session, 1, "new note") == "Updated memory #1."

    output = recall(session)

    assert "#1" in output
    assert "updated" in output
    assert "new note" in output


def test_search_memory_is_case_insensitive_and_reports_miss():
    session = "search-memory"
    remember(session, "Blue Config")
    remember(session, "green setting")

    assert "Blue Config" in search_memory(session, "blue")
    assert "green setting" in search_memory(session, "GREEN")
    assert search_memory(session, "missing") == "No matching memory found."


def test_forget_memory_by_id_text_empty_and_missing_target():
    session = "forget-memory"
    remember(session, "alpha item")
    remember(session, "beta item")
    remember(session, "beta second item")

    assert forget_memory(session, "") == "No memory id or search text provided."
    assert forget_memory(session, "999") == "No matching memory found."
    assert forget_memory(session, "1") == "Forgot 1 memory item(s)."
    assert "alpha item" not in recall(session)

    assert forget_memory(session, "beta") == "Forgot 2 memory item(s)."
    assert recall(session) == "No memory saved for this session."


def test_forget_memory_with_no_saved_memory():
    assert forget_memory("missing-memory", "anything") == "No memory saved for this session."


def test_edit_memory_missing_id_does_not_create_memory():
    session = "edit-missing-memory"

    assert edit_memory(session, 42, "new note") == "Memory #42 not found."
    assert list_memory(session) == []


def test_legacy_markdown_memory_migrates_to_json():
    session = "legacy-memory"
    legacy_path = memory_path(session)
    legacy_path.write_text("- 2026-01-01T00:00:00: old one\n\n- old two\n")

    entries = list_memory(session)

    assert [entry["id"] for entry in entries] == [1, 3]
    assert entries[0]["created_at"] == "legacy"
    assert entries[0]["note"] == "2026-01-01T00:00:00: old one"
    assert entries[1]["note"] == "old two"
    assert memory_json_path(session).exists()


def test_json_memory_takes_precedence_over_legacy_markdown():
    session = "json-before-legacy-memory"
    memory_path(session).write_text("- legacy note\n")
    memory_json_path(session).write_text(json.dumps([{"id": 7, "created_at": "now", "updated_at": None, "note": "json note"}]))

    entries = list_memory(session)

    assert len(entries) == 1
    assert entries[0]["id"] == 7
    assert entries[0]["note"] == "json note"


def test_invalid_json_memory_shape_returns_empty_list():
    session = "invalid-json-memory"
    memory_json_path(session).write_text(json.dumps({"note": "not a list"}))

    assert list_memory(session) == []
    assert recall(session) == "No memory saved for this session."


def test_reset_session_removes_json_and_legacy_memory_files():
    session = "reset-memory"
    memory_path(session).write_text("- legacy note\n")
    remember(session, "json note")

    assert memory_path(session).exists()
    assert memory_json_path(session).exists()

    reset_session(session)

    assert not memory_path(session).exists()
    assert not memory_json_path(session).exists()
    assert recall(session) == "No memory saved for this session."
