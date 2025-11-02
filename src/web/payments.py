"""Stripe billing integration endpoints."""
from __future__ import annotations

import logging
from typing import Dict, Any

from flask import Blueprint, current_app, jsonify, request, url_for
import stripe

logger = logging.getLogger(__name__)

payments_bp = Blueprint("payments", __name__)


def _stripe_enabled() -> bool:
    return bool(current_app.config.get("STRIPE_ENABLED"))


def _get_plan_catalog() -> Dict[str, Dict[str, Any]]:
    return current_app.config.get("STRIPE_PLANS", {})


@payments_bp.route("/status", methods=["GET"])
def status() -> Any:
    """Return Stripe configuration status."""
    return jsonify({
        "enabled": _stripe_enabled()
    })


@payments_bp.route("/plans", methods=["GET"])
def plans() -> Any:
    """Expose available plans with bilingual labels."""
    if not _stripe_enabled():
        return jsonify({
            "enabled": False,
            "plans": []
        })

    catalog = _get_plan_catalog()
    plans_payload = []
    for plan_id, plan in catalog.items():
        unit_amount = plan.get("custom_amount") or plan.get("amount")
        currency = plan.get("currency")
        plans_payload.append({
            "id": plan_id,
            "price_id": plan["price_id"],
            "mode": plan.get("mode", "subscription"),
            "billing_interval": plan.get("billing_interval"),
            "label_en": plan.get("label_en"),
            "label_ja": plan.get("label_ja"),
            "features_en": plan.get("features_en", []),
            "features_ja": plan.get("features_ja", []),
            "unit_amount": unit_amount,
            "currency": currency,
            "buyout_months": plan.get("buyout_months")
        })

    return jsonify({
        "enabled": True,
        "plans": plans_payload
    })


@payments_bp.route("/checkout", methods=["POST"])
def create_checkout_session() -> Any:
    """Create a Stripe Checkout session for subscription purchase."""
    if not _stripe_enabled():
        return jsonify({"error": "Stripe integration is disabled."}), 503

    payload = request.get_json(silent=True) or {}
    plan_id = payload.get("plan_id")
    customer_email = payload.get("customer_email")

    catalog = _get_plan_catalog()
    plan_config = catalog.get(plan_id)
    if not plan_config:
        return jsonify({"error": "Unknown plan."}), 400

    success_url = (
        payload.get("success_url")
        or current_app.config.get("STRIPE_SUCCESS_URL")
        or url_for("billing_success", _external=True)
    )
    cancel_url = (
        payload.get("cancel_url")
        or current_app.config.get("STRIPE_CANCEL_URL")
        or url_for("billing_cancel", _external=True)
    )

    if not success_url or not cancel_url:
        return jsonify({"error": "Missing success or cancel URL configuration."}), 500

    mode = plan_config.get("mode", "subscription")

    line_item: Dict[str, Any]
    if plan_config.get("price_id"):
        line_item = {
            "price": plan_config["price_id"],
            "quantity": 1,
        }
    else:
        unit_amount = plan_config.get("custom_amount")
        currency = plan_config.get("currency")
        if not unit_amount or not currency:
            return jsonify({"error": "Plan is missing billing amount information."}), 500

        price_data: Dict[str, Any] = {
            "currency": currency,
            "unit_amount": unit_amount,
        }

        product_id = plan_config.get("product_id")
        if product_id:
            price_data["product"] = product_id
        else:
            price_data["product_data"] = {
                "name": plan_config.get("label_en") or plan_id
            }

        line_item = {
            "price_data": price_data,
            "quantity": 1,
        }

    try:
        session = stripe.checkout.Session.create(
            success_url=success_url + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=cancel_url,
            mode=mode,
            line_items=[line_item],
            customer_email=customer_email if isinstance(customer_email, str) else None,
            automatic_tax={"enabled": True},
            metadata={
                "plan_id": plan_id,
                "product": "3d_print_cad_assistant",
                "buyout_months": plan_config.get("buyout_months"),
            }
        )
        return jsonify({
            "checkout_url": session.url,
            "session_id": session.id
        })
    except stripe.error.StripeError as exc:
        logger.exception("Stripe checkout session creation failed: %s", exc)
        return jsonify({"error": str(exc)}), 502


@payments_bp.route("/portal", methods=["POST"])
def create_customer_portal_session() -> Any:
    """Create a billing portal session when Stripe Customer portal is configured."""
    if not _stripe_enabled():
        return jsonify({"error": "Stripe integration is disabled."}), 503

    payload = request.get_json(silent=True) or {}
    customer_id = payload.get("customer_id")
    return_url = payload.get("return_url") or current_app.config.get("STRIPE_SUCCESS_URL")

    if not customer_id:
        return jsonify({"error": "customer_id is required"}), 400

    try:
        session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=return_url
        )
        return jsonify({
            "portal_url": session.url
        })
    except stripe.error.StripeError as exc:
        logger.exception("Stripe portal session creation failed: %s", exc)
        return jsonify({"error": str(exc)}), 502


@payments_bp.route("/webhook", methods=["POST"])
def stripe_webhook() -> Any:
    """Stripe webhook endpoint for subscription lifecycle events."""
    if not _stripe_enabled():
        return jsonify({"error": "Stripe integration is disabled."}), 503

    webhook_secret = current_app.config.get("STRIPE_WEBHOOK_SECRET")
    payload = request.data
    sig_header = request.headers.get("Stripe-Signature")

    if webhook_secret:
        try:
            event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
        except (ValueError, stripe.error.SignatureVerificationError) as exc:
            logger.warning("Stripe webhook signature verification failed: %s", exc)
            return jsonify({"error": "Invalid signature."}), 400
    else:
        try:
            event = stripe.Event.construct_from(request.get_json(force=True), stripe.api_key)
        except ValueError as exc:
            logger.warning("Stripe webhook payload invalid: %s", exc)
            return jsonify({"error": "Invalid payload."}), 400

    event_type = event.get("type")
    logger.info("Received Stripe event: %s", event_type)

    handled_events = {
        "checkout.session.completed": "Checkout completed",
        "customer.subscription.created": "Subscription created",
        "customer.subscription.updated": "Subscription updated",
        "customer.subscription.deleted": "Subscription cancelled"
    }

    if event_type in handled_events:
        logger.info("Stripe event handled: %s", handled_events[event_type])
    else:
        logger.debug("Unhandled Stripe event type: %s", event_type)

    return jsonify({"status": "ok"})
