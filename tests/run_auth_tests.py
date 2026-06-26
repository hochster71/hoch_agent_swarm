import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tests.test_release_authorization_gate import (
    test_release_authorization_pending_when_missing,
    test_release_authorization_pending_when_unauthorized,
    test_release_authorization_go_when_authorized
)

def run():
    print("Running release authorization gate tests...")
    try:
        test_release_authorization_pending_when_missing()
        print(" [PASS] test_release_authorization_pending_when_missing")
        
        test_release_authorization_pending_when_unauthorized()
        print(" [PASS] test_release_authorization_pending_when_unauthorized")
        
        test_release_authorization_go_when_authorized()
        print(" [PASS] test_release_authorization_go_when_authorized")
        
        print("\nALL TESTS PASSED SUCCESSFULLY!")
        sys.exit(0)
    except AssertionError as e:
        print(f" [FAIL] Test assertion failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f" [ERROR] Test execution error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run()
