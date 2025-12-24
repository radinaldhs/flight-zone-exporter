import midtransclient
from app.core.config import settings
from app.core.firebase import get_firestore_client
from datetime import datetime, timedelta
import uuid
import hashlib


class PaymentService:
    def __init__(self):
        self.snap = midtransclient.Snap(
            is_production=settings.MIDTRANS_IS_PRODUCTION,
            server_key=settings.MIDTRANS_SERVER_KEY,
            client_key=settings.MIDTRANS_CLIENT_KEY
        )
        self.db = get_firestore_client()

    def create_payment(self, user_id: str, user_email: str, user_name: str):
        """Create Midtrans Snap payment for monthly subscription"""
        order_id = f"SUB-{user_id[:8]}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

        param = {
            "transaction_details": {
                "order_id": order_id,
                "gross_amount": settings.MONTHLY_SUBSCRIPTION_PRICE
            },
            "customer_details": {
                "first_name": user_name or "Vendor",
                "email": user_email or f"{user_id}@flightzone.local"
            },
            "item_details": [{
                "id": "monthly_subscription",
                "price": settings.MONTHLY_SUBSCRIPTION_PRICE,
                "quantity": 1,
                "name": "Flight Zone Exporter - Monthly Subscription"
            }],
            "expiry": {
                "duration": 24,
                "unit": "hour"
            }
        }

        # Create Snap transaction
        transaction = self.snap.create_transaction(param)

        # Store payment in Firestore
        payment_id = str(uuid.uuid4())
        payment_data = {
            "user_id": user_id,
            "midtrans_order_id": order_id,
            "amount": settings.MONTHLY_SUBSCRIPTION_PRICE,
            "currency": "IDR",
            "status": "pending",
            "payment_url": transaction['redirect_url'],
            "created_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(hours=24)
        }

        self.db.collection('payments').document(payment_id).set(payment_data)

        return {
            "payment_id": payment_id,
            "order_id": order_id,
            "payment_url": transaction['redirect_url'],
            "amount": settings.MONTHLY_SUBSCRIPTION_PRICE,
            "expires_at": payment_data["expires_at"]
        }

    def verify_signature(self, order_id: str, status_code: str, gross_amount: str, signature_key: str) -> bool:
        """Verify Midtrans webhook signature"""
        server_key = settings.MIDTRANS_SERVER_KEY
        string = f"{order_id}{status_code}{gross_amount}{server_key}"
        calculated_signature = hashlib.sha512(string.encode()).hexdigest()
        return calculated_signature == signature_key

    def handle_payment_notification(self, notification: dict):
        """Handle Midtrans webhook notification"""
        order_id = notification.get('order_id')
        transaction_status = notification.get('transaction_status')
        fraud_status = notification.get('fraud_status')

        # Verify signature
        if not self.verify_signature(
            order_id,
            notification.get('status_code'),
            notification.get('gross_amount'),
            notification.get('signature_key')
        ):
            raise ValueError("Invalid signature")

        # Get payment from Firestore
        payments = self.db.collection('payments').where('midtrans_order_id', '==', order_id).get()

        if not payments:
            raise ValueError(f"Payment not found for order_id: {order_id}")

        payment_doc = payments[0]
        payment_data = payment_doc.to_dict()
        user_id = payment_data['user_id']

        # Update payment status based on transaction status
        if transaction_status == 'capture':
            if fraud_status == 'accept':
                status = 'success'
            else:
                status = 'pending'
        elif transaction_status == 'settlement':
            status = 'success'
        elif transaction_status in ['cancel', 'deny', 'expire']:
            status = 'failed'
        elif transaction_status == 'pending':
            status = 'pending'
        else:
            status = 'pending'

        # Update payment in Firestore
        self.db.collection('payments').document(payment_doc.id).update({
            "status": status,
            "midtrans_transaction_id": notification.get('transaction_id'),
            "paid_at": datetime.utcnow() if status == 'success' else None
        })

        # If payment successful, activate subscription
        if status == 'success':
            self._activate_subscription(user_id, payment_doc.id)

        return {"status": status, "user_id": user_id}

    def _activate_subscription(self, user_id: str, payment_id: str):
        """Activate user subscription after successful payment"""
        now = datetime.utcnow()
        end_date = now + timedelta(days=30)  # 30 days subscription

        # Update user subscription status
        self.db.collection('users').document(user_id).update({
            "subscription_status": "active",
            "subscription_end_date": end_date,
            "plan_type": "monthly"
        })

        # Create subscription record
        subscription_id = str(uuid.uuid4())
        subscription_data = {
            "user_id": user_id,
            "plan_name": "monthly_4m",
            "amount": settings.MONTHLY_SUBSCRIPTION_PRICE,
            "start_date": now,
            "end_date": end_date,
            "status": "active",
            "payment_id": payment_id,
            "created_at": now
        }

        self.db.collection('subscriptions').document(subscription_id).set(subscription_data)

    def check_payment_status(self, payment_id: str):
        """Check payment status from Firestore"""
        payment_doc = self.db.collection('payments').document(payment_id).get()

        if not payment_doc.exists:
            raise ValueError("Payment not found")

        return payment_doc.to_dict()
