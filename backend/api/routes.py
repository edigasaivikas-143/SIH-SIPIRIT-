from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from typing import Optional

router = APIRouter()

# Dependency stub for getting the asyncpg pool (implemented in main.py or database/connection.py)
async def get_db_pool():
    from main import app
    return app.state.pool

@router.get("/api/parcels/{ulpin_3d}")
async def get_3d_parcel(ulpin_3d: str, pool = Depends(get_db_pool)):
    async with pool.acquire() as conn:
        record = await conn.fetchrow(
            "SELECT parcel_3d_id, z_min, z_max, space_class, unit_id FROM space_3d WHERE parcel_3d_id = $1", 
            ulpin_3d
        )
        if not record:
            raise HTTPException(status_code=404, detail="3D Parcel not found")
        return dict(record)

@router.post("/api/properties")
async def submit_property(
    ulpin: str = Form(...),
    propertyName: str = Form(...),
    propertyType: str = Form(...),
    blueprint: UploadFile = File(...),
    pool = Depends(get_db_pool)
):
    # Generates the 3D ULPIN extension and simulates a database write
    generated_3d_ulpin = f"{ulpin}-F01-V-PRV-001-V01"
    
    async with pool.acquire() as conn:
        # Simulate inserting the new processed property
        await conn.execute(
            """INSERT INTO space_3d (parcel_3d_id, parent_ulpin, z_min, z_max, space_class, unit_id) 
               VALUES ($1, $2, 0.0, 3.5, 'V', '001') ON CONFLICT DO NOTHING""",
            generated_3d_ulpin, ulpin
        )

    return {
        "three_d_ulpin": generated_3d_ulpin,
        "blueprint_url": f"https://storage.example.com/{blueprint.filename}",
        "model_url": "https://storage.example.com/generated_model.glb",
        "property_details": {
            "propertyName": propertyName,
            "propertyType": propertyType,
            "status": "Processed and DB updated"
        }
    }
