"""
Tests for resource_optimizer module
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from app.services.resource_optimizer import ResourceOptimizer


class TestResourceOptimizerInit:
    """Tests for ResourceOptimizer initialization"""

    def test_init_defaults(self):
        ro = ResourceOptimizer()
        assert ro.last_gc_time is None
        assert ro.memory_threshold_mb == 200
        assert ro.last_memory_check is not None


class TestGetMemoryUsage:
    """Tests for get_memory_usage"""

    def test_returns_dict_with_expected_keys(self):
        ro = ResourceOptimizer()
        result = ro.get_memory_usage()
        assert "rss_mb" in result
        assert "vms_mb" in result
        assert "percent" in result

    def test_rss_is_positive(self):
        ro = ResourceOptimizer()
        result = ro.get_memory_usage()
        assert result["rss_mb"] > 0

    def test_values_are_float(self):
        ro = ResourceOptimizer()
        result = ro.get_memory_usage()
        assert isinstance(result["rss_mb"], float)
        assert isinstance(result["vms_mb"], float)
        assert isinstance(result["percent"], float)


class TestShouldOptimizeMemory:
    """Tests for should_optimize_memory"""

    def test_returns_bool(self):
        ro = ResourceOptimizer()
        result = ro.should_optimize_memory()
        assert isinstance(result, bool)

    def test_low_threshold_triggers_optimization(self):
        ro = ResourceOptimizer()
        ro.memory_threshold_mb = 0  # Will always trigger
        assert ro.should_optimize_memory() is True

    def test_high_threshold_no_optimization(self):
        ro = ResourceOptimizer()
        ro.memory_threshold_mb = 999999  # Will never trigger
        assert ro.should_optimize_memory() is False


@pytest.mark.asyncio
class TestOptimizeMemory:
    """Tests for optimize_memory"""

    async def test_optimize_returns_true(self):
        ro = ResourceOptimizer()
        result = await ro.optimize_memory()
        assert result is True

    async def test_optimize_sets_last_gc_time(self):
        ro = ResourceOptimizer()
        assert ro.last_gc_time is None
        await ro.optimize_memory()
        assert ro.last_gc_time is not None
