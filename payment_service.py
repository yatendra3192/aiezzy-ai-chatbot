"""
DodoPayments integration service for AIezzy.
Handles subscription management, checkout sessions, and webhooks.
"""

import os
from datetime import datetime
from typing import Dict, Optional
from dodopayments import DodoPayments

from models_v2 import db, User, Subscription
from quota_service import quota_service


class PaymentService:
    """Service for managing DodoPayments integration"""

    def __init__(self):
        self.api_key = os.environ.get('DODO_PAYMENTS_API_KEY')
        self.webhook_secret = os.environ.get('DODO_PAYMENTS_WEBHOOK_SECRET')
        self.environment = os.environ.get('DODO_PAYMENTS_ENV', 'test_mode')

        # Product IDs from DodoPayments dashboard
        self.products = {
            'pro_monthly': os.environ.get('DODO_PRODUCT_PRO_MONTHLY'),
            'pro_yearly': os.environ.get('DODO_PRODUCT_PRO_YEARLY'),
            'enterprise_monthly': os.environ.get('DODO_PRODUCT_ENTERPRISE_MONTHLY'),
            'enterprise_yearly': os.environ.get('DODO_PRODUCT_ENTERPRISE_YEARLY'),
        }

        self.client = None
        if self.api_key:
            self.client = DodoPayments(
                bearer_token=self.api_key,
                environment=self.environment
            )

    def is_configured(self) -> bool:
        """Check if DodoPayments is properly configured"""
        return self.client is not None and self.api_key is not None

    def create_checkout_session(
        self,
        user_id: int,
        plan: str,
        interval: str = 'month',
        success_url: str = None,
        cancel_url: str = None
    ) -> Dict:
        """
        Create a DodoPayments checkout session for subscription.

        Args:
            user_id: User ID
            plan: Plan name (pro, enterprise)
            interval: Billing interval (month, year)
            success_url: Redirect URL after successful payment
            cancel_url: Redirect URL if user cancels

        Returns:
            dict: Checkout session data with URL
        """
        if not self.is_configured():
            return {'error': 'Payment service not configured'}

        # Get user
        user = User.query.get(user_id)
        if not user:
            return {'error': 'User not found'}

        # Get product ID
        product_key = f"{plan}_{interval}ly"
        product_id = self.products.get(product_key)

        if not product_id:
            return {'error': f'Invalid plan: {plan} ({interval})'}

        try:
            # Create checkout session with DodoPayments
            checkout_response = self.client.checkout_sessions.create(
                product_cart=[{
                    'product_id': product_id,
                    'quantity': 1
                }],
                customer={
                    'email': user.email,
                    'name': user.full_name or user.username
                },
                metadata={
                    'user_id': str(user_id),
                    'plan': plan,
                    'interval': interval
                },
                success_url=success_url,
                cancel_url=cancel_url
            )

            return {
                'success': True,
                'session_id': checkout_response.session_id,
                'checkout_url': checkout_response.url
            }

        except Exception as e:
            print(f"DodoPayments checkout error: {e}")
            return {'error': str(e)}

    def handle_webhook(self, payload: Dict, signature: str) -> Dict:
        """
        Handle DodoPayments webhook events.

        Args:
            payload: Webhook payload
            signature: Webhook signature for verification

        Returns:
            dict: Processing result
        """
        if not self.is_configured():
            return {'error': 'Payment service not configured'}

        try:
            event_type = payload.get('type')
            data = payload.get('data', {})

            if event_type == 'subscription.created':
                return self._handle_subscription_created(data)
            elif event_type == 'subscription.active':
                return self._handle_subscription_active(data)
            elif event_type == 'subscription.cancelled':
                return self._handle_subscription_cancelled(data)
            elif event_type == 'subscription.expired':
                return self._handle_subscription_expired(data)
            elif event_type == 'payment.succeeded':
                return self._handle_payment_succeeded(data)
            elif event_type == 'payment.failed':
                return self._handle_payment_failed(data)
            else:
                return {'success': True, 'message': f'Unhandled event: {event_type}'}

        except Exception as e:
            print(f"Webhook processing error: {e}")
            return {'error': str(e)}

    def _handle_subscription_created(self, data: Dict) -> Dict:
        """Handle new subscription creation"""
        try:
            metadata = data.get('metadata', {})
            user_id = int(metadata.get('user_id', 0))
            plan = metadata.get('plan', 'pro')
            interval = metadata.get('interval', 'month')

            if not user_id:
                return {'error': 'No user_id in metadata'}

            user = User.query.get(user_id)
            if not user:
                return {'error': 'User not found'}

            # Create subscription record
            subscription = Subscription(
                user_id=user_id,
                dodo_customer_id=data.get('customer_id'),
                dodo_subscription_id=data.get('subscription_id'),
                dodo_product_id=data.get('product_id'),
                plan=plan,
                status='pending',
                interval=interval,
                amount=data.get('amount'),
                currency=data.get('currency', 'USD')
            )

            db.session.add(subscription)
            db.session.commit()

            return {'success': True, 'subscription_id': subscription.id}

        except Exception as e:
            db.session.rollback()
            return {'error': str(e)}

    def _handle_subscription_active(self, data: Dict) -> Dict:
        """Handle subscription becoming active"""
        try:
            subscription_id = data.get('subscription_id')

            subscription = Subscription.query.filter_by(
                dodo_subscription_id=subscription_id
            ).first()

            if not subscription:
                # Create if not exists (from direct signup)
                metadata = data.get('metadata', {})
                user_id = int(metadata.get('user_id', 0))
                if user_id:
                    subscription = Subscription(
                        user_id=user_id,
                        dodo_subscription_id=subscription_id,
                        plan=metadata.get('plan', 'pro'),
                        interval=metadata.get('interval', 'month')
                    )
                    db.session.add(subscription)
                else:
                    return {'error': 'Subscription not found'}

            # Update subscription status
            subscription.status = 'active'
            subscription.current_period_start = datetime.utcnow()

            # Parse period end from webhook data
            if data.get('current_period_end'):
                subscription.current_period_end = datetime.fromisoformat(
                    data['current_period_end'].replace('Z', '+00:00')
                )

            # Update user tier
            user = User.query.get(subscription.user_id)
            if user:
                user.tier = subscription.plan
                db.session.commit()

            return {'success': True}

        except Exception as e:
            db.session.rollback()
            return {'error': str(e)}

    def _handle_subscription_cancelled(self, data: Dict) -> Dict:
        """Handle subscription cancellation"""
        try:
            subscription_id = data.get('subscription_id')

            subscription = Subscription.query.filter_by(
                dodo_subscription_id=subscription_id
            ).first()

            if subscription:
                subscription.status = 'cancelled'
                subscription.cancelled_at = datetime.utcnow()
                subscription.cancel_at_period_end = data.get('cancel_at_period_end', True)

                # If immediate cancellation, downgrade user
                if not subscription.cancel_at_period_end:
                    user = User.query.get(subscription.user_id)
                    if user:
                        user.tier = 'free'

                db.session.commit()

            return {'success': True}

        except Exception as e:
            db.session.rollback()
            return {'error': str(e)}

    def _handle_subscription_expired(self, data: Dict) -> Dict:
        """Handle subscription expiration"""
        try:
            subscription_id = data.get('subscription_id')

            subscription = Subscription.query.filter_by(
                dodo_subscription_id=subscription_id
            ).first()

            if subscription:
                subscription.status = 'expired'

                # Downgrade user to free tier
                user = User.query.get(subscription.user_id)
                if user:
                    user.tier = 'free'

                db.session.commit()

            return {'success': True}

        except Exception as e:
            db.session.rollback()
            return {'error': str(e)}

    def _handle_payment_succeeded(self, data: Dict) -> Dict:
        """Handle successful payment"""
        # Payment succeeded, subscription should be active
        return {'success': True}

    def _handle_payment_failed(self, data: Dict) -> Dict:
        """Handle failed payment"""
        try:
            subscription_id = data.get('subscription_id')

            if subscription_id:
                subscription = Subscription.query.filter_by(
                    dodo_subscription_id=subscription_id
                ).first()

                if subscription:
                    subscription.status = 'past_due'
                    db.session.commit()

            return {'success': True}

        except Exception as e:
            db.session.rollback()
            return {'error': str(e)}

    def get_user_subscription(self, user_id: int) -> Optional[Subscription]:
        """Get active subscription for user"""
        subscription = Subscription.query.filter_by(
            user_id=user_id
        ).order_by(Subscription.created_at.desc()).first()

        if subscription and subscription.is_active():
            return subscription

        return None

    def cancel_subscription(self, user_id: int, at_period_end: bool = True) -> Dict:
        """
        Cancel user subscription.

        Args:
            user_id: User ID
            at_period_end: If True, cancel at end of billing period

        Returns:
            dict: Cancellation result
        """
        if not self.is_configured():
            return {'error': 'Payment service not configured'}

        subscription = self.get_user_subscription(user_id)
        if not subscription:
            return {'error': 'No active subscription found'}

        try:
            # Cancel via DodoPayments API
            self.client.subscriptions.cancel(
                subscription_id=subscription.dodo_subscription_id
            )

            # Update local record
            subscription.cancel_at_period_end = at_period_end
            if not at_period_end:
                subscription.status = 'cancelled'
                subscription.cancelled_at = datetime.utcnow()

                user = User.query.get(user_id)
                if user:
                    user.tier = 'free'

            db.session.commit()

            return {'success': True}

        except Exception as e:
            db.session.rollback()
            return {'error': str(e)}

    def get_subscription_status(self, user_id: int) -> Dict:
        """Get subscription status for user"""
        user = User.query.get(user_id)
        if not user:
            return {'error': 'User not found'}

        subscription = self.get_user_subscription(user_id)

        return {
            'user_id': user_id,
            'tier': user.tier,
            'has_active_subscription': subscription is not None,
            'subscription': subscription.to_dict() if subscription else None,
            'quota_status': quota_service.get_user_quota_status(user_id)
        }


# Global payment service instance
payment_service = PaymentService()
