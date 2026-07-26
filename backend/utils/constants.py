"""
FarmerVerify AI - Constants and Configuration
All thresholds, patterns, messages, and mappings.
"""

# ============================================================
# Quality Check Thresholds
# ============================================================
QUALITY_SCORE_ACCEPT = 70       # Score >= this = accepted
QUALITY_SCORE_WARNING = 50      # Score >= this but < accept = warning

# Blur detection (Laplacian variance)
BLUR_THRESHOLD_GOOD = 100       # Above this = sharp
BLUR_THRESHOLD_MIN = 50         # Below this = definitely blurry

# Brightness (mean pixel intensity, 0-255)
BRIGHTNESS_MIN = 50             # Below = too dark
BRIGHTNESS_MAX = 200            # Above = too bright

# Angle/Skew (degrees)
ANGLE_THRESHOLD_GOOD = 5        # Within this = acceptable
ANGLE_THRESHOLD_MAX = 15        # Above this = too skewed

# Resolution
MIN_WIDTH = 640
MIN_HEIGHT = 480

# Quality weights (must sum to 1.0)
QUALITY_WEIGHTS = {
    "blur": 0.50,
    "brightness": 0.30,
    "angle": 0.20,
}

# ============================================================
# File Upload Constraints
# ============================================================
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB in bytes
MAX_FILE_SIZE_MB = 10

SUPPORTED_EXTENSIONS = [".jpg", ".jpeg", ".png", ".webp"]
SUPPORTED_IMAGE_FORMATS = [
    "image/jpeg",
    "image/png",
    "image/webp",
]

# ============================================================
# Document Types
# ============================================================
DOCUMENT_TYPES = {
    "passbook": {
        "id": "passbook",
        "name": "Bank Passbook",
        "name_hi": "बैंक पासबुक",
        "name_mr": "बँक पासबुक",
        "required_fields": ["name", "account_number", "ifsc_code", "bank_name"],
    },
    "aadhaar": {
        "id": "aadhaar",
        "name": "Aadhaar Card",
        "name_hi": "आधार कार्ड",
        "name_mr": "आधार कार्ड",
        "required_fields": ["name", "aadhaar_number"],
    },
    "land_record": {
        "id": "land_record",
        "name": "Land Record (7/12 Extract)",
        "name_hi": "भूमि अभिलेख (7/12)",
        "name_mr": "जमिनीचा उतारा (7/12)",
        "required_fields": ["name", "survey_number", "area"],
    },
}

# ============================================================
# Document & Verification Status Values
# ============================================================
DOCUMENT_STATUSES = [
    "uploaded",
    "quality_check",
    "quality_passed",
    "quality_warning",
    "quality_failed",
    "ocr_processing",
    "ocr_complete",
    "matching",
    "verified",
    "needs_review",
    "rejected",
    "error",
]

VERIFICATION_STATUSES = [
    "pending",
    "verified",
    "needs_review",
    "rejected",
]

# ============================================================
# Regex Patterns for Field Extraction
# ============================================================
ACCOUNT_NUMBER_PATTERN = r'\b\d[\d\s\-]{8,17}\d\b'
IFSC_PATTERN = r'\b[A-Z]{4}0[A-Z0-9]{6}\b'
AADHAAR_PATTERN = r'\b\d{4}\s?\d{4}\s?\d{4}\b'
PHONE_PATTERN = r'\b[6-9]\d{9}\b'
PINCODE_PATTERN = r'\b[1-9]\d{5}\b'

# Survey number patterns for land records
SURVEY_PATTERN = r'(?:survey|सर्वे|गट)\s*(?:no\.?|नं\.?|क्र\.?)?\s*(\d+[/\-]?\d*)'

# ============================================================
# Field Keywords (for locating fields in OCR text)
# ============================================================
FIELD_KEYWORDS = {
    "name": {
        "en": ["name", "account holder", "holder name", "customer name"],
        "hi": ["नाम", "खाताधारक", "ग्राहक का नाम"],
        "mr": ["नाव", "खातेदार", "ग्राहकाचे नाव"],
    },
    "account_number": {
        "en": ["account no", "a/c no", "account number", "acct no"],
        "hi": ["खाता संख्या", "खाता नं", "खाता क्र"],
        "mr": ["खाते क्र", "खाता क्रमांक"],
    },
    "ifsc_code": {
        "en": ["ifsc", "ifsc code", "ifs code"],
        "hi": ["आईएफएससी"],
        "mr": ["आयएफएससी"],
    },
    "bank_name": {
        "en": ["bank", "branch"],
        "hi": ["बैंक", "शाखा"],
        "mr": ["बँक", "शाखा"],
    },
    "aadhaar_number": {
        "en": ["aadhaar", "aadhar", "uid"],
        "hi": ["आधार"],
        "mr": ["आधार"],
    },
    "survey_number": {
        "en": ["survey no", "survey number", "gut no"],
        "hi": ["सर्वे नं", "गट नं"],
        "mr": ["सर्वे क्र", "गट क्र"],
    },
}

# ============================================================
# Fuzzy Matching Thresholds
# ============================================================
MATCH_THRESHOLD_EXACT = 95      # Score >= this = exact match
MATCH_THRESHOLD_GOOD = 80       # Score >= this = good match
MATCH_THRESHOLD_PARTIAL = 60    # Score >= this = partial match (needs review)
# Below PARTIAL = no match

OVERALL_MATCH_ACCEPT = 80       # Overall score >= this = verified
OVERALL_MATCH_REVIEW = 60       # Overall score >= this = needs_review
# Below REVIEW = rejected

# ============================================================
# Messages (Trilingual)
# ============================================================
MESSAGES = {
    "upload_success": {
        "en": "Document uploaded successfully! We're checking the image quality.",
        "hi": "दस्तावेज़ सफलतापूर्वक अपलोड हो गया! हम छवि गुणवत्ता की जाँच कर रहे हैं।",
        "mr": "दस्तऐवज यशस्वीपणे अपलोड झाला! आम्ही प्रतिमेची गुणवत्ता तपासत आहोत.",
    },
    "quality_pass": {
        "en": "Image quality is good! Processing your document now.",
        "hi": "छवि गुणवत्ता अच्छी है! अब आपका दस्तावेज़ प्रोसेस हो रहा है।",
        "mr": "प्रतिमेची गुणवत्ता चांगली आहे! आता तुमचा दस्तऐवज प्रक्रिया होत आहे.",
    },
    "quality_warning": {
        "en": "Image quality could be better, but we'll try to process it. You may need to reupload.",
        "hi": "छवि गुणवत्ता बेहतर हो सकती है, लेकिन हम प्रोसेस करने की कोशिश करेंगे।",
        "mr": "प्रतिमेची गुणवत्ता चांगली असू शकते, पण आम्ही प्रक्रिया करण्याचा प्रयत्न करू.",
    },
    "quality_fail_blur": {
        "en": "The image is too blurry. Please hold your phone steady and retake the photo.",
        "hi": "छवि बहुत धुंधली है। कृपया फोन स्थिर रखें और फोटो दोबारा लें।",
        "mr": "प्रतिमा खूप अस्पष्ट आहे. कृपया फोन स्थिर धरा आणि पुन्हा फोटो काढा.",
    },
    "quality_fail_brightness": {
        "en": "The image is too dark or too bright. Please take the photo in good lighting.",
        "hi": "छवि बहुत अंधेरी या बहुत उजली है। अच्छी रोशनी में फोटो लें।",
        "mr": "प्रतिमा खूप गडद किंवा खूप तेजस्वी आहे. चांगल्या प्रकाशात फोटो काढा.",
    },
    "quality_fail_angle": {
        "en": "The document appears tilted. Place it flat on a surface and hold your phone directly above.",
        "hi": "दस्तावेज़ तिरछा दिख रहा है। इसे सतह पर सीधा रखें और फोन सीधा ऊपर रखें।",
        "mr": "दस्तऐवज तिरपा दिसत आहे. सपाट ठेवा आणि फोन थेट वर धरा.",
    },
    "verification_success": {
        "en": "Your document has been verified successfully! ✅",
        "hi": "आपका दस्तावेज़ सफलतापूर्वक सत्यापित हो गया! ✅",
        "mr": "तुमचा दस्तऐवज यशस्वीपणे सत्यापित झाला! ✅",
    },
    "verification_review": {
        "en": "Your document needs manual review. A team member will check it shortly.",
        "hi": "आपके दस्तावेज़ की मैन्युअल समीक्षा आवश्यक है। टीम का सदस्य जल्द जांच करेगा।",
        "mr": "तुमच्या दस्तऐवजाला मॅन्युअल तपासणी आवश्यक आहे. टीम सदस्य लवकरच तपासेल.",
    },
    "verification_failed": {
        "en": "We couldn't verify your document. Please check the details and try again.",
        "hi": "हम आपका दस्तावेज़ सत्यापित नहीं कर सके। विवरण जांचें और पुनः प्रयास करें।",
        "mr": "आम्ही तुमचा दस्तऐवज सत्यापित करू शकलो नाही. तपशील तपासा आणि पुन्हा प्रयत्न करा.",
    },
    "error_generic": {
        "en": "Something went wrong. Please try again or contact support.",
        "hi": "कुछ गलत हो गया। कृपया पुनः प्रयास करें या सहायता से संपर्क करें।",
        "mr": "काहीतरी चूक झाली. कृपया पुन्हा प्रयत्न करा किंवा सपोर्टशी संपर्क करा.",
    },
}