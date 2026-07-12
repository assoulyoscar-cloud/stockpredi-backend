import stripe
from flask import Blueprint, request, jsonify
from middleware.auth_middleware import auth_required
from models.user_store import ensure_user_row
from config import Config
from supabase import create_client

stripe.api_key = Config.STRIPE_SECRET_KEY
stripe_bp = Blueprint("stripe", __name__)


def get_client():
    return create_client(Config.SUPABASE_URL, Config.SUPABASE_SERVICE_KEY)


_RESOLVED_PRICE_ID = None


def _resolve_recurring_price():
    """Retourne un price Stripe recurrent mensuel valide (auto-reparation).

    1. Si STRIPE_PRICE_ID est un price recurrent -> l'utiliser.
    2. Sinon, chercher un price recurrent mensuel actif sur le meme produit.
    3. Sinon, creer un price recurrent 35 EUR/mois sur le produit.
    Le resultat est mis en cache en memoire pour la duree du process.
    """
    global _RESOLVED_PRICE_ID
    if _RESOLVED_PRICE_ID:
        return _RESOLVED_PRICE_ID

    product_id = None
    configured = Config.STRIPE_PRICE_ID
    if configured:
        try:
            price = stripe.Price.retrieve(configured)
            if price.get("recurring"):
                _RESOLVED_PRICE_ID = price["id"]
                return _RESOLVED_PRICE_ID
            product_id = price["product"]
        except stripe.StripeError:
            product_id = None

    if product_id:
        prices = stripe.Price.list(product=product_id, active=True, limit=100)
        for p in prices.get("data", []):
            rec = p.get("recurring")
            if rec and rec.get("interval") == "month":
                _RESOLVED_PRICE_ID = p["id"]
                return _RESOLVED_PRICE_ID

    create_kwargs = {
        "unit_amount": 3500,
        "currency": "eur",
        "recurring": {"interval": "month"},
        "nickname": "StockPredi Mensuel 35EUR (auto)",
    }
    if product_id:
        create_kwargs["product"] = product_id
    else:
        create_kwargs["product_data"] = {"name": "StockPredi Abonnement Mensuel"}
    new_price = stripe.Price.create(**create_kwargs)
    _RESOLVED_PRICE_ID = new_price["id"]
    return _RESOLVED_PRICE_ID


@stripe_bp.route("/create-subscription", methods=["POST"])
@auth_required
def create_subscription():
    """Cree un abonnement Stripe pour l'utilisateur connecte."""
    supabase = get_client()
    try:
        ensure_user_row(supabase, request.user_id, request.user_email)
        # Recupere ou cree le customer Stripe
        user_res = supabase.table("users").select("stripe_customer_id, email")             .eq("id", request.user_id).single().execute()
        user = user_res.data

        customer_id = user.get("stripe_customer_id")
        if not customer_id:
            customer = stripe.Customer.create(email=user["email"])
            customer_id = customer.id
            supabase.table("users").update({"stripe_customer_id": customer_id})                 .eq("id", request.user_id).execute()

        # Cree une session Checkout
        session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=["card"],
            line_items=[{"price": _resolve_recurring_price(), "quantity": 1}],
            mode="subscription",
            success_url=f"{Config.FRONTEND_URL}/dashboard?payment=success",
            cancel_url=f"{Config.FRONTEND_URL}/dashboard?payment=cancelled",
            client_reference_id=request.user_id,
            subscription_data={"trial_period_days": 14}
        )
        return jsonify({"checkout_url": session.url, "session_id": session.id}), 200
    except stripe.StripeError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": "Erreur creation abonnement", "detail": str(e)}), 500


@stripe_bp.route("/cancel-subscription", methods=["POST"])
@auth_required
def cancel_subscription():
    """Annule l'abonnement Stripe de l'utilisateur."""
    supabase = get_client()
    try:
        user_res = supabase.table("users").select("stripe_subscription_id")             .eq("id", request.user_id).single().execute()
        sub_id = user_res.data.get("stripe_subscription_id")
        if not sub_id:
            return jsonify({"error": "Aucun abonnement actif"}), 404

        stripe.Subscription.modify(sub_id, cancel_at_period_end=True)
        supabase.table("users").update({"plan": "cancelling"})             .eq("id", request.user_id).execute()
        return jsonify({"message": "Abonnement annule en fin de periode"}), 200
    except stripe.StripeError as e:
        return jsonify({"error": str(e)}), 400


@stripe_bp.route("/status", methods=["GET"])
@auth_required
def subscription_status():
    """Retourne le statut abonnement de l'utilisateur."""
    supabase = get_client()
    try:
        ensure_user_row(supabase, request.user_id, request.user_email)
        res = supabase.table("users")             .select("plan, stripe_customer_id, stripe_subscription_id")             .eq("id", request.user_id).single().execute()
        return jsonify(res.data), 200
    except Exception as e:
        return jsonify({"error": "Statut introuvable", "detail": str(e)}), 404


@stripe_bp.route("/webhook", methods=["POST"])
def stripe_webhook():
    """Webhook Stripe — mise a jour plan utilisateur."""
    payload = request.get_data()
    sig = request.headers.get("Stripe-Signature", "")
    try:
        event = stripe.Webhook.construct_event(
            payload, sig, Config.STRIPE_WEBHOOK_SECRET
        )
    except stripe.SignatureVerificationError:
        return jsonify({"error": "Signature invalide"}), 400

    supabase = get_client()
    event_type = event["type"]
    data = event["data"]["object"]

    if event_type == "checkout.session.completed":
        user_id = data.get("client_reference_id")
        sub_id = data.get("subscription")
        if user_id and sub_id:
            supabase.table("users").update({
                "stripe_subscription_id": sub_id,
                "plan": "trial"
            }).eq("id", user_id).execute()

    elif event_type == "customer.subscription.updated":
        sub_id = data["id"]
        status = data["status"]
        plan = "active" if status == "active" else ("trial" if status == "trialing" else "inactive")
        supabase.table("users").update({"plan": plan})             .eq("stripe_subscription_id", sub_id).execute()

    elif event_type == "customer.subscription.deleted":
        sub_id = data["id"]
        supabase.table("users").update({
            "plan": "inactive",
            "stripe_subscription_id": None
        }).eq("stripe_subscription_id", sub_id).execute()

    elif event_type in ("invoice.payment_failed", "invoice.payment_action_required"):
        customer_id = data.get("customer")
        if customer_id:
            supabase.table("users").update({"plan": "payment_failed"})                 .eq("stripe_customer_id", customer_id).execute()

    return jsonify({"received": True}), 200
