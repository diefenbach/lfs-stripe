"""The checkout gets the Stripe publishable key from the shop's settings, not from the package."""

from django.test import override_settings
from django.urls import reverse


@override_settings(STRIPE_PUBLISHABLE_KEY="pk_test_from_settings")
def test_config_returns_the_publishable_key_from_the_settings(client):
    response = client.get(reverse("lfs-stripe:config"))

    assert response.status_code == 200
    assert response.json() == {"publishableKey": "pk_test_from_settings"}
