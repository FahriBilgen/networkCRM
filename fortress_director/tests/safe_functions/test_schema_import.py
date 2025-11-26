from __future__ import annotations

from fortress_director.core.functions.function_schema import FunctionParam, SafeFunctionMeta


def test_schema_dataclasses_initialize() -> None:
    param = FunctionParam(name="intensity", type="int", required=False)
    meta = SafeFunctionMeta(
        name="demo_function",
        category="combat",
        description="Demo entry",
        params=[param],
        gas_cost=2,
    )
    assert meta.name == "demo_function"
    assert meta.params[0].required is False
    assert "intensity" in meta.signature()
