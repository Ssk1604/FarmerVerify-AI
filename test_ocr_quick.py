# test_ocr_quick.py (temporary — run from project root)
import os
import asyncio
# Set this to your own Google Cloud service-account credentials JSON path.
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.environ.get(
    "GOOGLE_APPLICATION_CREDENTIALS", "path/to/your-credentials.json"
)

from backend.services.ocr_engine import extract_text

# Point to any test image (Hindi passbook scan, Aadhaar photo, etc.)
result = asyncio.run(extract_text("path/to/test_image.jpg"))  # adjust path

print(f"Text ({len(result.raw_text)} chars): {result.raw_text[:300]}")
print(f"Confidence: {result.confidence}")
print(f"Language: {result.language_detected}")
print(f"Time: {result.processing_time}s")