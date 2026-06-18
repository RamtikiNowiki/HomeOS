"""Tests for host health metrics."""

from app.system.health import get_host_health


def test_host_health_shape():
    data = get_host_health()
    assert "available" in data
    assert "cpu_temp_c" in data
    assert "memory" in data
    assert "disk" in data
    assert "docker" in data
    assert isinstance(data["docker"]["services"], list)
