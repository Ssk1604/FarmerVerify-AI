# backend/services/fuzzy_matcher.py

from __future__ import annotations

from typing import Optional

from loguru import logger
from rapidfuzz import fuzz

from backend.config import get_settings
from backend.database.seed_data import MockFarmerDatabase
from backend.models.validation_result import (
    ExtractedFields,
    FuzzyMatchReport,
    MatchResult,
)

_db = MockFarmerDatabase()
_settings = get_settings()


# ── Bilingual location lookup ─────────────────────────────────────────────────
# Maps Devanagari village/district names to their English equivalents.
# Covers all villages in seed_data.py.

_DEVANAGARI_TO_ENGLISH: dict[str, str] = {
    # Yavatmal district
    "पांढरकवडा": "Pandharkawada",
    "पुसद": "Pusad",
    "उमरखेड": "Umarkhed",
    "दिग्रस": "Digras",
    "दारव्हा": "Darwha",
    "केळापूर": "Kelapur",
    # Yavatmal (district name)
    "यवतमाळ": "Yavatmal",
    # Akola
    "पातूर": "Patur",
    "अकोला": "Akola",
    # Washim
    "रिसोड": "Risod",
    "करंजा लाड": "Karanja Lad",
    "मंगरुळपीर": "Mangrulpir",
    "मालेगाव": "Malegaon",
    "वाशिम": "Washim",
    # Amravati
    "धामणगाव": "Dhamangaon",
    "अचलपूर": "Achalpur",
    "मोर्शी": "Morshi",
    "चांदूर रेल्वे": "Chandur Railway",
    "वरूड": "Warud",
    "अमरावती": "Amravati",
    # Wardha
    "आर्वी": "Arvi",
    "देवळी": "Deoli",
    "हिंगणघाट": "Hinganghat",
    "समुद्रपूर": "Samudrapur",
    "वर्धा": "Wardha",
    # Nagpur
    "काटोल": "Katol",
    "रामटेक": "Ramtek",
    "सावनेर": "Saoner",
    "उमरेड": "Umred",
    "नागपूर": "Nagpur",
    # Bhandara
    "भंडारा": "Bhandara",
    "तुमसर": "Tumsar",
    # Gondia
    "तिरोडा": "Tirora",
    "गोरेगाव": "Goregaon",
    "गोंदिया": "Gondia",
    # Chandrapur
    "चिमूर": "Chimur",
    "वरोरा": "Warora",
    "राजुरा": "Rajura",
    "चंद्रपूर": "Chandrapur",
    # Parbhani
    "परभणी": "Parbhani",
    "जिंतूर": "Jintur",
    "गंगाखेड": "Gangakhed",
    "सोनपेठ": "Sonpeth",
    "सेलू": "Selu",
    # Beed
    "अंबेजोगाई": "Ambejogai",
    "कैज": "Kaij",
    "गेवराई": "Georai",
    "परळी": "Parli",
    "आष्टी": "Ashti",
    "बीड": "Beed",
    # Latur
    "लातूर": "Latur",
    "उदगीर": "Udgir",
    "निलंगा": "Nilanga",
    "औसा": "Ausa",
    # Nanded
    "नांदेड": "Nanded",
    "देगलूर": "Deglur",
    "मुखेड": "Mukhed",
    "किनवट": "Kinwat",
    "हदगाव": "Hadgaon",
    # Osmanabad
    "उस्मानाबाद": "Osmanabad",
    "तुळजापूर": "Tuljapur",
    "उमरगा": "Umarga",
    "कळंब": "Kalamb",
    # Jalna
    "जालना": "Jalna",
    "अंबड": "Ambad",
    "भोकरदन": "Bhokardan",
    # Hingoli
    "हिंगोली": "Hingoli",
    "कळमनुरी": "Kalamnuri",
    "बसमत": "Basmath",
}


def _normalize_location(value: Optional[str]) -> str:
    """
    Normalize a location name by transliterating Devanagari to English.
    Returns the original value if no transliteration is found.
    """
    if not value:
        return ""
    stripped = value.strip()
    # Check direct transliteration lookup
    english = _DEVANAGARI_TO_ENGLISH.get(stripped)
    if english:
        return english
    # Check if it's already English (contains only ASCII)
    if all(c.isascii() or c.isspace() for c in stripped):
        return stripped
    # Partial match in transliteration table
    for dev, eng in _DEVANAGARI_TO_ENGLISH.items():
        if dev in stripped:
            return eng
    return stripped


# ── Scoring helpers ───────────────────────────────────────────────────────────

def _name_score(extracted: Optional[str], db_name: str, variants: list[str]) -> float:
    if not extracted:
        return 0.0
    candidates = [db_name] + [v for v in variants if v]
    best = max(
        max(
            fuzz.token_sort_ratio(extracted.upper(), c.upper()),
            fuzz.token_set_ratio(extracted.upper(), c.upper()),
        )
        for c in candidates if c
    )
    return round(best, 1)


def _numeric_score(extracted: Optional[str], db_value: Optional[str]) -> float:
    if not extracted or not db_value:
        return 0.0
    e = extracted.replace(" ", "").replace("-", "")
    d = db_value.replace(" ", "").replace("-", "")
    if e == d:
        return 100.0
    if e in d or d in e:
        return 70.0
    return round(fuzz.ratio(e, d), 1)


def _location_score(extracted: Optional[str], db_value: Optional[str]) -> float:
    """
    Compare location names, handling Devanagari ↔ English translation.
    """
    if not extracted or not db_value:
        return 0.0
    # Normalize both to English if possible
    norm_extracted = _normalize_location(extracted)
    norm_db = _normalize_location(db_value)
    return round(
        max(
            fuzz.token_sort_ratio(norm_extracted.upper(), norm_db.upper()),
            fuzz.token_sort_ratio(extracted.upper(), db_value.upper()),
        ),
        1,
    )


def _classify(score: float) -> str:
    s = _settings
    if score >= s.match_threshold_exact:
        return "exact"
    if score >= s.match_threshold_good:
        return "good"
    if score >= s.match_threshold_partial:
        return "partial"
    return "no_match"


def _verdict(overall: float) -> str:
    s = _settings
    if overall >= s.match_threshold_good:
        return "verified"
    if overall >= s.match_threshold_partial:
        return "partial_match"
    return "no_match"


def _verdict_message(verdict: str, score: float) -> str:
    return {
        "verified": f"Document verified — match score {score:.0f}%.",
        "partial_match": f"Partial match ({score:.0f}%) — manual review recommended.",
        "no_match": f"No confident match (score {score:.0f}%). Verify manually.",
    }.get(verdict, f"Unknown verdict (score {score:.0f}%).")


# ── Public function ───────────────────────────────────────────────────────────

def match_fields(
    extracted: ExtractedFields,
    farmer_id: Optional[str] = None,
) -> FuzzyMatchReport:
    """
    Match extracted document fields against the mock farmer database.

    Lookup priority:
      1. farmer_id  (direct O(1))
      2. Aadhaar    (exact O(1))
      3. Account    (exact O(1))
      4. Name       (fuzzy O(n))
    """
    farmer: Optional[dict] = None
    lookup_method = "none"

    # 1. Direct lookup
    if farmer_id:
        farmer = _db.get_by_id(farmer_id)
        if farmer:
            lookup_method = "farmer_id"
            logger.debug("Found farmer by ID: {}", farmer_id)

    # 2. Aadhaar
    if not farmer and extracted.aadhaar_number:
        clean = extracted.aadhaar_number.replace(" ", "").replace("-", "")
        farmer = _db.get_by_aadhaar(clean)
        if farmer:
            lookup_method = "aadhaar"

    # 3. Account number
    if not farmer and extracted.account_number:
        clean = extracted.account_number.replace(" ", "").replace("-", "")
        farmer = _db.get_by_account(clean)
        if farmer:
            lookup_method = "account_number"

    # 4. Name fuzzy search
    if not farmer and extracted.name:
        results = _db.search_by_name(extracted.name)
        if results:
            farmer = results[0]
            lookup_method = "name_fuzzy"

    if not farmer:
        logger.warning("No farmer match found")
        return FuzzyMatchReport(
            farmer_id=None,
            farmer_name=None,
            lookup_method="none",
            field_scores={},
            overall_score=0.0,
            verdict="no_match",
            message="No matching farmer record found in database.",
        )

    logger.info(
        "Farmer located | id={} | method={}",
        farmer["farmer_id"], lookup_method,
    )

    # ── Field scoring ─────────────────────────────────────────────────────

    field_scores: dict[str, float] = {}
    match_results: list[MatchResult] = []

    db_name_en: str = farmer["personal"]["name_en"]
    db_name_local: str = (
        farmer["personal"].get("name_mr")
        or farmer["personal"].get("name_hi")
        or ""
    )
    db_variants: list[str] = farmer["personal"].get("name_variants", [])

    # Name (English)
    if extracted.name:
        candidates = [db_name_en] + [v for v in db_variants if v]
        score = max(
            max(
                fuzz.token_sort_ratio(extracted.name.upper(), c.upper()),
                fuzz.token_set_ratio(extracted.name.upper(), c.upper()),
            )
            for c in candidates if c
        )
        if db_name_local:
            score = max(
                score,
                fuzz.token_sort_ratio(extracted.name, db_name_local),
            )
        score = round(score, 1)
        field_scores["name"] = score
        match_results.append(MatchResult(
            field="name",
            extracted=extracted.name,
            database=db_name_en,
            score=score,
            match_type=_classify(score),
        ))

    # Name (local / Devanagari)
    if extracted.name_local and db_name_local:
        score = round(fuzz.token_sort_ratio(extracted.name_local, db_name_local), 1)
        field_scores["name_local"] = score
        match_results.append(MatchResult(
            field="name_local",
            extracted=extracted.name_local,
            database=db_name_local,
            score=score,
            match_type=_classify(score),
        ))

    # Account number
    if extracted.account_number:
        db_acct: str = farmer["bank"]["account_number"]
        score = _numeric_score(extracted.account_number, db_acct)
        field_scores["account_number"] = score
        match_results.append(MatchResult(
            field="account_number",
            extracted=extracted.account_number,
            database=db_acct,
            score=score,
            match_type=_classify(score),
        ))

    # IFSC
    if extracted.ifsc_code:
        db_ifsc: str = farmer["bank"]["ifsc_code"]
        score = round(fuzz.ratio(
            extracted.ifsc_code.upper().strip(),
            db_ifsc.upper().strip(),
        ), 1)
        field_scores["ifsc_code"] = score
        match_results.append(MatchResult(
            field="ifsc_code",
            extracted=extracted.ifsc_code,
            database=db_ifsc,
            score=score,
            match_type=_classify(score),
        ))

    # Bank name
    if extracted.bank_name:
        db_bank: str = farmer["bank"]["bank_name"]
        db_bank_local: str = farmer["bank"].get("bank_name_mr", "")
        s1 = fuzz.token_sort_ratio(extracted.bank_name.upper(), db_bank.upper())
        s2 = fuzz.token_sort_ratio(extracted.bank_name, db_bank_local) if db_bank_local else 0
        score = round(max(s1, s2), 1)
        field_scores["bank_name"] = score
        match_results.append(MatchResult(
            field="bank_name",
            extracted=extracted.bank_name,
            database=db_bank,
            score=score,
            match_type=_classify(score),
        ))

    # Aadhaar
    if extracted.aadhaar_number:
        db_aadhaar: str = farmer["personal"]["aadhaar_number"]
        score = _numeric_score(extracted.aadhaar_number, db_aadhaar)
        field_scores["aadhaar_number"] = score
        match_results.append(MatchResult(
            field="aadhaar_number",
            extracted=extracted.aadhaar_number,
            database=db_aadhaar,
            score=score,
            match_type=_classify(score),
        ))

    # Village — use bilingual comparison
    if extracted.village:
        db_village: str = farmer["address"]["village"]
        score = _location_score(extracted.village, db_village)
        field_scores["village"] = score
        match_results.append(MatchResult(
            field="village",
            extracted=extracted.village,
            database=db_village,
            score=score,
            match_type=_classify(score),
        ))

    # District — use bilingual comparison
    if extracted.district:
        db_district: str = farmer["address"]["district"]
        score = _location_score(extracted.district, db_district)
        field_scores["district"] = score
        match_results.append(MatchResult(
            field="district",
            extracted=extracted.district,
            database=db_district,
            score=score,
            match_type=_classify(score),
        ))

    # Survey number
    if extracted.survey_number:
        db_survey: str = farmer["land"].get("survey_number", "")
        if db_survey:
            score = _numeric_score(extracted.survey_number, db_survey)
            field_scores["survey_number"] = score
            match_results.append(MatchResult(
                field="survey_number",
                extracted=extracted.survey_number,
                database=db_survey,
                score=score,
                match_type=_classify(score),
            ))

    # ── Overall score & verdict ───────────────────────────────────────────

    overall = (
        round(sum(field_scores.values()) / len(field_scores), 2)
        if field_scores
        else 0.0
    )
    verdict = _verdict(overall)

    report = FuzzyMatchReport(
        farmer_id=farmer["farmer_id"],
        farmer_name=farmer["personal"]["name_en"],
        lookup_method=lookup_method,
        field_scores=field_scores,
        overall_score=overall,
        verdict=verdict,
        message=_verdict_message(verdict, overall),
    )

    logger.info(
        "Match result | farmer={} | score={} | verdict={} | method={}",
        farmer["farmer_id"], overall, verdict, lookup_method,
    )
    return report