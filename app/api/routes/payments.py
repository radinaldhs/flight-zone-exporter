from fastapi import APIRouter, Depends, HTTPException, Request
from app.models.payment import PaymentResponse, MidtransWebhook
from app.services.payment_service import PaymentService
from app.api.dependencies import get_current_active_user
from app.models.user import UserInDB

router = APIRouter(prefix="/api/payments", tags=["payments"])


@router.post("/create", response_model=PaymentResponse)
async def create_payment(current_user: UserInDB = Depends(get_current_active_user)):
    """Create Midtrans payment link for subscription"""
    payment_service = PaymentService()

    try:
        payment = payment_service.create_payment(
            user_id=current_user.id,
            user_email=f"{current_user.gis_auth_username}@flightzone.local",
            user_name=current_user.full_name
        )
        return payment
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{payment_id}/status")
async def get_payment_status(
    payment_id: str,
    current_user: UserInDB = Depends(get_current_active_user)
):
    """Check payment status"""
    payment_service = PaymentService()

    try:
        payment = payment_service.check_payment_status(payment_id)

        # Ensure user can only check their own payments
        if payment['user_id'] != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized")

        return payment
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/webhook")
async def midtrans_webhook(request: Request):
    """Handle Midtrans payment notifications"""
    payment_service = PaymentService()

    try:
        notification = await request.json()
        result = payment_service.handle_payment_notification(notification)
        return {"status": "ok", "data": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
