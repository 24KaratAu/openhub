#!/usr/bin/env python
import os
import sys
import subprocess

SCRIPTS = [
    "test_core.py"
]

TESTS_DIR = os.path.join(os.path.dirname(__file__), "tests")

def main():
    print("=" * 60)
    print("      OPENHUB TUI - INTEGRATION TEST SUITE")
    print("=" * 60)
    
    failed = []
    
    # Ensure database is clean at start
    db_path = os.path.expanduser("~/.cache/opencode-hub/repos.db")
    if os.path.exists(db_path):
        os.remove(db_path)
        print("Cleared database cache.")
        
    for script in SCRIPTS:
        path = os.path.join(TESTS_DIR, script)
        print(f"\nRunning {script}...")
        print("-" * 40)
        
        try:
            res = subprocess.run([sys.executable, path], check=True, text=True)
            print(f"[PASSED] {script}")
        except subprocess.CalledProcessError:
            print(f"[FAILED] {script}")
            failed.append(script)
            
    print("\n" + "=" * 60)
    if failed:
        print(f"[FAIL] TEST SUITE FAILED. Failed scripts: {', '.join(failed)}")
        sys.exit(1)
    else:
        print("[SUCCESS] All integration tests passed successfully.")
        sys.exit(0)

if __name__ == "__main__":
    main()
