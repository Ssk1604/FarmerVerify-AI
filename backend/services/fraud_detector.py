# backend/services/fraud_detector.py

from __future__ import annotations

import io
import os
import time
from pathlib import Path
from typing import Union

import cv2
import numpy as np
from loguru import logger
from PIL import Image

from backend.models.validation_result import FraudResult

try:
    import imagehash
    HAS_IMAGEHASH = True
except ImportError:
    HAS_IMAGEHASH = False

# ELA constants
_ELA_QUALITY = 90
_ELA_MEAN_THRESHOLD = 40.0
_ELA_STD_THRESHOLD = 50.0
_DUPLICATE_HASH_THRESHOLD = 5
_MIN_FILE_KB = 10
_MAX_FILE_MB = 15

# Session-level hash store for duplicate detection
_seen_hashes: list[str] = []


def detect_fraud(image_path: Union[str, Path]) -> FraudResult:
    """
    Run fraud detection on a document image.

    Accepts both str and Path for image_path.
    """
    path = Path(image_path)   # ← always convert to Path
    t0 = time.time()
    flags: list[str] = []
    details: dict = {}
    risk_score = 0.0

    if not path.exists():
        logger.error("Fraud detector: image not found: {}", path)
        return FraudResult(
            risk_score=0.0,
            risk_level="unknown",
            is_suspicious=False,
            flags=["Image file not found"],
            processing_time=round(time.time() - t0, 3),
        )

    # 1. File size check
    size_bytes = os.path.getsize(path)
    size_kb = size_bytes / 1024
    size_mb = size_bytes / (1024 * 1024)

    if size_kb < _MIN_FILE_KB:
        flags.append(f"Suspiciously small file ({size_kb:.1f} KB).")
        risk_score += 10
    if size_mb > _MAX_FILE_MB:
        flags.append(f"Unusually large file ({size_mb:.1f} MB).")
        risk_score += 5

    details["file_size_kb"] = round(size_kb, 1)

    # 2. ELA (Error Level Analysis)
    try:
        ela_mean, ela_std = _run_ela(path)
        details["ela_mean"] = round(ela_mean, 2)
        details["ela_std"] = round(ela_std, 2)

        if ela_mean > _ELA_MEAN_THRESHOLD:
            flags.append(
                f"High ELA mean ({ela_mean:.1f}) — possible re-save or editing."
            )
            risk_score += 20

        if ela_std > _ELA_STD_THRESHOLD:
            flags.append(
                f"High ELA variance ({ela_std:.1f}) — localized editing suspected."
            )
            risk_score += 25
    except Exception as exc:
        logger.warning("ELA failed: {}", exc)

    # 3. Perceptual hash + duplicate check
    if HAS_IMAGEHASH:
        try:
            phash = _compute_phash(path)
            details["perceptual_hash"] = phash
            if phash:
                is_dup, matched = _check_duplicate(phash)
                if is_dup:
                    flags.append(f"Near-duplicate of a previously submitted document.")
                    details["duplicate_of"] = matched
                    risk_score += 35
                else:
                    _seen_hashes.append(phash)
        except Exception as exc:
            logger.warning("Perceptual hash failed: {}", exc)

    # 4. Uniformity analysis
    try:
        uni_flags = _check_uniformity(path)
        flags.extend(uni_flags)
        risk_score += len(uni_flags) * 10
    except Exception as exc:
        logger.warning("Uniformity check failed: {}", exc)

    risk_score = min(round(risk_score, 1), 100.0)

    risk_level = (
        "high" if risk_score >= 60
        else "medium" if risk_score >= 30
        else "low"
    )

    elapsed = round(time.time() - t0, 3)

    result = FraudResult(
        risk_score=risk_score,
        risk_level=risk_level,
        is_suspicious=risk_score >= 40,
        flags=flags,
        details=details,
        processing_time=elapsed,
    )

    logger.info(
        "Fraud detection | risk={} | level={} | flags={} | time={}s",
        risk_score, risk_level, len(flags), elapsed,
    )
    return result


def _run_ela(path: Path) -> tuple[float, float]:
    original = Image.open(path).convert("RGB")
    buf = io.BytesIO()
    original.save(buf, format="JPEG", quality=_ELA_QUALITY)
    buf.seek(0)
    resaved = Image.open(buf).convert("RGB")
    orig_arr = np.array(original, dtype=np.float64)
    resaved_arr = np.array(resaved, dtype=np.float64)
    ela = np.abs(orig_arr - resaved_arr) * 15
    ela = np.clip(ela, 0, 255)
    return float(np.mean(ela)), float(np.std(ela))


def _compute_phash(path: Path) -> str | None:
    if not HAS_IMAGEHASH:
        return None
    try:
        img = Image.open(path)
        return str(imagehash.phash(img))
    except Exception:
        return None


def _check_duplicate(phash: str) -> tuple[bool, str | None]:
    if not HAS_IMAGEHASH or not _seen_hashes:
        return False, None
    try:
        current = imagehash.hex_to_hash(phash)
        for known in _seen_hashes:
            if current - imagehash.hex_to_hash(known) <= _DUPLICATE_HASH_THRESHOLD:
                return True, known
    except Exception:
        pass
    return False, None


def _check_uniformity(path: Path) -> list[str]:
    flags = []
    img = cv2.imread(str(path))
    if img is None:
        return flags
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    variance = float(np.var(gray))
    if variance < 100:
        flags.append(f"Very low image variance ({variance:.1f}) — may be synthetic.")
    return flags