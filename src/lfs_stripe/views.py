"""Views of the Stripe checkout: the publishable key, the PaymentIntent for the cart, and the order once paid."""

import logging

from django.conf import settings
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect, JsonResponse
from django.urls import reverse
import stripe

from lfs.cart.models import Cart
from lfs.cart.utils import get_cart
from lfs.core.signals import order_paid, order_submitted
from lfs.order.settings import PAID
from lfs.order.utils import add_order

logger = logging.getLogger("lfs.stripe")

CURRENCY = "eur"


def amount_in_cents(request: HttpRequest, cart: Cart) -> int:
    """Return the cart's gross total in cents, as Stripe expects it (rounded, so 37.88 is 3788 and not 3787)."""
    return round(cart.get_total_price_gross(request) * 100)


def cart_reference(cart: Cart) -> str:
    """Return the reference of ``cart`` stored in the PaymentIntent's metadata, which ties the payment to the cart."""
    return f"{settings.STRIPE_SHOP_NAME}, {cart.id}"


def config(request: HttpRequest) -> JsonResponse:
    """Return the shop's Stripe publishable key, which the checkout JavaScript needs to start Stripe."""
    return JsonResponse({"publishableKey": settings.STRIPE_PUBLISHABLE_KEY})


def create_payment_intent(request: HttpRequest) -> HttpResponse:
    """Create a PaymentIntent for the cart's total at Stripe and return its client secret to the checkout script."""
    cart = get_cart(request)
    if cart is None:
        return HttpResponseRedirect(reverse("lfs_cart"))

    stripe.api_key = settings.STRIPE_SECRET_KEY
    try:
        intent = stripe.PaymentIntent.create(
            amount=amount_in_cents(request, cart),
            currency=CURRENCY,
            payment_method_types=["card"],
            metadata={"cart_id": cart_reference(cart)},
        )
    except stripe.StripeError as error:
        logger.exception("Creating the PaymentIntent for cart %s failed", cart.id)
        return JsonResponse({"error": str(error)}, status=400)

    return JsonResponse({"clientSecret": intent.client_secret})


def payment_problem(request: HttpRequest, cart: Cart, payment_intent_id: str) -> str | None:
    """Return why the PaymentIntent ``payment_intent_id`` does not pay ``cart``, or None if it does.

    Asks Stripe: the PaymentIntent must have succeeded, for the cart's total in euros, be the one created for this
    cart, and not have paid an order yet.
    """
    try:
        intent = stripe.PaymentIntent.retrieve(payment_intent_id)
    except stripe.StripeError:
        logger.exception("Retrieving PaymentIntent %s failed", payment_intent_id)
        return "unknown payment"

    metadata = intent.metadata.to_dict() if intent.metadata else {}
    if intent.status != "succeeded":
        return f"status {intent.status}"
    if intent.amount != amount_in_cents(request, cart) or intent.currency != CURRENCY:
        return f"amount {intent.amount} {intent.currency} does not match the cart"
    if metadata.get("cart_id") != cart_reference(cart):
        return f"made for {metadata.get('cart_id')!r}"
    if metadata.get("order_number"):
        return f"already paid order {metadata['order_number']!r}"
    return None


def create_order(request: HttpRequest) -> JsonResponse:
    """Create the paid order for the cart, once Stripe confirms that the posted PaymentIntent paid it.

    Refuses (400, no order) when no PaymentIntent is posted or ``payment_problem`` finds one; each refusal is logged.
    On success sends ``order_submitted`` and ``order_paid`` and adds the order number to the PaymentIntent.
    """
    cart = get_cart(request)
    payment_intent_id = request.POST.get("payment_intent_id")
    if cart is None or not payment_intent_id:
        logger.warning("Stripe order refused: no cart or no PaymentIntent (cart %s)", cart and cart.id)
        return JsonResponse({"error": "The payment could not be verified."}, status=400)

    stripe.api_key = settings.STRIPE_SECRET_KEY
    problem = payment_problem(request, cart, payment_intent_id)
    if problem:
        logger.warning("Stripe order refused for cart %s, PaymentIntent %s: %s", cart.id, payment_intent_id, problem)
        return JsonResponse({"error": "The payment could not be verified."}, status=400)

    order = add_order(request)
    order.state = PAID
    order.save()
    logger.info("Order %s created for PaymentIntent %s", order.number, payment_intent_id)

    try:
        stripe.PaymentIntent.modify(
            payment_intent_id, metadata={"order_number": f"{settings.STRIPE_SHOP_NAME}, {order.number}"}
        )
    except stripe.StripeError:
        logger.exception("Adding order %s to PaymentIntent %s failed", order.number, payment_intent_id)

    order_submitted.send(sender=order, request=request)
    order_paid.send(sender=order, request=request)

    return JsonResponse({"message": "Payment confirmed"})
