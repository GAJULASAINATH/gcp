import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import the router we defined in endpoints/whatsapp.py
from app.api.endpoints import whatsapp

# Initialize the App
app = FastAPI(
    title="PropPanda Chatbot API",
    description="Multi-tenant WhatsApp Chatbot for Real Estate Agents",
    version="1.0.0"
)

# --- CORS MIDDLEWARE ---
# This allows external requests (essential if you add a frontend later)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- ROUTER REGISTRATION ---
# We mount the WhatsApp router under '/api/v1'
# Resulting URL: http://localhost:8000/api/v1/webhook
app.include_router(
    whatsapp.router, 
    prefix="/api/v1", 
    tags=["WhatsApp"]
)

# --- ROOT ENDPOINT ---
# Good for health checks (e.g., "Is the server running?")
@app.get("/")
async def health_check():
    return {
        "status": "active",
        "service": "PropPanda WhatsApp API",
        "version": "1.0.0"
    }

# --- ENTRY POINT ---
# Allows you to run: python app/main.py
if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)