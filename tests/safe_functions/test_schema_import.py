from fortress_director.core.functions import function_schema as fs


def test_schema_dataclasses_present():
    assert hasattr(fs, "FunctionParam")
    assert hasattr(fs, "SafeFunctionMeta")
