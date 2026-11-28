"""The checkout against Stripe itself, with Stripe's test cards: what the mocked tests cannot show.

Runs only with a test secret key in STRIPE_TEST_SECRET_KEY (a Stripe sandbox or test mode; never a live key) and
network access; otherwise skipped. The browser's part, confirmCardPayment, is done on the server with Stripe's test
payment methods (pm_card_*), so the shop's own views and the real Stripe objects are what is tested.
"""

import os

import pytest
import stripe
from django.core import mail
from django.test import override_settings
from django.urls import reverse

from lfs.order.models import Order
from lfs.order.settings import PAID

KEY = os.environ.get("STRIPE_TEST_SECRET_KEY", "")
SHOP = "lfs-stripe tests"

pytestmark = [
    pytest.mark.skipif(not KEY.startswith("sk_test_"), reason="needs a Stripe test key in STRIPE_TEST_SECRET_KEY"),
    pytest.mark.usefixtures("stripe_settings"),
]


@pytest.fixture
def stripe_settings():
    with override_settings(STRIPE_SECRET_KEY=KEY, STRIPE_SHOP_NAME=SHOP):
        yield


def pay(client, card: str | None) -> str:
    """Create the PaymentIntent through the shop and confirm it with the test payment method ``card``.

    Returns the PaymentIntent's id. ``card=None`` leaves it unconfirmed; a declined card leaves it unpaid.
    """
    response = client.post(reverse("lfs-stripe:create_payment_intent"))
    assert response.status_code == 200, response.content
    intent_id = response.json()["clientSecret"].split("_secret_")[0]
    if card:
        stripe.api_key = KEY
        try:
            stripe.PaymentIntent.confirm(intent_id, payment_method=card)
        except stripe.CardError:
            pass
    return intent_id


def create_order(client, intent_id: str):
    return client.post(reverse("lfs-stripe:create_order"), {"payment_intent_id": intent_id})


def test_visa_creates_a_paid_order_and_marks_the_payment_with_it(cart_client):
    intent_id = pay(cart_client, "pm_card_visa")

    response = create_order(cart_client, intent_id)

    assert response.status_code == 200
    order = Order.objects.get()
    assert order.state == PAID
    assert mail.outbox
    payment = stripe.PaymentIntent.retrieve(intent_id)
    assert payment.amount == 3788
    assert payment.metadata["order_number"] == f"{SHOP}, {order.number}"


@pytest.mark.parametrize(
    "card",
    [
        pytest.param("pm_card_chargeDeclined", id="declined"),
        pytest.param("pm_card_chargeDeclinedInsufficientFunds", id="insufficient funds"),
        pytest.param("pm_card_chargeDeclinedExpiredCard", id="expired"),
        pytest.param("pm_card_threeDSecure2Required", id="3-D Secure not completed"),
        pytest.param(None, id="not confirmed"),
    ],
)
def test_unpaid_payment_creates_no_order(cart_client, card):
    intent_id = pay(cart_client, card)

    response = create_order(cart_client, intent_id)

    assert response.status_code == 400
    assert not Order.objects.exists()
    assert mail.outbox == []


def test_made_up_payment_creates_no_order(cart_client):
    response = create_order(cart_client, "pi_made_up")

    assert response.status_code == 400
    assert not Order.objects.exists()
