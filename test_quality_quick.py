"""Quick smoke test for quality_checker — run from project root."""
import sys
import os

# Ensure imports work
sys.path.insert(0, os.getcwd())

from backend.services.quality_checker import check_quality

# Test 1: Non-existent file (should return rejected gracefully)
print("=" * 60)
print("TEST 1: Non-existent file")
result = check_quality("does_not_exist.jpg")
print(f"  Status   : {result.status}")
print(f"  Score    : {result.overall_score}")
print(f"  Issues   : {result.issues}")
print(f"  Feedback : {result.feedback}")
print()

# Test 2: If you have a sample image, put it in test_data/ and update the path
sample = "test_data/LANDDEED2.jpg"
if os.path.exists(sample):
    print("=" * 60)
    print(f"TEST 2: Real image — {sample}")
    result = check_quality(sample)
    print(f"  Status          : {result.status}")
    print(f"  Overall Score   : {result.overall_score}")
    print(f"  Blur (Lap var)  : {result.blur_score}")
    print(f"  Brightness      : {result.brightness_value} ({result.brightness_status})")
    print(f"  Angle           : {result.angle_degrees}° ({result.angle_status})")
    print(f"  Issues          : {result.issues}")
    print(f"  Feedback (en)   : {result.feedback.get('en')}")
    print(f"  Feedback (hi)   : {result.feedback.get('hi')}")
    print(f"  Processing time : {result.processing_time}s")
else:
    print(f"(Skipping Test 2 — no sample image at {sample})")
    print("  → Drop any document photo into test_data/sample_passbook.jpg and re-run")

print()
print("✅ Quality checker is working!")