# app/schemas/property_search.py
from pydantic import BaseModel, Field
from typing import Optional

class PropertySearchFilters(BaseModel):
    """
    Structured extraction of user preferences for property search.
    The AI will populate this based on the conversation.
    """
    
    # --- 1. CORE REQUIREMENTS ---
    location_query: Optional[str] = Field(
        None, 
        description="Target area, MRT station, or region name (e.g., 'Bedok', 'Yio Chu Kang')."
    )
    budget_max: Optional[int] = Field(
        None, 
        description="Maximum monthly rental budget in SGD. If user says 'around 2k', put 2000."
    )
    move_in_date: Optional[str] = Field(
        None, 
        description="Target move-in date in ISO format YYYY-MM-DD."
    )

    # --- 2. DEMOGRAPHICS (Crucial for filtering) ---
    tenant_gender: Optional[str] = Field(
        None, 
        description="Gender of the tenant (Male, Female, Couple). DB values include 'any', 'male', 'female'."
    )
    tenant_nationality: Optional[str] = Field(
        None, 
        description="Nationality of the tenant (e.g., Indian, Malaysian). Needed for 'nationality_preferences'."
    )
    
    # --- 3. UNIT SPECIFICS ---
    room_type: Optional[str] = Field(
        None, 
        description="Type of room. Map 'Master' to 'Master', 'Common' or 'No Attached Bath' to 'Common'."
    )
    needs_ensuite: Optional[bool] = Field(
        None, 
        description="True if user explicitly asks for an attached/private bathroom."
    )

    # --- 4. AMENITIES & POLICIES ---
    needs_cooking: Optional[bool] = Field(
        None, 
        description="True if user needs to cook. Checks 'cooking_allowed' and 'gas_stove'."
    )
    has_pets: Optional[bool] = Field(
        None, 
        description="True if user has pets. Checks 'pet_policy' for 'Allowed'."
    )
    needs_gym: Optional[bool] = Field(
        None, 
        description="True if user asks for gym access."
    )
    needs_pool: Optional[bool] = Field(
        None, 
        description="True if user asks for a swimming pool."
    )
    needs_visitor_allowance: Optional[bool] = Field(
        None, 
        description="True if user asks about bringing guests. Checks 'visitor_policy'."
    )
    needs_wifi: Optional[bool] = Field(
        None,
        description="True if user asks for Wifi included."
    )
    environment: Optional[str] = Field(
        None, 
        description="Specific living environment preference: 'Female' (Ladies only), 'Male' (Men only), or 'Mixed'."
    )