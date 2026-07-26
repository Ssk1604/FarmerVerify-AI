# backend/database/seed_data.py
"""
FarmerVerify AI — Mock Farmer Database
100 synthetic, randomly-generated farmer records for demo purposes.
Used for fuzzy matching during document verification.

All data is synthetic and does not correspond to any real person.
Languages: Hindi, Marathi, English name variants
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any, Optional

from loguru import logger


# ══════════════════════════════════════════════════════════════════════════════
# DEMO FARMER — guaranteed match for mock OCR output
# ══════════════════════════════════════════════════════════════════════════════

DEMO_FARMER: dict = {
    "farmer_id": "FF-MH-0001",
    "registration_date": "2025-01-15",
    "personal": {
        "name_en": "Test Farmer",
        "name_mr": "टेस्ट फार्मर",
        "name_hi": "टेस्ट फार्मर",
        "name_variants": [
            "Test Farmer",
            "T Farmer",
            "Test F",
            "Demo Farmer 1",
            "TEST FARMER",
        ],
        "father_name_en": "Sample Father",
        "father_name_mr": "सॅम्पल फादर",
        "gender": "Male",
        "age": 48,
        "phone": "9999999999",
        "aadhaar_number": "000000000000",
        "aadhaar_number_masked": "XXXX XXXX 0000",
    },
    "address": {
        "village": "Sample Village",
        "taluka": "Sample Taluka",
        "district": "Sample District",
        "state": "Sample State",
        "pincode": "000000",
        "full_address_en": (
            "At/Post Sample Village, Tal. Sample Taluka, "
            "Dist. Sample District, Sample State - 000000"
        ),
        "full_address_mr": (
            "मु/पो सॅम्पल व्हिलेज, ता. सॅम्पल तालुका, "
            "जि. सॅम्पल जिल्हा, सॅम्पल स्टेट - 000000"
        ),
    },
    "bank": {
        "bank_name": "Sample Bank",
        "bank_name_mr": "सॅम्पल बँक",
        "branch": "Sample Branch",
        "account_number": "00000000000",
        "ifsc_code": "TEST0000000",
        "account_holder_name": "TEST FARMER",
    },
    "land": {
        "survey_number": "000/A",
        "gat_number": "000/A",
        "village": "Sample Village",
        "taluka": "Sample Taluka",
        "district": "Sample District",
        "area": {"acres": 3.5, "hectares": 1.42},
        "land_type": "Jirayat",
        "primary_crop": "Cotton",
        "khata_number": "0000",
    },
    "documents": {
        "passbook_verified": False,
        "aadhaar_verified": False,
        "land_record_verified": False,
    },
    "status": "pending",
}


# ══════════════════════════════════════════════════════════════════════════════
# NAME POOLS
# ══════════════════════════════════════════════════════════════════════════════

_FIRST_NAMES_MALE = [
    "Ramesh", "Suresh", "Ganesh", "Mahesh", "Rajesh",
    "Prakash", "Vinod", "Anil", "Sunil", "Mohan",
    "Shankar", "Vitthal", "Balaji", "Pandurang", "Dattatray",
    "Kishor", "Ashok", "Vilas", "Dnyaneshwar", "Sambhaji",
    "Tanaji", "Balu", "Nana", "Mahadev", "Bhimrao",
    "Govind", "Tukaram", "Namdev", "Eknath", "Ramdas",
    "Sanjay", "Vijay", "Ajay", "Deepak", "Ravi",
    "Krishna", "Shivaji", "Maruti", "Hanuman", "Digambar",
    "Popat", "Bharat", "Santosh", "Chandrakant", "Laxman",
]

_FIRST_NAMES_FEMALE = [
    "Savitri", "Laxmi", "Suman", "Sunita", "Anita",
    "Kavita", "Mangal", "Shobha", "Vandana", "Rekha",
    "Sushila", "Parvati", "Saraswati", "Durga", "Asha",
    "Chhaya", "Nirmala", "Shanta", "Pushpa", "Kamala",
]

_LAST_NAMES = [
    "Patil", "Deshmukh", "Jadhav", "More", "Pawar",
    "Shinde", "Gaikwad", "Bhosale", "Chavan", "Kale",
    "Wagh", "Sonawane", "Yadav", "Ingale", "Rathod",
    "Borde", "Deshpande", "Kulkarni", "Joshi", "Thakare",
    "Dhage", "Waghmare", "Kamble", "Gawande", "Meshram",
    "Khedkar", "Ghuge", "Tayde", "Raut", "Lokhande",
    "Nikam", "Shete", "Landge", "Bawane", "Ingle",
]

_FATHER_PREFIXES = [
    "Shankar", "Vitthal", "Raghunath", "Pandurang", "Maruti",
    "Tukaram", "Namdev", "Dattatray", "Mahadev", "Govind",
    "Ramchandra", "Eknath", "Dnyanoba", "Baburao", "Kashinath",
    "Ganpat", "Bhimrao", "Dagdu", "Kondiba", "Limbaji",
]


# ══════════════════════════════════════════════════════════════════════════════
# GEOGRAPHY  (Vidarbha + Marathwada)
# ══════════════════════════════════════════════════════════════════════════════

_VILLAGES: list[tuple[str, str, str]] = [
    # (village, district, pincode)
    # Vidarbha
    ("Patur", "Akola", "444501"),
    ("Risod", "Washim", "444506"),
    ("Karanja Lad", "Washim", "444105"),
    ("Mangrulpir", "Washim", "444403"),
    ("Malegaon", "Washim", "444503"),
    ("Dhamangaon", "Amravati", "444709"),
    ("Achalpur", "Amravati", "444806"),
    ("Morshi", "Amravati", "444905"),
    ("Chandur Railway", "Amravati", "444904"),
    ("Warud", "Amravati", "444906"),
    ("Arvi", "Wardha", "442201"),
    ("Deoli", "Wardha", "442101"),
    ("Hinganghat", "Wardha", "442301"),
    ("Samudrapur", "Wardha", "442305"),
    ("Katol", "Nagpur", "441302"),
    ("Ramtek", "Nagpur", "441106"),
    ("Saoner", "Nagpur", "441107"),
    ("Umred", "Nagpur", "441204"),
    ("Bhandara", "Bhandara", "441904"),
    ("Tumsar", "Bhandara", "441912"),
    ("Tirora", "Gondia", "441911"),
    ("Goregaon", "Gondia", "441801"),
    ("Chimur", "Chandrapur", "442903"),
    ("Warora", "Chandrapur", "442907"),
    ("Rajura", "Chandrapur", "442905"),
    ("Pandharkawada", "Yavatmal", "445302"),
    ("Pusad", "Yavatmal", "445204"),
    ("Umarkhed", "Yavatmal", "445206"),
    ("Digras", "Yavatmal", "445203"),
    ("Darwha", "Yavatmal", "445202"),
    # Marathwada
    ("Parbhani", "Parbhani", "431401"),
    ("Jintur", "Parbhani", "431509"),
    ("Gangakhed", "Parbhani", "431514"),
    ("Sonpeth", "Parbhani", "431516"),
    ("Selu", "Parbhani", "431503"),
    ("Ambejogai", "Beed", "431517"),
    ("Kaij", "Beed", "431518"),
    ("Georai", "Beed", "431127"),
    ("Parli", "Beed", "431515"),
    ("Ashti", "Beed", "414203"),
    ("Latur", "Latur", "413512"),
    ("Udgir", "Latur", "413517"),
    ("Nilanga", "Latur", "413521"),
    ("Ausa", "Latur", "413520"),
    ("Nanded", "Nanded", "431601"),
    ("Deglur", "Nanded", "431717"),
    ("Mukhed", "Nanded", "431715"),
    ("Osmanabad", "Osmanabad", "413501"),
    ("Tuljapur", "Osmanabad", "413601"),
    ("Jalna", "Jalna", "431203"),
    ("Ambad", "Jalna", "431204"),
    ("Bhokardan", "Jalna", "431114"),
    ("Hingoli", "Hingoli", "431513"),
    ("Basmath", "Hingoli", "431512"),
    ("Kelapur", "Yavatmal", "445301"),
]


# ══════════════════════════════════════════════════════════════════════════════
# BANKS
# ══════════════════════════════════════════════════════════════════════════════

_BANKS: list[tuple[str, str, str]] = [
    # (bank_name_en, ifsc_prefix, bank_name_mr)
    ("State Bank of India", "SBIN", "स्टेट बँक ऑफ इंडिया"),
    ("Bank of Maharashtra", "MAHB", "बँक ऑफ महाराष्ट्र"),
    ("Central Bank of India", "CBIN", "सेंट्रल बँक ऑफ इंडिया"),
    ("Bank of India", "BKID", "बँक ऑफ इंडिया"),
    ("Punjab National Bank", "PUNB", "पंजाब नॅशनल बँक"),
    ("Union Bank of India", "UBIN", "युनियन बँक ऑफ इंडिया"),
    ("Canara Bank", "CNRB", "कॅनरा बँक"),
    ("Indian Overseas Bank", "IOBA", "इंडियन ओव्हरसीज बँक"),
    ("Vidarbha Konkan Gramin Bank", "VKGB", "विदर्भ कोकण ग्रामीण बँक"),
    ("Maharashtra Gramin Bank", "MAHG", "महाराष्ट्र ग्रामीण बँक"),
]


# ══════════════════════════════════════════════════════════════════════════════
# DEVANAGARI TRANSLITERATIONS
# ══════════════════════════════════════════════════════════════════════════════

_TRANSLITERATE: dict[str, str] = {
    # First names — male
    "Ramesh": "रमेश", "Suresh": "सुरेश", "Ganesh": "गणेश",
    "Mahesh": "महेश", "Rajesh": "राजेश", "Prakash": "प्रकाश",
    "Vinod": "विनोद", "Anil": "अनिल", "Sunil": "सुनील",
    "Mohan": "मोहन", "Shankar": "शंकर", "Vitthal": "विठ्ठल",
    "Balaji": "बालाजी", "Pandurang": "पांडुरंग", "Dattatray": "दत्तात्रय",
    "Kishor": "किशोर", "Ashok": "अशोक", "Vilas": "विलास",
    "Dnyaneshwar": "ज्ञानेश्वर", "Sambhaji": "संभाजी",
    "Tanaji": "तानाजी", "Balu": "बालू", "Nana": "नाना",
    "Mahadev": "महादेव", "Bhimrao": "भीमराव",
    "Govind": "गोविंद", "Tukaram": "तुकाराम", "Namdev": "नामदेव",
    "Eknath": "एकनाथ", "Ramdas": "रामदास",
    "Sanjay": "संजय", "Vijay": "विजय", "Ajay": "अजय",
    "Deepak": "दीपक", "Ravi": "रवी",
    "Krishna": "कृष्णा", "Shivaji": "शिवाजी", "Maruti": "मारुती",
    "Hanuman": "हनुमान", "Digambar": "दिगंबर",
    "Popat": "पोपट", "Bharat": "भारत", "Santosh": "संतोष",
    "Chandrakant": "चंद्रकांत", "Laxman": "लक्ष्मण",
    # First names — female
    "Savitri": "सावित्री", "Laxmi": "लक्ष्मी", "Suman": "सुमन",
    "Sunita": "सुनिता", "Anita": "अनिता",
    "Kavita": "कविता", "Mangal": "मंगल", "Shobha": "शोभा",
    "Vandana": "वंदना", "Rekha": "रेखा",
    "Sushila": "सुशीला", "Parvati": "पार्वती", "Saraswati": "सरस्वती",
    "Durga": "दुर्गा", "Asha": "आशा",
    "Chhaya": "छाया", "Nirmala": "निर्मला", "Shanta": "शांता",
    "Pushpa": "पुष्पा", "Kamala": "कमला",
    # Last names
    "Patil": "पाटील", "Deshmukh": "देशमुख", "Jadhav": "जाधव",
    "More": "मोरे", "Pawar": "पवार",
    "Shinde": "शिंदे", "Gaikwad": "गायकवाड", "Bhosale": "भोसले",
    "Chavan": "चव्हाण", "Kale": "काळे",
    "Wagh": "वाघ", "Sonawane": "सोनवणे", "Yadav": "यादव",
    "Ingale": "इंगळे", "Rathod": "राठोड",
    "Borde": "बोर्डे", "Deshpande": "देशपांडे", "Kulkarni": "कुलकर्णी",
    "Joshi": "जोशी", "Thakare": "ठाकरे",
    "Dhage": "ढगे", "Waghmare": "वाघमारे", "Kamble": "कांबळे",
    "Gawande": "गावंडे", "Meshram": "मेश्राम",
    "Khedkar": "खेडकर", "Ghuge": "घुगे", "Tayde": "तायडे",
    "Raut": "राऊत", "Lokhande": "लोखंडे",
    "Nikam": "निकम", "Shete": "शेटे", "Landge": "लांडगे",
    "Bawane": "बावणे", "Ingle": "इंगळे",
    # Father name prefixes
    "Ramchandra": "रामचंद्र", "Dnyanoba": "ज्ञानोबा",
    "Baburao": "बाबुराव", "Kashinath": "काशिनाथ",
    "Ganpat": "गणपत", "Dagdu": "दगडू",
    "Kondiba": "कोंडिबा", "Limbaji": "लिंबाजी",
    "Raghunath": "रघुनाथ",
}


_CROPS = [
    "Cotton", "Soybean", "Tur Dal", "Jowar", "Wheat",
    "Orange", "Gram", "Sugarcane", "Groundnut", "Sunflower",
]

_LAND_TYPES = ["Jirayat", "Bagayat", "Paddy"]


# ══════════════════════════════════════════════════════════════════════════════
# GENERATOR HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _dv(name: str) -> str:
    """Return Devanagari transliteration of a name, or the name itself."""
    return _TRANSLITERATE.get(name, name)


def _gen_aadhaar() -> str:
    first = str(random.randint(2, 9))
    rest = "".join(str(random.randint(0, 9)) for _ in range(11))
    n = first + rest
    return n   # stored as 12 digits, no spaces


def _gen_account(prefix: str) -> str:
    length = random.choice([11, 12, 13, 14])
    return "".join(str(random.randint(0, 9)) for _ in range(length))


def _gen_ifsc(prefix: str, pincode: str) -> str:
    code = prefix[:4].upper().ljust(4, "X")
    branch = pincode[:3] + "".join(str(random.randint(0, 9)) for _ in range(3))
    return f"{code}0{branch}"


def _gen_survey() -> str:
    main = random.randint(1, 999)
    if random.random() < 0.4:
        return f"{main}/{random.randint(1, 20)}"
    return str(main)


def _gen_phone() -> str:
    prefix = random.choice([
        "70", "72", "73", "74", "75", "76", "77", "78",
        "80", "81", "82", "83", "84", "85", "86", "87", "88", "89",
        "90", "91", "92", "93", "94", "95", "96", "97", "98", "99",
    ])
    return prefix + "".join(str(random.randint(0, 9)) for _ in range(8))


def _gen_land_area() -> dict:
    acres = round(random.uniform(0.5, 15.0), 2)
    return {"acres": acres, "hectares": round(acres * 0.4047, 2)}


# ══════════════════════════════════════════════════════════════════════════════
# RECORD GENERATOR
# ══════════════════════════════════════════════════════════════════════════════

def generate_farmer_record(seq: int) -> dict:
    """Generate one realistic mock farmer record."""
    is_male = random.random() < 0.80
    first = random.choice(_FIRST_NAMES_MALE if is_male else _FIRST_NAMES_FEMALE)
    last = random.choice(_LAST_NAMES)
    father_first = random.choice(_FATHER_PREFIXES)

    village, district, pincode = random.choice(_VILLAGES)
    bank_name, bank_code, bank_name_mr = random.choice(_BANKS)

    aadhaar = _gen_aadhaar()
    account = _gen_account(bank_code)
    ifsc = _gen_ifsc(bank_code, pincode)
    survey = _gen_survey()
    phone = _gen_phone()
    land = _gen_land_area()

    name_en = f"{first} {father_first} {last}"
    name_mr = f"{_dv(first)} {_dv(father_first)} {_dv(last)}"

    # Build realistic name variants for fuzzy matching
    variants = [
        name_en,
        name_mr,
        f"{first} {last}",
        f"{first[0]}. {last}",
        f"{first} {father_first[0]}. {last}",
        name_en.upper(),
    ]

    return {
        "farmer_id": f"FF-MH-{seq:04d}",
        "registration_date": (
            f"2025-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}"
        ),
        "personal": {
            "name_en": name_en,
            "name_mr": name_mr,
            "name_hi": name_mr,
            "name_variants": variants,
            "father_name_en": f"{father_first} {last}",
            "father_name_mr": f"{_dv(father_first)} {_dv(last)}",
            "gender": "Male" if is_male else "Female",
            "age": random.randint(25, 70),
            "phone": phone,
            "aadhaar_number": aadhaar,
            "aadhaar_number_masked": f"XXXX XXXX {aadhaar[-4:]}",
        },
        "address": {
            "village": village,
            "taluka": village,
            "district": district,
            "state": "Maharashtra",
            "pincode": pincode,
            "full_address_en": (
                f"At/Post {village}, Tal. {village}, "
                f"Dist. {district}, Maharashtra - {pincode}"
            ),
            "full_address_mr": (
                f"मु/पो {village}, ता. {village}, "
                f"जि. {district}, महाराष्ट्र - {pincode}"
            ),
        },
        "bank": {
            "bank_name": bank_name,
            "bank_name_mr": bank_name_mr,
            "branch": f"{village} Branch",
            "account_number": account,
            "ifsc_code": ifsc,
            "account_holder_name": name_en.upper(),
        },
        "land": {
            "survey_number": survey,
            "gat_number": survey,
            "village": village,
            "taluka": village,
            "district": district,
            "area": land,
            "land_type": random.choice(_LAND_TYPES),
            "primary_crop": random.choice(_CROPS),
            "khata_number": str(random.randint(100, 9999)),
        },
        "documents": {
            "passbook_verified": random.random() < 0.3,
            "aadhaar_verified": random.random() < 0.3,
            "land_record_verified": random.random() < 0.3,
        },
        "status": random.choice(
            ["pending", "pending", "pending", "partial", "verified"]
        ),
    }


# ══════════════════════════════════════════════════════════════════════════════
# DATABASE CLASS
# ══════════════════════════════════════════════════════════════════════════════

class MockFarmerDatabase:
    """In-memory mock farmer database with indexed lookup and fuzzy search."""

    def __init__(self) -> None:
        self._records: list[dict] = []
        self._index_by_id: dict[str, dict] = {}
        self._index_by_aadhaar: dict[str, dict] = {}
        self._index_by_account: dict[str, dict] = {}
        self._loaded = False

    # ── Load ─────────────────────────────────────────────────────────────

    def load(self, count: int = 100) -> None:
        """Generate and index all records. Idempotent."""
        if self._loaded:
            return

        logger.info(f"Generating {count} mock farmer records...")
        random.seed(42)

        # DEMO_FARMER is always first (ID = FF-MH-0001)
        # It matches the mock OCR output so the pipeline can return "verified"
        generated = [generate_farmer_record(i + 2) for i in range(count - 1)]
        self._records = [DEMO_FARMER] + generated

        # Build O(1) indexes
        for record in self._records:
            fid = record["farmer_id"]
            aadhaar_clean = record["personal"]["aadhaar_number"].replace(" ", "")
            account_clean = record["bank"]["account_number"].replace(" ", "")

            self._index_by_id[fid] = record
            self._index_by_aadhaar[aadhaar_clean] = record
            self._index_by_account[account_clean] = record

        self._loaded = True
        districts = {r["address"]["district"] for r in self._records}
        banks = {r["bank"]["bank_name"] for r in self._records}
        logger.info(
            f"✅ Mock database loaded: {len(self._records)} farmers"
        )
        logger.info(f"   Districts: {len(districts)} | Banks: {len(banks)}")

    def _ensure_loaded(self) -> None:
        if not self._loaded:
            self.load()

    # ── Indexed lookups (O(1)) ────────────────────────────────────────────

    def get_by_id(self, farmer_id: str) -> Optional[dict]:
        self._ensure_loaded()
        return self._index_by_id.get(farmer_id)

    def get_by_aadhaar(self, aadhaar: str) -> Optional[dict]:
        """Lookup by 12-digit Aadhaar (spaces/dashes stripped)."""
        self._ensure_loaded()
        clean = aadhaar.replace(" ", "").replace("-", "")
        return self._index_by_aadhaar.get(clean)

    def get_by_account(self, account_number: str) -> Optional[dict]:
        """Lookup by bank account number (spaces/dashes stripped)."""
        self._ensure_loaded()
        clean = account_number.replace(" ", "").replace("-", "")
        return self._index_by_account.get(clean)

    # ── Search (O(n)) ─────────────────────────────────────────────────────

    def search_by_name(self, name: str, top_n: int = 5) -> list[dict]:
        """
        Fuzzy name search — returns up to top_n records.
        Checks name_en, name_mr, name_hi, and all name_variants.
        Simple contains check; fuzzy scoring is done in fuzzy_matcher.py.
        """
        self._ensure_loaded()
        name_lower = name.lower().strip()
        results: list[dict] = []

        for record in self._records:
            personal = record["personal"]
            candidates = [
                personal["name_en"].lower(),
                personal["name_mr"].lower(),
                personal.get("name_hi", "").lower(),
            ] + [v.lower() for v in personal.get("name_variants", [])]

            for candidate in candidates:
                if name_lower in candidate or candidate in name_lower:
                    results.append(record)
                    break
            if len(results) >= top_n:
                break

        return results

    def search_by_village(self, village: str) -> list[dict]:
        self._ensure_loaded()
        v_lower = village.lower().strip()
        return [
            r for r in self._records
            if v_lower in r["address"]["village"].lower()
        ]

    # ── Bulk access ───────────────────────────────────────────────────────

    @property
    def records(self) -> list[dict]:
        self._ensure_loaded()
        return self._records

    def get_all_names(self) -> list[dict]:
        """Returns minimal name info for all farmers (used by fuzzy matcher)."""
        self._ensure_loaded()
        return [
            {
                "farmer_id": r["farmer_id"],
                "name_en": r["personal"]["name_en"],
                "name_mr": r["personal"]["name_mr"],
                "name_variants": r["personal"].get("name_variants", []),
                "account_number": r["bank"]["account_number"],
                "aadhaar_number": r["personal"]["aadhaar_number"],
            }
            for r in self._records
        ]

    # ── Export ────────────────────────────────────────────────────────────

    def export_json(self, filepath: Optional[str] = None) -> str:
        self._ensure_loaded()
        if filepath is None:
            filepath = str(
                Path(__file__).parent / "mock_farmers.json"
            )
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self._records, f, ensure_ascii=False, indent=2)
        logger.info(f"📁 Exported {len(self._records)} records → {filepath}")
        return filepath

    # ── Stats ─────────────────────────────────────────────────────────────

    def get_stats(self) -> dict[str, Any]:
        self._ensure_loaded()
        districts: dict = {}
        banks: dict = {}
        statuses: dict = {}

        for r in self._records:
            d = r["address"]["district"]
            b = r["bank"]["bank_name"]
            s = r["status"]
            districts[d] = districts.get(d, 0) + 1
            banks[b] = banks.get(b, 0) + 1
            statuses[s] = statuses.get(s, 0) + 1

        return {
            "total_farmers": len(self._records),
            "districts": districts,
            "banks": banks,
            "statuses": statuses,
            "male_count": sum(
                1 for r in self._records if r["personal"]["gender"] == "Male"
            ),
            "female_count": sum(
                1 for r in self._records if r["personal"]["gender"] == "Female"
            ),
        }


# ══════════════════════════════════════════════════════════════════════════════
# SINGLETON
# ══════════════════════════════════════════════════════════════════════════════

_db_instance: Optional[MockFarmerDatabase] = None


def get_mock_database() -> MockFarmerDatabase:
    """Return the singleton MockFarmerDatabase, loading data on first call."""
    global _db_instance
    if _db_instance is None:
        _db_instance = MockFarmerDatabase()
        _db_instance.load()
    return _db_instance


# ══════════════════════════════════════════════════════════════════════════════
# CLI — run directly to preview data
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    db = get_mock_database()
    stats = db.get_stats()

    print("\n" + "=" * 60)
    print("  FarmerVerify AI — Mock Farmer Database")
    print("=" * 60)
    print(f"  Total farmers : {stats['total_farmers']}")
    print(f"  Male          : {stats['male_count']}")
    print(f"  Female        : {stats['female_count']}")

    print(f"\n  Districts ({len(stats['districts'])}):")
    for d, c in sorted(stats["districts"].items(), key=lambda x: -x[1])[:8]:
        print(f"    {d}: {c}")

    print(f"\n  Banks ({len(stats['banks'])}):")
    for b, c in sorted(stats["banks"].items(), key=lambda x: -x[1]):
        print(f"    {b}: {c}")

    print(f"\n  Statuses:")
    for s, c in stats["statuses"].items():
        print(f"    {s}: {c}")

    print("\n" + "-" * 60)
    print("  Demo Farmer (always matches mock OCR):")
    demo = db.get_by_id("FF-MH-0001")
    if demo:
        print(f"    ID      : {demo['farmer_id']}")
        print(f"    Name    : {demo['personal']['name_en']}")
        print(f"    Name MR : {demo['personal']['name_mr']}")
        print(f"    Account : {demo['bank']['account_number']}")
        print(f"    IFSC    : {demo['bank']['ifsc_code']}")
        print(f"    Survey  : {demo['land']['survey_number']}")
        print(f"    Village : {demo['address']['village']}, {demo['address']['district']}")

    print("\n  Sample records (2-4):")
    for record in db.records[1:4]:
        p = record["personal"]
        b = record["bank"]
        a = record["address"]
        print(f"\n  [{record['farmer_id']}] {p['name_en']}")
        print(f"    MR: {p['name_mr']}")
        print(f"    Village: {a['village']}, {a['district']}")
        print(f"    Bank: {b['bank_name']} | A/c: {b['account_number']}")

    filepath = db.export_json()
    print(f"\n  ✅ Exported to: {filepath}")
    print("=" * 60)