from fastapi import APIRouter, Depends, HTTPException
from app.api.dependencies import get_current_active_user
from app.models.user import UserInDB
from app.core.firebase import get_firestore_client
from datetime import datetime

router = APIRouter(prefix="/api/subscriptions", tags=["subscriptions"])


@router.get("/status")
async def get_subscription_status(current_user: UserInDB = Depends(get_current_active_user)):
    """Get current user's subscription status"""
    return {
        "is_active": current_user.is_subscription_active(),
        "is_whitelisted": current_user.is_whitelisted,
        "subscription_status": current_user.subscription_status,
        "subscription_end_date": current_user.subscription_end_date,
        "plan_type": current_user.plan_type
    }


@router.get("/history")
async def get_subscription_history(current_user: UserInDB = Depends(get_current_active_user)):
    """Get user's subscription history"""
    db = get_firestore_client()
    subscriptions = db.collection('subscriptions')\
        .where('user_id', '==', current_user.id)\
        .order_by('created_at', direction='DESCENDING')\
        .limit(10)\
        .get()

    return [sub.to_dict() for sub in subscriptions]
