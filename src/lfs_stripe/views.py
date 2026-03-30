import logging

from django.conf import settings
from django.http import HttpResponseRedirect, JsonResponse
from django.urls import reverse
import stripe

import lfs.core.utils
from lfs.cart.utils import get_cart
from lfs.core.signals import order_paid, order_submitted
from lfs.order.settings import PAID
from lfs.order.utils import add_order

logger = logging.getLogger("lfs.stripe")


def create_payment_intent(request):
    cart = lfs.cart.utils.get_cart(request)
    if cart is None:
        return HttpResponseRedirect(reverse("lfs_cart"))

    # Set Stripe API key
    stripe.api_key = settings.STRIPE_SECRET_KEY

    try:
        # Get cart and total amount
        cart = get_cart(request)

        # Convert to cents
        amount = cart.get_total_price_gross(request) * 100

        intent = stripe.PaymentIntent.create(
            amount=int(amount),
            currency="eur",
            payment_method_types=["card"],
            metadata={"cart_id": f"{settings.STRIPE_SHOP_NAME}, {cart.id}"},
        )

        return JsonResponse({"clientSecret": intent.client_secret})

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


def create_order(request):
    cart = get_cart(request)
    order = add_order(request)
    logger.info(f"Order created: {order.id}")
    order.state = PAID
    order.save()

    # Update Stripe PaymentIntent with order ID
    stripe.api_key = settings.STRIPE_SECRET_KEY
    payment_intent_id = request.POST.get("payment_intent_id")
    if payment_intent_id:
        try:
            stripe.PaymentIntent.modify(
                payment_intent_id, metadata={"order_number": f"{settings.STRIPE_SHOP_NAME}, {order.number}"}
            )
            logger.info(f"Updated PaymentIntent {payment_intent_id} with order_id: {order.id}")
        except Exception as e:
            logger.error(f"Failed to update PaymentIntent metadata: {e}")

    # Notify the system
    order_submitted.send(sender=order, request=request)
    order_paid.send(sender=order, request=request)

    return JsonResponse({"message": "Payment confirmed"})
