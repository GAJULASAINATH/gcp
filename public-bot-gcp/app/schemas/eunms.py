# app/schemas/enums.py
from enum import Enum

class UserType(str, Enum):
    """User type enum matching database values exactly"""
    CORPORATE = "corporate"  # Matches DB value (lowercase)
    REAL_ESTATE = "real estate agent"  # Matches DB value exactly (with space)


class CurrentListing(str, Enum):
    """Listing status enum matching database values exactly"""
    AVAILABLE_TO_RENT = "Available to rent"
    BOOKED = "Booked"