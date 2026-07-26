"""
FarmerVerify AI — Farmer Data Model
Defines the structure of farmer records in the database.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class Farmer(BaseModel):
    """
    Represents a farmer in the system.
    
    Example:
    {
        "id": "FM_2024_08291",
        "name": "Test Farmer",
        "name_local": "टेस्ट फार्मर",
        "phone": "9999999999",
        "account_number": "1234567890123",
        "ifsc_code": "SBIN0012345",
        "bank_name": "State Bank of India",
        "village": "Shirur",
        "taluka": "Shirur",
        "district": "Pune",
        "state": "Maharashtra"
    }
    """
    
    id: str = Field(
        description="Unique farmer ID (e.g., FM_2024_08291)"
    )
    
    name: str = Field(
        description="Full name in English"
    )
    
    name_local: Optional[str] = Field(
        default=None,
        description="Name in local language (Hindi/Marathi)"
    )
    
    phone: str = Field(
        description="10-digit mobile number"
    )
    
    account_number: Optional[str] = Field(
        default=None,
        description="Bank account number (9-18 digits)"
    )
    
    ifsc_code: Optional[str] = Field(
        default=None,
        description="Bank IFSC code (11 characters)"
    )
    
    bank_name: Optional[str] = Field(
        default=None,
        description="Name of the bank"
    )
    
    village: Optional[str] = Field(
        default=None,
        description="Village name"
    )
    
    taluka: Optional[str] = Field(
        default=None,
        description="Taluka name"
    )
    
    district: Optional[str] = Field(
        default=None,
        description="District name"
    )
    
    state: str = Field(
        default="Maharashtra",
        description="State name"
    )
    
    survey_number: Optional[str] = Field(
        default=None,
        description="Land survey number"
    )
    
    land_area: Optional[float] = Field(
        default=None,
        description="Land area in hectares"
    )
    
    aadhaar_number: Optional[str] = Field(
        default=None,
        description="12-digit Aadhaar number"
    )
    
    registration_date: Optional[datetime] = Field(
        default=None,
        description="Date farmer was registered"
    )
    
    status: str = Field(
        default="active",
        description="Farmer status (active/inactive)"
    )
    
    language_preference: str = Field(
        default="hi",
        description="Preferred language (hi/mr/en)"
    )