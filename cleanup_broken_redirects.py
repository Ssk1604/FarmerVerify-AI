# cleanup_broken_redirects.py — run once: python cleanup_broken_redirects.py

import sys, os, json
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

RESULTS_DIR = Path("results")

def cleanup():
    print("Scanning for broken redirect stubs...")
    removed = 0
    
    for path in RESULTS_DIR.glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        
        if not data.get("is_redirect"):
            continue
        
        original_id = data.get("original_request_id", "")
        if not original_id:
            print(f"  REMOVE (no original_id): {path.name}")
            path.unlink()
            removed += 1
            continue
        
        # Check if the original file exists
        original_path = RESULTS_DIR / f"{original_id}.json"
        if not original_path.exists():
            print(f"  REMOVE (broken redirect {path.stem} → {original_id} which doesn't exist)")
            path.unlink()
            removed += 1
        else:
            print(f"  OK: {path.stem} → {original_id}")
    
    print(f"\nDone. Removed {removed} broken redirect stubs.")

if __name__ == "__main__":
    cleanup()