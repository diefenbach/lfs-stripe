"""/stripe/create-order/ creates a paid order only for a PaymentIntent that Stripe confirms as paid for this cart.

Stripe is the boundary: ``stripe.PaymentIntent.retrieve`` is replaced by what Stripe would answer.
"""

import pytest
import stripe
from django.core import mail
from django.core.management import call_command
from django.test import override_settings
from django.urls import reverse

from lfs.cart.models import Cart
from lfs.catalog.models import Product
from lfs.customer.models import Customer
from lfs.order.models import Order
from lfs.order.settings import PAID

SHOP = "Test shop"


@pytest.fixture
def cart_client(db, client):
    """A client with one product for 37.88 in its cart."""
    call_command("lfs_init")
    product = Product.objects.create(name="Board", slug="board", sku="B1", price=37.88, active=True)
    client.post(reverse("lfs_add_to_cart"), {"product_id": product.id, "quantity": 1, "action": "add-to-cart"})
    assert Cart.objects.count() == 1
    client.get(reverse("lfs_checkout"))  # creates the customer with its addresses, as in the shop
    customer = Customer.objects.get(session=client.session.session_key)
    customer.set_email_address("kunde@example.invalid")
    return client


def intent(status: str = "succeeded", amount: int = 3788, currency: str = "eur", cart: Cart | None = None, **metadata):
    """Return a PaymentIntent as Stripe sends it back."""
    cart = cart or Cart.objects.get()
    return stripe.PaymentIntent.construct_from(
        {
            "id": "pi_test",
            "object": "payment_intent",
            "status": status,
            "amount": amount,
            "currency": currency,
            "metadata": {"cart_id": f"{SHOP}, {cart.id}", **metadata},
        },
        "sk_test",
    )


def create_order(client, mocker, answer, payment_intent_id: str | None = "pi_test"):
    """Post to /stripe/create-order/ the way the checkout script does, with Stripe answering ``answer``."""
    mocker.patch("stripe.PaymentIntent.retrieve", return_value=answer)
    mocker.patch("stripe.PaymentIntent.modify")
    data = {"payment_intent_id": payment_intent_id} if payment_intent_id else {}
    return client.post(reverse("lfs-stripe:create_order"), data)


@override_settings(STRIPE_SHOP_NAME=SHOP, STRIPE_SECRET_KEY="sk_test")
def test_paid_intent_of_the_cart_creates_a_paid_order(cart_client, mocker):
    response = create_order(cart_client, mocker, intent())

    assert response.status_code == 200
    order = Order.objects.get()
    assert order.state == PAID
    assert order.price == pytest.approx(37.88)


@override_settings(STRIPE_SHOP_NAME=SHOP, STRIPE_SECRET_KEY="sk_test")
def test_without_a_payment_intent_no_order_is_created(cart_client, mocker):
    response = create_order(cart_client, mocker, intent(), payment_intent_id=None)

    assert response.status_code == 400
    assert not Order.objects.exists()
    assert mail.outbox == []


@override_settings(STRIPE_SHOP_NAME=SHOP, STRIPE_SECRET_KEY="sk_test")
@pytest.mark.parametrize(
    "answer",
    [
        pytest.param({"status": "requires_payment_method"}, id="not paid"),
        pytest.param({"status": "processing"}, id="still processing"),
        pytest.param({"amount": 100}, id="smaller amount"),
        pytest.param({"currency": "usd"}, id="other currency"),
    ],
)
def test_intent_that_does_not_pay_the_cart_creates_no_order(cart_client, mocker, answer):
    response = create_order(cart_client, mocker, intent(**answer))

    assert response.status_code == 400
    assert not Order.objects.exists()
    assert mail.outbox == []


@override_settings(STRIPE_SHOP_NAME=SHOP, STRIPE_SECRET_KEY="sk_test")
def test_intent_of_another_cart_creates_no_order(cart_client, mocker):
    other = Cart.objects.create(session="other")
    response = create_order(cart_client, mocker, intent(cart=other))

    assert response.status_code == 400
    assert not Order.objects.exists()


@override_settings(STRIPE_SHOP_NAME=SHOP, STRIPE_SECRET_KEY="sk_test")
def test_intent_that_already_paid_an_order_creates_no_second_one(cart_client, mocker):
    response = create_order(cart_client, mocker, intent(order_number=f"{SHOP}, 1001"))

    assert response.status_code == 400
    assert not Order.objects.exists()


@override_settings(STRIPE_SHOP_NAME=SHOP, STRIPE_SECRET_KEY="sk_test")
def test_unknown_intent_creates_no_order(cart_client, mocker):
    mocker.patch("stripe.PaymentIntent.retrieve", side_effect=stripe.InvalidRequestError("No such payment_intent", "id"))

    response = cart_client.post(reverse("lfs-stripe:create_order"), {"payment_intent_id": "pi_forged"})

    assert response.status_code == 400
    assert not Order.objects.exists()
