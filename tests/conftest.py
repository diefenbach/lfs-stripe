"""Fixtures shared by the lfs-stripe tests."""

import pytest
from django.core.management import call_command
from django.test import Client
from django.urls import reverse

from lfs.cart.models import Cart
from lfs.catalog.models import Product
from lfs.customer.models import Customer


@pytest.fixture
def cart_client(db: None, client: Client) -> Client:
    """A client with one product for 37.88 in its cart and a customer with an e-mail address, as before paying."""
    call_command("lfs_init")
    product = Product.objects.create(name="Board", slug="board", sku="B1", price=37.88, active=True)
    client.post(reverse("lfs_add_to_cart"), {"product_id": product.id, "quantity": 1, "action": "add-to-cart"})
    assert Cart.objects.count() == 1
    client.get(reverse("lfs_checkout"))  # creates the customer with its addresses, as in the shop
    customer = Customer.objects.get(session=client.session.session_key)
    customer.set_email_address("kunde@example.invalid")
    return client
