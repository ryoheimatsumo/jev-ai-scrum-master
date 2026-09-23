import copy
import math
from types import SimpleNamespace

import pytest

from jev_sm.judgment import Assistant, DecisionEngine, JevBackend, Question
from conftest import new_task, settings_update, start, verify


class FixtureBackend:
    name = "test-fixture"
    def __init__(self, *, choice="UNKNOWN", confidence=0.95, noul=0.9):
        self.choice, self.confidence, self.noul = choice, confidence, noul
        self.calls = []
    def evaluate(self, state, questions):
        self.calls.append((copy.deepcopy(state), questions))
        answers = {}
        for key, q in questions.items():
            if q.kind == "noul":
                answers[key] = {"noul": self.noul}
            else:
                choice = self.choice if self.choice in q.options else q.options[-1]
                answers[key] = {"choice": choice, "confidence": self.confidence,
                                "probabilities": {o: float(o == choice) for o in q.options}}
        return {"answers": answers, "usage": {"input_tokens": 120, "output_tokens": 0},
                "request_id": "fixture", "resolved_model": "fixture-not-a-model"}


Q = {"route": Question("choice", "Which route fits?", ("A", "B", "UNKNOWN"))}


def test_readiness_questions_batched(core):
    task = new_task(core)
    backend = FixtureBackend(choice="NONE")
    result = Assistant(core, backend).readiness(task)
    assert len(backend.calls) == 1 and len(backend.calls[0][1]) == 2
    assert result["is_advisory"]
    assert core.store.get(task)["state"] == "WAITING_USER"


def test_same_input_cached_without_new_backend_call(core):
    task = new_task(core)
    backend = FixtureBackend()
    engine = DecisionEngine(core.workspace, core.store, backend)
    first = engine.judge(task, "test", {"text": "sample"}, Q)
    second = engine.judge(task, "test", {"text": "sample"}, Q)
    assert first["status"] == "available"
    assert second["cached"] and len(backend.calls) == 1
    assert second["backend_calls"] == 0


def test_changed_input_not_cached(core):
    task = new_task(core)
    backend = FixtureBackend()
    engine = DecisionEngine(core.workspace, core.store, backend)
    engine.judge(task, "test", {"text": "one"}, Q)
    engine.judge(task, "test", {"text": "two"}, Q)
    assert len(backend.calls) == 2


def test_changed_question_not_cached(core):
    task = new_task(core)
    backend = FixtureBackend()
    engine = DecisionEngine(core.workspace, core.store, backend)
    engine.judge(task, "test", {}, Q)
    engine.judge(task, "test", {}, {"route": Question("choice", "A different question?", ("A", "B", "UNKNOWN"))})
    assert len(backend.calls) == 2


def test_low_confidence_abstains(core):
    task = new_task(core)
    result = DecisionEngine(core.workspace, core.store, FixtureBackend(choice="A", confidence=0.5)).judge(task, "test", {}, Q)
    assert result["answers"]["route"]["choice"] == "UNKNOWN"
    assert result["answers"]["route"]["raw_choice"] == "A"


@pytest.mark.parametrize("value", [float("nan"), float("inf"), 1.01, -0.01, True])
def test_invalid_numeric_answers_fail_closed(core, value):
    task = new_task(core)
    result = DecisionEngine(core.workspace, core.store, FixtureBackend(confidence=value)).judge(task, "test", {}, Q)
    assert result["status"] == "unavailable" and result["answers"] == {}


def test_disabled_does_not_call_provider(core):
    task = new_task(core)
    class Spy(FixtureBackend):
        name = "typesafe"
    backend = Spy()
    result = DecisionEngine(core.workspace, core.store, backend).judge(task, "test", {}, Q)
    assert not backend.calls
    assert result["error"] == "JUDGMENT_DISABLED"


def test_error_does_not_leak_exception_or_fabricate_success(core):
    task = new_task(core)
    class Broken(FixtureBackend):
        def evaluate(self, state, questions):
            raise RuntimeError("api_key=private-secret-value")
    result = DecisionEngine(core.workspace, core.store, Broken()).judge(task, "test", {}, Q)
    assert result["status"] == "unavailable"
    assert "private-secret-value" not in str(result)
    assert not core.gate(task)["eligible"]


def test_missing_answer_id_rejected(core):
    task = new_task(core)
    class Wrong(FixtureBackend):
        def evaluate(self, state, questions):
            return {"answers": {"different": {"noul": 1}}}
    result = DecisionEngine(core.workspace, core.store, Wrong()).judge(task, "test", {}, Q)
    assert result["status"] == "unavailable"


def test_payload_limit_no_silent_truncation(core):
    settings_update(core, jev_max_payload_chars=1000)
    task = new_task(core)
    backend = FixtureBackend()
    result = DecisionEngine(core.workspace, core.store, backend).judge(task, "test", {"text": "x" * 2000}, Q)
    assert result["error"] == "PAYLOAD_TOO_LARGE" and not backend.calls


def test_call_budget_enforced(core):
    settings_update(core, jev_max_calls_per_task=1)
    task = new_task(core)
    backend = FixtureBackend()
    engine = DecisionEngine(core.workspace, core.store, backend)
    engine.judge(task, "test", {"text": "one"}, Q)
    result = engine.judge(task, "test", {"text": "two"}, Q)
    assert result["error"] == "JUDGMENT_BUDGET_EXCEEDED"
    assert len(backend.calls) == 1


def test_masking_happens_before_transmission(core, monkeypatch):
    monkeypatch.setenv("EXAMPLE_API_KEY", "testsecret123456")
    task = new_task(core)
    backend = FixtureBackend()
    DecisionEngine(core.workspace, core.store, backend).judge(task, "test", {"text": "key testsecret123456"}, Q)
    assert "testsecret123456" not in str(backend.calls[0][0])


def test_context_retains_mandatory_even_when_irrelevant(core):
    task = new_task(core)
    backend = FixtureBackend(noul=0.01)
    result = Assistant(core, backend).select_context(task, "saving", [
        {"id": "a", "text": "required acceptance condition", "mandatory": True},
        {"id": "b", "text": "unrelated decoration"}], max_chars=1)
    assert [s["id"] for s in result["selected"]] == ["a"]
    assert result["parked_ids"] == ["b"] and result["over_budget"]
    assert not result["truncated"]


def test_context_failure_retains_everything(core):
    task = new_task(core)
    result = Assistant(core).select_context(task, "saving", [
        {"id": "a", "text": "source A"}, {"id": "b", "text": "source B"}])
    assert len(result["selected"]) == 2 and not result["parked_ids"]


def test_duplicate_snippet_ids_rejected(core):
    task = new_task(core)
    with pytest.raises(Exception):
        Assistant(core).select_context(task, "query", [{"id": "same", "text": "x"}, {"id": "same", "text": "y"}])


def test_playbook_is_advice_not_execution(core):
    task = new_task(core)
    result = Assistant(core, FixtureBackend(choice="PERSISTENCE")).recommend_playbook(task, "Reload loses a value")
    assert result["playbook"] == "PERSISTENCE"
    assert not result["executed"]
    assert not core.store.get(task)["jobs"]


def test_evidence_mapping_cannot_grant_pass(core):
    task = start(core)
    verify(core, task)
    result = Assistant(core, FixtureBackend(choice="DIRECT_CANDIDATE")).map_evidence(task)
    assert result["status"] == "available"
    assert core.gate(task)["criteria"]["AC-1"] == "NEEDS_REVIEW"


def test_official_sdk_adapter_contract_without_network():
    class Client:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def system_one(self, *, state, questions):
            assert questions["route"]["type"] == "choice"
            assert "A" in questions["route"]["criteria"]
            return SimpleNamespace(choices={"route": SimpleNamespace(
                choice="A", confidence=0.9, probabilities={"A": 1.0, "B": 0.0, "UNKNOWN": 0.0})},
                nouls={}, request_id="local-contract-test", model="fixture", usage={"input_tokens": 12})
    result = JevBackend("jev-1.13.0", client_factory=Client).evaluate({"input": "fixture"}, Q)
    assert result["answers"]["route"]["choice"] == "A"
    assert result["usage"]["input_tokens"] == 12
