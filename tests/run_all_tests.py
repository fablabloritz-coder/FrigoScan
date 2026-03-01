"""
Runner principal pour tous les tests
"""
import subprocess
import sys
import os
import time

TEST_DIR = os.path.dirname(__file__)
TESTS = [
    ("test_error_exposure.py", "Stack Trace Exposure"),
    ("test_input_validation.py", "Input Validation"),
    ("test_pagination.py", "Pagination"),
    ("test_concurrent_access.py", "Concurrent Access"),
    ("test_transactions.py", "Transaction Atomicity"),
]

def run_tests():
    print("=" * 70)
    print("🧪 FrigoScan Test Suite v2.9.7")
    print("=" * 70)
    
    final_results = []
    
    for test_file, test_name in TESTS:
        print(f"\n🔄 Running: {test_name}...")
        print("-" * 70)
        
        try:
            result = subprocess.run(
                [sys.executable, os.path.join(TEST_DIR, test_file)],
                capture_output=False,
                timeout=60
            )
            
            passed = result.returncode == 0
            final_results.append((test_name, passed))
            
        except subprocess.TimeoutExpired:
            print(f"❌ TIMEOUT: {test_name} took too long")
            final_results.append((test_name, False))
        except Exception as e:
            print(f"❌ ERROR: {test_name} - {e}")
            final_results.append((test_name, False))
        
        time.sleep(1)  # Brief pause between tests
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 SUMMARY")
    print("=" * 70)
    
    passed_count = sum(1 for _, p in final_results if p)
    total_count = len(final_results)
    
    for test_name, passed in final_results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\n📈 Total: {passed_count}/{total_count} tests passed")
    
    if passed_count == total_count:
        print("🎉 All tests PASSED! Application is healthy.")
        return 0
    else:
        print(f"⚠️ {total_count - passed_count} test(s) failed.")
        return 1

if __name__ == "__main__":
    sys.exit(run_tests())
