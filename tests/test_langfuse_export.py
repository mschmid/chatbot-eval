from __future__ import annotations

from types import SimpleNamespace

from scenarios.export_langfuse import export_scenario_traces


class FakeTraceApi:
    def __init__(self) -> None:
        self.summaries = [
            SimpleNamespace(id="t1", metadata={"cartwheel.scenario_id": "support-1"}),
            SimpleNamespace(id="noise", metadata={}),
            SimpleNamespace(id="t2", metadata={"cartwheel.scenario_id": "support-2"}),
        ]

    def list(self, *, page: int, limit: int):
        start = (page - 1) * limit
        return SimpleNamespace(data=self.summaries[start : start + limit])

    def get(self, trace_id: str):
        if trace_id == "t2":
            return {
                "id": trace_id,
                "observations": [
                    {"metadata": {"cartwheel.scenario_id": "support-2"}}
                ],
            }
        return {"id": trace_id, "observations": []}


def test_export_filters_and_paginates_scenario_traces() -> None:
    client = SimpleNamespace(api=SimpleNamespace(trace=FakeTraceApi()))
    client.api.trace.summaries[2].metadata = {}
    records = export_scenario_traces({"support-1", "support-2"}, client, page_size=2)
    assert [record["id"] for record in records] == ["t1", "t2"]
    assert [record["cartwheel_scenario_id"] for record in records] == [
        "support-1",
        "support-2",
    ]
