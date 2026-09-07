from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
import asyncpg
from api.routes import router as api_router
import os

app = FastAPI(title="3D ULPIN Backend API")

# Allow requests from the React/Streamlit frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    # Initialize asyncpg connection pool
    app.state.pool = await asyncpg.create_pool(
        dsn=os.getenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/ulpin_db")
    )

@app.on_event("shutdown")
async def shutdown():
    await app.state.pool.close()

# Hard-coded Auth/RBAC Stub (Phase 8 Roadmap Split)
def get_current_user(authorization: str = Header("Bearer demo-officer-token")):
    token = authorization.replace("Bearer ", "")
    if token == "demo-officer-token":
        return {"role": "municipal_officer", "user_id": "officer_01"}
    elif token == "demo-citizen-token":
        return {"role": "citizen", "user_id": "citizen_01"}
    raise HTTPException(status_code=401, detail="Invalid token")

@app.post("/api/publish")
async def publish_record(parcel_id: str, user: dict = Depends(get_current_user)):
    if user["role"] != "municipal_officer":
        raise HTTPException(status_code=403, detail="Only municipal officers can publish cadastral objects.")
    return {"status": "Approved and Published", "parcel": parcel_id, "approved_by": user["user_id"]}

# Include the main routes
app.include_router(api_router)
