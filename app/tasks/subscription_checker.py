from app.core.firebase import get_firestore_client
from datetime import datetime, timedelta
from app.core.config import settings


def update_expired_subscriptions():
    """
    Background task to check and update expired subscriptions
    Run this daily via cron or scheduler
    """
    db = get_firestore_client()
    now = datetime.utcnow()

    # Get all active subscriptions that have expired
    users = db.collection('users')\
        .where('subscription_status', '==', 'active')\
        .where('subscription_end_date', '<', now)\
        .get()

    moved_to_grace_count = 0
    for user_doc in users:
        user_id = user_doc.id
        # Move to grace period
        db.collection('users').document(user_id).update({
            "subscription_status": "grace_period"
        })
        moved_to_grace_count += 1

    # Get all grace_period subscriptions where grace period has ended
    grace_cutoff = now - timedelta(days=settings.SUBSCRIPTION_GRACE_PERIOD_DAYS)

    users_grace = db.collection('users')\
        .where('subscription_status', '==', 'grace_period')\
        .where('subscription_end_date', '<', grace_cutoff)\
        .get()

    moved_to_expired_count = 0
    for user_doc in users_grace:
        user_id = user_doc.id
        # Move to expired (block access)
        db.collection('users').document(user_id).update({
            "subscription_status": "expired"
        })
        moved_to_expired_count += 1

    return {
        "moved_to_grace": moved_to_grace_count,
        "moved_to_expired": moved_to_expired_count,
        "timestamp": now.isoformat()
    }


if __name__ == "__main__":
    # Allow running this script directly for testing
    result = update_expired_subscriptions()
    print(f"Subscription checker completed:")
    print(f"  - Moved to grace period: {result['moved_to_grace']} users")
    print(f"  - Moved to expired: {result['moved_to_expired']} users")
    print(f"  - Timestamp: {result['timestamp']}")
