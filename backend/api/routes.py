from fastapi import APIRouter, Depends
from database.connection import get_db_pool

router = APIRouter()

@router.get("/api/parcels/{ulpin_3d}")
async def get_3d_parcel(ulpin_3d: str, pool = Depends(get_db_pool)):
    async with pool.acquire() as conn:
        record = await conn.fetchrow(
            "SELECT parcel_3d_id, z_min, z_max, status FROM space_3d WHERE parcel_3d_id = $1", 
            ulpin_3d
        )
        return dict(record) if record else {"error": "Not found"}
