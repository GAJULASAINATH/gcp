from pydantic import BaseModel, Field
from typing import Optional

class AppointmentInfo(BaseModel):
    email: Optional[str] = Field(None, description="User's email address")
    pass_type: Optional[str] = Field(None, description="Type of pass: EP, SP, WP, Student, Citizen, PR")
    lease_months: Optional[int] = Field(None, description="Lease duration in months (Must be number)")
    viewing_type: Optional[str] = Field(None, description="Virtual or In-person")
    time_preference: Optional[str] = Field(None, description="morning, after lunch, or after work")
    selected_slot: Optional[str] = Field(None, description="The specific date/time user picked from the list")