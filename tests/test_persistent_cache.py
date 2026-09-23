"""Advisory cache tests; all providers are explicit fixtures, never live Jev."""
import json

import pytest

from jev_sm.judgment import DecisionEngine, Question
from jev_sm.store import Store
from conftest import new_task, plan, rev, settings_update
from test_judgment import FixtureBackend, Q


def engine(core, backend=None):
    return DecisionEngine(core.workspace, Store(core.store.path), backend or FixtureBackend())


def test_persists_across_new_engine_and_store(core):
    task = new_task(core)
    first = engine(core).judge(task, "cache-test", {"text": "example"}, Q)
    spy = FixtureBackend()
    second = engine(core, spy).judge(task, "cache-test", {"text": "example"}, Q)
    assert first["status"] == "available"
    assert second["cached"] and second["cache_source"] == "sqlite" and spy.calls == []
    assert second["usage"] == {"input_tokens": 0, "output_tokens": 0}
    assert second["backend_calls"] == 0 and second["http_attempts"] == 0
    assert second["cost_usd"] == 0 and second["request_id"] is None
    assert second["source_request_id"] == "fixture"
    assert len(core.store.decisions(task)) == 2


def test_expiry_forces_new_judgment(core, monkeypatch):
    task = new_task(core)
    monkeypatch.setattr("jev_sm.store.time.time", lambda: 100.0)
    engine(core).judge(task, "cache-test", {}, Q)
    monkeypatch.setattr("jev_sm.store.time.time", lambda: 100.0 + 86401)
    spy = FixtureBackend()
    assert not engine(core, spy).judge(task, "cache-test", {}, Q)["cached"]
    assert len(spy.calls) == 1


@pytest.mark.parametrize("change", [
    {"jev_model": "jev-1.13.1"}, {"jev_max_payload_chars": 25000},
    {"jev_cache_ttl_seconds": 300}, {"jev_enabled": True}])
def test_configuration_change_is_not_a_cache_hit(core, change):
    task = new_task(core)
    engine(core).judge(task, "cache-test", {}, Q)
    settings_update(core, **change)
    assert not engine(core).judge(task, "cache-test", {}, Q)["cached"]


def test_question_version_change_invalidates(core, monkeypatch):
    task = new_task(core)
    engine(core).judge(task, "cache-test", {}, Q)
    monkeypatch.setattr("jev_sm.judgment.QUESTION_VERSION", "future-test-version")
    assert not engine(core).judge(task, "cache-test", {}, Q)["cached"]


def test_task_and_contract_scope(core):
    task = new_task(core)
    engine(core).judge(task, "cache-test", {}, Q)
    second = new_task(core)
    assert not engine(core).judge(second, "cache-test", {}, Q)["cached"]
    core.submit_plan(task, plan(title="A changed contract"), rev(core, task), "new-contract")
    assert not engine(core).judge(task, "cache-test", {}, Q)["cached"]


def test_purpose_and_original_input_separate_cache_keys(core, monkeypatch):
    monkeypatch.setenv("FIRST_API_KEY", "secret-one-123")
    monkeypatch.setenv("SECOND_API_KEY", "secret-two-456")
    task = new_task(core)
    spy = FixtureBackend()
    item = engine(core, spy)
    item.judge(task, "purpose-one", {"text": "secret-one-123"}, Q)
    item.judge(task, "purpose-one", {"text": "secret-two-456"}, Q)
    item.judge(task, "purpose-two", {"text": "secret-two-456"}, Q)
    assert len(spy.calls) == 3
    assert spy.calls[0][0] == spy.calls[1][0]  # Redacted inputs equal, originals differ.
    with core.store.connect() as con:
        rows = " ".join(row[0] for row in con.execute("SELECT data FROM judgment_cache"))
    assert "secret-one" not in rows and "secret-two" not in rows


@pytest.mark.parametrize("model", ["jev-latest", "jev", "jev-1", "jev-preview"])
def test_mutable_aliases_are_not_cached(core, model):
    settings_update(core, jev_model=model)
    task = new_task(core)
    spy = FixtureBackend()
    for _ in range(2):
        assert not engine(core, spy).judge(task, "cache-test", {}, Q)["cached"]
    assert len(spy.calls) == 2 and core.store.cache_stats()["entries"] == 0


@pytest.mark.parametrize("setting", [{"jev_cache_ttl_seconds": 0}, {"jev_cache_max_entries": 0}])
def test_caching_can_be_disabled(core, setting):
    settings_update(core, **setting)
    task = new_task(core)
    for _ in range(2):
        assert not engine(core).judge(task, "cache-test", {}, Q)["cached"]
    assert core.store.cache_stats()["entries"] == 0


def test_failed_judgments_never_cached(core):
    task = new_task(core)
    class Broken(FixtureBackend):
        def evaluate(self, state, questions):
            raise RuntimeError("do not persist this input")
    assert engine(core, Broken()).judge(task, "cache-test", {}, Q)["status"] == "unavailable"
    assert core.store.cache_stats()["entries"] == 0
    assert engine(core).judge(task, "cache-test", {}, Q)["status"] == "available"


def test_disabling_provider_cannot_reuse_an_old_answer(core):
    class NamedFixture(FixtureBackend):
        name = "typesafe"
    settings_update(core, jev_enabled=True)
    task = new_task(core)
    engine(core, NamedFixture()).judge(task, "cache-test", {}, Q)
    settings_update(core, jev_enabled=False)
    spy = NamedFixture()
    result = engine(core, spy).judge(task, "cache-test", {}, Q)
    assert result["error"] == "JUDGMENT_DISABLED" and not spy.calls


def test_cache_size_bounded_and_clear_preserves_audit(core):
    settings_update(core, jev_cache_max_entries=2)
    task = new_task(core)
    for i in range(5):
        engine(core).judge(task, "cache-test", {"i": i}, Q)
    assert core.store.cache_stats()["entries"] == 2
    assert core.store.clear_judgment_cache()["deleted_entries"] == 2
    assert len(core.store.decisions(task)) == 5 and core.store.get(task)


@pytest.mark.parametrize("corrupt", ["not json", "[]", '{"status":"available"}'])
def test_corrupt_cache_entry_is_a_miss_not_a_result(core, corrupt):
    task = new_task(core)
    engine(core).judge(task, "cache-test", {}, Q)
    with core.store.connect() as con:
        con.execute("UPDATE judgment_cache SET data=?", (corrupt,))
    assert not engine(core).judge(task, "cache-test", {}, Q)["cached"]


def test_cache_hit_does_not_consume_backend_budget(core):
    settings_update(core, jev_max_calls_per_task=1)
    task = new_task(core)
    engine(core).judge(task, "cache-test", {}, Q)
    assert engine(core).judge(task, "cache-test", {}, Q)["cached"]
    result = engine(core).judge(task, "cache-test", {"changed": True}, Q)
    assert result["error"] == "JUDGMENT_BUDGET_EXCEEDED"
    assert not core.gate(task)["eligible"]


def test_backend_namespace_does_not_collide(core):
    settings_update(core, jev_enabled=True)
    task = new_task(core)
    engine(core).judge(task, "cache-test", {}, Q)
    class Other(FixtureBackend):
        name = "another-fixture"
    assert not engine(core, Other()).judge(task, "cache-test", {}, Q)["cached"]


def test_database_upgrade_keeps_preexisting_tasks(core):
    task = new_task(core)
    with core.store.connect() as con:
        con.execute("DROP TABLE judgment_cache")
    upgraded = Store(core.store.path)
    assert upgraded.get(task)["id"] == task
    assert upgraded.cache_stats()["entries"] == 0


def test_cache_survives_actual_os_process_exit(core, tmp_path):
    import os
    import subprocess
    import sys
    from pathlib import Path
    task = new_task(core)
    marker = tmp_path / "fixture-provider-calls.txt"
    script = '''import json,sys
from pathlib import Path
from jev_sm.core import Core
from jev_sm.workspace import Workspace
from jev_sm.judgment import DecisionEngine,Question
class ExplicitTestFixture:
    name='test-fixture'
    def evaluate(self,state,questions):
        with Path(sys.argv[4]).open('a') as output: output.write('fixture-call\\n')
        return {'answers':{'yes':{'noul':0.9}},'request_id':'fixture-only','usage':{'input_tokens':10,'output_tokens':0}}
core=Core(Workspace(Path(sys.argv[1]),Path(sys.argv[2])))
result=DecisionEngine(core.workspace,core.store,ExplicitTestFixture()).judge(sys.argv[3],'process-test',{'input':'bounded fixture'},{'yes':Question('noul','Is this a fixture?')})
print(json.dumps(result))
'''
    command = [sys.executable, "-c", script, str(core.workspace.root),
               str(core.workspace.state_dir.parent), task, str(marker)]
    env = {**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")}
    one = json.loads(subprocess.run(command, check=True, capture_output=True, text=True, env=env, timeout=10).stdout)
    two = json.loads(subprocess.run(command, check=True, capture_output=True, text=True, env=env, timeout=10).stdout)
    assert not one["cached"] and two["cached"]
    assert marker.read_text() == "fixture-call\n"
