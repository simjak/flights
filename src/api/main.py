from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import flights

app = FastAPI(
    title="Flight Search API",
    description="API for searching and tracking flight prices",
    version="1.0.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(flights.router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}
