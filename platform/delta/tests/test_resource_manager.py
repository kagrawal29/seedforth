from types import SimpleNamespace

from delta.resource_manager import should_auto_hibernate


def test_retained_active_products_are_not_auto_hibernated():
    assert should_auto_hibernate(SimpleNamespace(status="active", project_type="standard"))
    assert not should_auto_hibernate(SimpleNamespace(status="active", project_type="product"))
    assert not should_auto_hibernate(SimpleNamespace(status="active", project_type="persistent"))
    assert not should_auto_hibernate(SimpleNamespace(status="hibernated", project_type="standard"))
