# routes/subscriptions.py — Phase 4 P1 Monetization (single €35/month pricing)
import os
import logging
from datetime import datetime, timezone
import stripe
from flask import Blueprint, request, jsonify
from middleware.auth_middleware import auth_required
from models.user_store import ensure_user_row
from config import Config
from supabase import create_client

stripe.api_key = Config.STRIPE_SECRET_KEY
subscriptions_bp = Blueprint("subscriptions", __name__)
logger = logging.getLogger("stockpredi.subscriptions")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

@subscriptions_bp.route("/create-session", methods=["POST"])
@auth_required
def create_checkout_session():
    """Create Stripe checkout session for €35/month subscription"""
    user_id = request.user_id
    price_id = os.getenv("STRIPE_PRICE_ID")
    
    if not price_id:
        return jsonify({"error": "STRIPE_PRICE_ID not configured"}), 500
    
    try:
        checkout_session = stripe.checkout.Session.create(
            customer_email=request.user_email,
            payment_method_types=["card"],
            line_items=[{"price": price_id, "quantity": 1}],
            mode="subscription",
            success_url="https://stockpredi.vercel.app/dashboard?session_id={CHECKOUT_SESSION_ID}",
            cancel_url="https://stockpredi.vercel.app/pricing",
        )
        
        return jsonify({"url": checkout_session.url}), 200
    except Exception as e:
        logger.error(f"Checkout error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@subscriptions_bp.route("/webhook", methods=["POST"])
def handle_webhook():
    """Handle Stripe webhook events"""
    payload = request.get_data()
    sig_header = request.headers.get("Stripe-Signature")
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
    
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except ValueError:
        return jsonify({"error": "Invalid payload"}), 400
    except stripe.error.SignatureVerificationError:
        return jsonify({"error": "Invalid signature"}), 400
    
    if event["type"] == "customer.subscription.created":
        subscription = event["data"]["object"]
        customer_email = subscription.get("billing_details", {}).get("email")
        if customer_email:
            ensure_user_row(customer_email)
            supabase.table("users").update({
                "stripe_subscription_id": subscription["id"],
                "stripe_subscription_status": subscription["status"],
                "subscription_started_at": datetime.now(timezone.utc).isoformat()
            }).eq("email", customer_email).execute()
        
        supabase.table("subscription_logs").insert({
            "event_type": "subscription.created",
            "customer_email": customer_email,
            "subscription_id": subscription["id"],
            "metadata": subscription
        }).execute()
    
    elif event["type"] == "customer.subscription.updated":
        subscription = event["data"]["object"]
        customer_email = subscription.get("billing_details", {}).get("email")
        if customer_email:
            supabase.table("users").update({
                "stripe_subscription_status": subscription["status"]
            }).eq("email", customer_email).execute()
        
        supabase.table("subscription_logs").insert({
            "event_type": "subscription.updated",
            "customer_email": customer_email,
            "subscription_id": subscription["id"],
            "metadata": subscription
        }).execute()
    
    elif event["type"] == "customer.subscription.deleted":
        subscription = event["data"]["object"]
        customer_email = subscription.get("billing_details", {}).get("email")
        if customer_email:
            supabase.table("users").update({
                "stripe_subscription_status": "canceled",
                "subscription_ended_at": datetime.now(timezone.utc).isoformat()
            }).eq("email", customer_email).execute()
        
        supabase.table("subscription_logs").insert({
            "event_type": "subscription.deleted",
            "customer_email": customer_email,
            "subscription_id": subscription["id"],
            "metadata": subscription
        }).execute()
    
    return jsonify({"status": "received"}), 200

@subscriptions_bp.route("/tier", methods=["GET"])
@auth_required
def get_subscription_tier():
    """Get current user subscription status"""
    user_id = request.user_id
    
    try:
        response = supabase.table("users").select("stripe_subscription_status").eq("id", user_id).execute()
        if response.data:
            status = response.data[0].get("stripe_subscription_status", "free")
            return jsonify({"status": status}), 200
        return jsonify({"status": "free"}), 200
    except Exception as e:
        logger.error(f"Error fetching subscription: {str(e)}")
        return jsonify({"error": str(e)}), 500
