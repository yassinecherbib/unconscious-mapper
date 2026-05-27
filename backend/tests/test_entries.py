import asyncio
import unittest
from types import SimpleNamespace

from fastapi import BackgroundTasks

from app.api.entries import (
    AmplifyBody,
    EntryCreate,
    _clean_personal_associations,
    amplify_entry,
    create_entry,
)
import app.api.entries as entries_module


class _Result:
    def __init__(self, data):
        self.data = data


class _EntriesTable:
    def __init__(self, entry):
        self.entry = entry
        self.operations = []

    def select(self, *args):
        self.operations.append(("select", args))
        return self

    def eq(self, *args):
        self.operations.append(("eq", args))
        return self

    def maybe_single(self):
        self.operations.append(("maybe_single", ()))
        return self

    def execute(self):
        self.operations.append(("execute", ()))
        return _Result(self.entry)


class _Db:
    def __init__(self, entry):
        self.entries_table = _EntriesTable(entry)
        self.table_calls = []
        self.rpc_calls = []

    def table(self, name):
        self.table_calls.append(name)
        if name != "entries":
            raise AssertionError(f"unexpected table call: {name}")
        return self.entries_table

    def rpc(self, *args):
        self.rpc_calls.append(args)
        raise AssertionError("idempotent amplify should not call rpc")


class _CreateEntriesTable:
    def insert(self, payload):
        self.payload = payload
        return self

    def execute(self):
        return _Result([{"id": "entry-1", **self.payload}])


class _PersonalSymbolsTable:
    def select(self, *args):
        return self

    def eq(self, *args):
        return self

    def execute(self):
        return _Result([])


class _CreateDb:
    def __init__(self):
        self.entries = _CreateEntriesTable()
        self.personal_symbols = _PersonalSymbolsTable()

    def table(self, name):
        if name == "entries":
            return self.entries
        if name == "personal_symbols":
            return self.personal_symbols
        raise AssertionError(f"unexpected table call: {name}")


class EntryRouteTests(unittest.TestCase):
    def test_clean_personal_associations_drops_blank_answers(self):
        self.assertEqual(
            _clean_personal_associations({
                " one male ": " disappointed ",
                "one female": " ",
                "": "ignored",
            }),
            {"one male": "disappointed"},
        )

    def test_amplify_returns_existing_successful_analysis_without_side_effects(self):
        entry = {
            "id": "entry-1",
            "user_id": "user-1",
            "raw_text": "dream text",
            "entry_type": "dream",
            "analysis": {"jungian_summary": "already complete"},
            "created_at": "2026-05-26T00:00:00Z",
        }
        db = _Db(entry)
        body = AmplifyBody(entry_id="entry-1", personal_associations={"symbol": "meaning"})

        result = asyncio.run(
            amplify_entry(
                body,
                BackgroundTasks(),
                user=SimpleNamespace(id="user-1"),
                db=db,
            )
        )

        self.assertEqual(result, entry)
        self.assertEqual(db.table_calls, ["entries"])
        self.assertEqual(db.rpc_calls, [])

    def test_create_entry_returns_entry_id_when_amplification_fails(self):
        async def failing_amplification(*args, **kwargs):
            raise RuntimeError("model unavailable")

        original = entries_module.get_amplification_questions
        entries_module.get_amplification_questions = failing_amplification
        try:
            result = asyncio.run(
                create_entry(
                    EntryCreate(raw_text="dream text", entry_type="dream"),
                    user=SimpleNamespace(id="user-create-fallback"),
                    db=_CreateDb(),
                )
            )
        finally:
            entries_module.get_amplification_questions = original

        self.assertEqual(result, {"entry_id": "entry-1", "amplification_questions": []})


if __name__ == "__main__":
    unittest.main()
