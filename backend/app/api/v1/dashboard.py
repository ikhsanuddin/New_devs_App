from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any
from app.services.cache import get_revenue_summary
from app.services.reservations import list_properties
from app.core.auth import authenticate_request as get_current_user

router = APIRouter()

def _tenant_of(current_user) -> str:
    tenant_id = getattr(current_user, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=403, detail="User has no tenant")
    return tenant_id


@router.get("/dashboard/properties")
async def get_dashboard_properties(current_user: dict = Depends(get_current_user)):
    return await list_properties(_tenant_of(current_user))


@router.get("/dashboard/summary")
async def get_dashboard_summary(
    property_id: str,
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    
    tenant_id = _tenant_of(current_user)

    revenue_data = await get_revenue_summary(property_id, tenant_id)

    return {
        "property_id": revenue_data['property_id'],
        "total_revenue": revenue_data['total'],  # decimal string, rounded to cents once; never a float
        "currency": revenue_data['currency'],
        "reservations_count": revenue_data['count']
    }
