# backend/services/quality_checker.py

from __future__ import annotations

import cv2
import numpy as np
from pathlib import Path
from loguru import logger

from backend.utils.constants import (
    BLUR_THRESHOLD_GOOD,
    BLUR_THRESHOLD_MIN,
    BRIGHTNESS_MIN,
    BRIGHTNESS_MAX,
    ANGLE_THRESHOLD_GOOD,
    ANGLE_THRESHOLD_MAX,
    QUALITY_SCORE_ACCEPT,
    QUALITY_SCORE_WARNING,
    QUALITY_WEIGHTS,
)
from backend.models.validation_result import QualityResult

BLUR_IDEAL = 500
MIN_RESOLUTION_PX = 600
IDEAL_RESOLUTION_PX = 1200


# ── Scorers ───────────────────────────────────────────────────────────────────

def _score_blur(gray: np.ndarray) -> tuple[float, float]:
    variance = cv2.Laplacian(gray, cv2.CV_64F).var()
    if variance >= BLUR_IDEAL:
        score = 100.0
    elif variance >= BLUR_THRESHOLD_GOOD:
        score = 60.0 + 40.0 * (variance - BLUR_THRESHOLD_GOOD) / (BLUR_IDEAL - BLUR_THRESHOLD_GOOD)
    elif variance >= BLUR_THRESHOLD_MIN:
        score = 20.0 + 40.0 * (variance - BLUR_THRESHOLD_MIN) / (BLUR_THRESHOLD_GOOD - BLUR_THRESHOLD_MIN)
    else:
        score = max(0.0, 20.0 * variance / max(BLUR_THRESHOLD_MIN, 1))
    return round(score, 1), round(float(variance), 2)


def _score_brightness(gray: np.ndarray) -> tuple[float, float]:
    mean_val = float(np.mean(gray))
    ideal_low, ideal_high = float(BRIGHTNESS_MIN), float(BRIGHTNESS_MAX)
    mid = (ideal_low + ideal_high) / 2.0
    if ideal_low <= mean_val <= ideal_high:
        distance = abs(mean_val - mid) / max(mid - ideal_low, 1)
        score = 100.0 - 30.0 * distance
    elif mean_val < ideal_low:
        score = max(0.0, 70.0 * mean_val / ideal_low)
    else:
        overshoot = mean_val - ideal_high
        max_overshoot = max(255.0 - ideal_high, 1)
        score = max(0.0, 70.0 * (1.0 - overshoot / max_overshoot))
    return round(score, 1), round(mean_val, 2)


def _detect_skew_angle(gray: np.ndarray) -> float:
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    lines = cv2.HoughLinesP(
        edges, 1, np.pi / 180, 100,
        minLineLength=gray.shape[1] // 4,
        maxLineGap=10,
    )
    if lines is None or len(lines) == 0:
        return 0.0
    angles = []
    for line in lines:
        x1, y1, x2, y2 = line.reshape(-1)[:4]
        angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
        angles.append(angle)
    median_angle = float(np.median(angles))
    skew = abs(median_angle) % 90
    if skew > 45:
        skew = 90 - skew
    return round(skew, 2)


def _score_angle(angle_deg: float) -> float:
    if angle_deg <= ANGLE_THRESHOLD_GOOD:
        score = 100.0 - (20.0 * angle_deg / max(ANGLE_THRESHOLD_GOOD, 1))
    elif angle_deg <= ANGLE_THRESHOLD_MAX:
        ratio = (angle_deg - ANGLE_THRESHOLD_GOOD) / max(ANGLE_THRESHOLD_MAX - ANGLE_THRESHOLD_GOOD, 1)
        score = 80.0 - 50.0 * ratio
    else:
        score = max(0.0, 30.0 - 2.0 * (angle_deg - ANGLE_THRESHOLD_MAX))
    return round(score, 1)


def _build_feedback(
    overall: float,
    blur_score: float,
    brightness_score: float,
    angle_score: float,
    raw_blur: float,
    raw_brightness: float,
    raw_angle: float,
    resolution_ok: bool,
) -> dict[str, str]:
    """
    Build FLAT feedback dict: {"en": "...", "hi": "...", "mr": "..."}.
    QualityResult.feedback is Dict[str, str] — must be flat, NOT nested.
    """
    issues_en: list[str] = []
    issues_hi: list[str] = []
    issues_mr: list[str] = []

    if not resolution_ok:
        issues_en.append("Image resolution is too low (min 600px).")
        issues_hi.append("छवि का रिज़ॉल्यूशन बहुत कम है।")
        issues_mr.append("प्रतिमेचे रिझोल्यूशन खूप कमी आहे.")

    if blur_score < 40:
        issues_en.append(f"Image is blurry (sharpness: {raw_blur}). Hold camera steady.")
        issues_hi.append(f"छवि धुंधली है (स्पष्टता: {raw_blur})। कैमरा स्थिर रखें।")
        issues_mr.append(f"प्रतिमा अस्पष्ट आहे (स्पष्टता: {raw_blur}). कॅमेरा स्थिर धरा.")
    elif blur_score < 60:
        issues_en.append(f"Image is slightly blurry ({raw_blur}).")
        issues_hi.append(f"छवि थोड़ी धुंधली है ({raw_blur})।")
        issues_mr.append(f"प्रतिमा थोडी अस्पष्ट आहे ({raw_blur}).")

    if brightness_score < 40:
        if raw_brightness < BRIGHTNESS_MIN:
            issues_en.append("Image is too dark. Use better lighting.")
            issues_hi.append("छवि बहुत अंधेरी है। बेहतर रोशनी का उपयोग करें।")
            issues_mr.append("प्रतिमा खूप गडद आहे. चांगला प्रकाश वापरा.")
        else:
            issues_en.append("Image is overexposed. Avoid direct flash.")
            issues_hi.append("छवि बहुत चमकीली है। सीधी रोशनी से बचें।")
            issues_mr.append("प्रतिमा खूप तेजस्वी आहे. थेट प्रकाश टाळा.")

    if angle_score < 40:
        issues_en.append(f"Document tilted ({raw_angle}°). Place flat.")
        issues_hi.append(f"दस्तावेज़ झुका है ({raw_angle}°)। समतल रखें।")
        issues_mr.append(f"कागद कललेले आहे ({raw_angle}°). सपाट ठेवा.")

    # Compose flat strings (not nested dicts)
    if overall >= QUALITY_SCORE_ACCEPT:
        base_en = "Image quality is good. Proceeding with verification."
        base_hi = "छवि की गुणवत्ता अच्छी है। सत्यापन जारी है।"
        base_mr = "प्रतिमेची गुणवत्ता चांगली आहे. पडताळणी सुरू आहे."
    elif overall >= QUALITY_SCORE_WARNING:
        base_en = "Image quality is acceptable."
        base_hi = "छवि की गुणवत्ता स्वीकार्य है।"
        base_mr = "प्रतिमेची गुणवत्ता स्वीकारार्ह आहे."
    else:
        base_en = "Image quality is too low."
        base_hi = "छवि की गुणवत्ता बहुत कम है।"
        base_mr = "प्रतिमेची गुणवत्ता खूप कमी आहे."

    sep = " "
    return {
        "en": (base_en + sep + sep.join(issues_en)).strip(),
        "hi": (base_hi + sep + sep.join(issues_hi)).strip(),
        "mr": (base_mr + sep + sep.join(issues_mr)).strip(),
    }


# ── Public function ───────────────────────────────────────────────────────────

def check_quality(image_path: str) -> QualityResult:
    """
    Evaluate image quality for document verification.

    Returns QualityResult with:
      - overall_score (0-100)
      - is_acceptable (bool)
      - checks (dict with per-metric details)
      - feedback (flat Dict[str, str] with en/hi/mr keys)
    """
    path = Path(image_path)

    if not path.exists():
        logger.error("Image not found: {}", image_path)
        return QualityResult(
            overall_score=0.0,
            is_acceptable=False,
            checks={},
            feedback={
                "en": "Image file not found. Please re-upload.",
                "hi": "छवि फ़ाइल नहीं मिली। पुनः अपलोड करें।",
                "mr": "प्रतिमा फाइल सापडली नाही. पुन्हा अपलोड करा.",
            },
        )

    img = cv2.imread(str(path))
    if img is None:
        logger.error("Cannot read image: {}", image_path)
        return QualityResult(
            overall_score=0.0,
            is_acceptable=False,
            checks={},
            feedback={
                "en": "Could not read image. File may be corrupted.",
                "hi": "छवि पढ़ नहीं सकी। फ़ाइल दूषित हो सकती है।",
                "mr": "प्रतिमा वाचता आली नाही. फाइल दूषित असू शकते.",
            },
        )

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape[:2]
    min_dim = min(h, w)
    resolution_ok = min_dim >= MIN_RESOLUTION_PX

    blur_score, raw_blur = _score_blur(gray)
    brightness_score, raw_brightness = _score_brightness(gray)
    raw_angle = _detect_skew_angle(gray)
    angle_score = _score_angle(raw_angle)

    overall = (
        QUALITY_WEIGHTS["blur"] * blur_score
        + QUALITY_WEIGHTS["brightness"] * brightness_score
        + QUALITY_WEIGHTS["angle"] * angle_score
    )
    overall = round(overall, 1)

    if not resolution_ok:
        overall = min(overall, QUALITY_SCORE_WARNING - 1)

    is_acceptable = overall >= QUALITY_SCORE_WARNING

    # Build FLAT feedback dict (not nested)
    feedback = _build_feedback(
        overall, blur_score, brightness_score, angle_score,
        raw_blur, raw_brightness, raw_angle, resolution_ok,
    )

    logger.info(
        "Quality check: score={}, acceptable={}, "
        "blur={}({}), brightness={}({}), angle={}({}°), resolution={}x{}({})",
        overall, is_acceptable,
        blur_score, raw_blur,
        brightness_score, raw_brightness,
        angle_score, raw_angle,
        w, h, "OK" if resolution_ok else "LOW",
    )

    return QualityResult(
        overall_score=overall,
        is_acceptable=is_acceptable,
        checks={
            "blur": {"score": blur_score, "raw": raw_blur},
            "brightness": {"score": brightness_score, "raw": raw_brightness},
            "angle": {"score": angle_score, "raw": raw_angle},
            "resolution": {"width": w, "height": h, "ok": resolution_ok},
        },
        feedback=feedback,
    )