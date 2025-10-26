#!/usr/bin/env python3
"""
Version Testing Utility for Employee Scheduler
This script helps test the version comparison logic.
"""

def version_compare(version1, version2):
    """Compare two version strings. Returns 1 if version1 > version2, -1 if version1 < version2, 0 if equal."""
    def version_tuple(v):
        return tuple(map(int, (v.split("."))))
    
    v1_tuple = version_tuple(version1)
    v2_tuple = version_tuple(version2)
    
    if v1_tuple > v2_tuple:
        return 1
    elif v1_tuple < v2_tuple:
        return -1
    else:
        return 0

def test_versions():
    """Test various version comparisons."""
    test_cases = [
        ("1.0.0", "1.0.1", -1),  # 1.0.0 < 1.0.1
        ("1.1.0", "1.0.1", 1),   # 1.1.0 > 1.0.1  
        ("2.0.0", "1.9.9", 1),   # 2.0.0 > 1.9.9
        ("1.2.0", "1.2.0", 0),   # 1.2.0 = 1.2.0
        ("1.10.0", "1.9.0", 1),  # 1.10.0 > 1.9.0 (numeric comparison)
    ]
    
    print("Version Comparison Tests:")
    print("=" * 40)
    
    for v1, v2, expected in test_cases:
        result = version_compare(v1, v2)
        status = "✓" if result == expected else "✗"
        comparison = ">" if result == 1 else "<" if result == -1 else "="
        
        print(f"{status} {v1} {comparison} {v2}")
        
        if result != expected:
            print(f"  Expected: {expected}, Got: {result}")
    
    print()

def check_current_vs_new(current_version, new_version):
    """Check if an update is available."""
    result = version_compare(new_version, current_version)
    
    if result > 0:
        print(f"🔄 UPDATE AVAILABLE: {current_version} → {new_version}")
        return True
    elif result == 0:
        print(f"✅ UP TO DATE: {current_version}")
        return False
    else:
        print(f"⚠️  NEWER VERSION INSTALLED: {current_version} (latest: {new_version})")
        return False

if __name__ == "__main__":
    print("Employee Scheduler - Version Testing Utility")
    print("=" * 50)
    print()
    
    # Run automated tests
    test_versions()
    
    # Interactive testing
    print("Interactive Version Check:")
    print("-" * 30)
    
    current = input("Enter current version (e.g., 1.2.0): ").strip()
    latest = input("Enter latest version (e.g., 1.3.0): ").strip()
    
    print()
    
    try:
        update_available = check_current_vs_new(current, latest)
        
        if update_available:
            print("\n📥 The application would show an update dialog.")
        else:
            print("\n💡 No update notification would be shown.")
            
    except ValueError as e:
        print(f"❌ Invalid version format: {e}")
        print("Please use format: MAJOR.MINOR.PATCH (e.g., 1.2.0)")