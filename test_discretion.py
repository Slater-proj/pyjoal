#!/usr/bin/env python3
"""
Simple test script to validate discretion improvements
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

def test_imports():
    """Test that all modules can be imported successfully"""
    try:
        from app.core.config import settings
        from app.core.tracker_announcer import TrackerAnnouncer
        from app.services.seeder_service import SeederService
        from app.models.schemas import ConfigSchema
        print("✅ All core modules imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def test_config_schema():
    """Test that config schema accepts discretion settings"""
    try:
        from app.models.schemas import ConfigSchema
        
        config_data = {
            "minUploadRate": 30,
            "maxUploadRate": 160,
            "simultaneousSeed": 20,
            "client": "qbittorrent-4.6.0.client",
            "keepTorrentWithZeroLeechers": True,
            "uploadRatioTarget": -1.0,
            "seedingDurationLimit": -1.0,
            "announceInterval": 45,
            "announceJitter": 25,
            "minStatsUpdateInterval": 5,
            "enableSpeedVariation": True,
            "speedVariationPercent": 15
        }
        
        config = ConfigSchema(**config_data)
        assert config.announceInterval == 45
        assert config.announceJitter == 25
        assert config.enableSpeedVariation == True
        print("✅ Config schema accepts discretion settings")
        return True
    except Exception as e:
        print(f"❌ Config schema test failed: {e}")
        return False

def test_settings_values():
    """Test that settings have reasonable defaults for discretion"""
    try:
        from app.core.config import settings
        
        assert hasattr(settings, 'ANNOUNCE_INTERVAL')
        assert hasattr(settings, 'ANNOUNCE_JITTER')
        assert hasattr(settings, 'MIN_STATS_UPDATE_INTERVAL')
        assert hasattr(settings, 'ENABLE_SPEED_VARIATION')
        assert hasattr(settings, 'SPEED_VARIATION_PERCENT')
        
        assert settings.ANNOUNCE_INTERVAL >= 15
        assert settings.ANNOUNCE_JITTER >= 0
        assert 1 <= settings.MIN_STATS_UPDATE_INTERVAL <= 30
        
        print("✅ Settings have proper discretion defaults")
        print(f"   Announce interval: {settings.ANNOUNCE_INTERVAL}s")
        print(f"   Announce jitter: ±{settings.ANNOUNCE_JITTER}s")
        print(f"   Min stats update: {settings.MIN_STATS_UPDATE_INTERVAL}s")
        print(f"   Speed variation: {settings.SPEED_VARIATION_PERCENT}%")
        return True
    except Exception as e:
        print(f"❌ Settings test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Testing PyJOAL discretion improvements...")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_config_schema,
        test_settings_values
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
            print()
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
            print()
    
    print("=" * 50)
    print(f"📊 Tests completed: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 All discretion improvements working correctly!")
        return True
    else:
        print("⚠️ Some tests failed - check the output above")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)