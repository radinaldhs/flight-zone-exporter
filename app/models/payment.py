from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class PaymentCreate(BaseModel):
    user_id: str
    amount: int = 4000000  # IDR
    currency: str = "IDR"
    payment_method: str = "midtrans"


class Payment(BaseModel):
    id: str  # Firestore doc ID
    user_id: str
    midtrans_order_id: str
    midtrans_transaction_id: Optional[str] = None
    amount: int
    currency: str
    status: str  # pending|success|failed|expired
    payment_url: Optional[str] = None  # Snap payment URL
    created_at: datetime
    paid_at: Optional[datetime] = None
    expires_at: datetime  # Payment link expires in 24h


class PaymentResponse(BaseModel):
    payment_id: str
    order_id: str
    payment_url: str
    amount: int
    expires_at: datetime


class MidtransWebhook(BaseModel):
    """Midtrans notification payload"""
    order_id: str
    status_code: str
    gross_amount: str
    signature_key: str
    transaction_status: str
    fraud_status: Optional[str] = None
    payment_type: Optional[str] = None
