"""
Payment routes for DodoPayments integration.
Handles checkout, webhooks, and subscription management endpoints.
"""

from flask import Blueprint, request, jsonify, render_template, redirect, url_for
import json

from auth import login_required, get_current_user
from payment_service import payment_service
from config import get_config

config = get_config()

payment_bp = Blueprint('payment', __name__, url_prefix='/payment')


@payment_bp.route('/pricing')
def pricing():
    """Display pricing page"""
    user = get_current_user()
    subscription_status = None

    if user:
        subscription_status = payment_service.get_subscription_status(user['id'])

    return render_template('pricing.html',
                           user=user,
                           subscription_status=subscription_status,
                           is_configured=payment_service.is_configured())


@payment_bp.route('/checkout', methods=['POST'])
@login_required
def create_checkout():
    """Create a checkout session for subscription"""
    user = get_current_user()

    data = request.get_json() or {}
    plan = data.get('plan', 'pro')
    interval = data.get('interval', 'month')

    # Build success/cancel URLs
    base_url = config.BASE_URL
    success_url = f"{base_url}/payment/success?session_id={{session_id}}"
    cancel_url = f"{base_url}/payment/pricing"

    result = payment_service.create_checkout_session(
        user_id=user['id'],
        plan=plan,
        interval=interval,
        success_url=success_url,
        cancel_url=cancel_url
    )

    if 'error' in result:
        return jsonify(result), 400

    return jsonify(result)


@payment_bp.route('/success')
@login_required
def payment_success():
    """Handle successful payment redirect"""
    session_id = request.args.get('session_id')
    user = get_current_user()

    return render_template('payment_success.html',
                           user=user,
                           session_id=session_id)


@payment_bp.route('/webhook', methods=['POST'])
def webhook():
    """Handle DodoPayments webhooks"""
    # Get raw payload for signature verification
    payload = request.get_json()
    signature = request.headers.get('X-Dodo-Signature', '')

    result = payment_service.handle_webhook(payload, signature)

    if 'error' in result:
        return jsonify(result), 400

    return jsonify(result), 200


@payment_bp.route('/status')
@login_required
def subscription_status():
    """Get current user's subscription status"""
    user = get_current_user()
    status = payment_service.get_subscription_status(user['id'])

    if request.headers.get('Accept') == 'application/json':
        return jsonify(status)

    return render_template('subscription_status.html',
                           user=user,
                           status=status)


@payment_bp.route('/cancel', methods=['POST'])
@login_required
def cancel_subscription():
    """Cancel current subscription"""
    user = get_current_user()

    data = request.get_json() or {}
    at_period_end = data.get('at_period_end', True)

    result = payment_service.cancel_subscription(user['id'], at_period_end)

    if 'error' in result:
        return jsonify(result), 400

    return jsonify(result)


@payment_bp.route('/manage')
@login_required
def manage_subscription():
    """Subscription management page"""
    user = get_current_user()
    status = payment_service.get_subscription_status(user['id'])

    return render_template('manage_subscription.html',
                           user=user,
                           status=status)
