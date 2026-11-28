# LFS Stripe

A Django Lightning Fast Shop (LFS) payment integration for Stripe.

## Overview

This package provides Stripe payment integration for LFS e-commerce platform. It allows customers to make secure credit card payments through Stripe's payment processing system.

## Features

- Seamless integration with LFS checkout process
- Secure credit card processing via Stripe API
- Support for payment intents
- Client-side card validation

## Installation

1. Install the package:
   ```
   pip install lfs-stripe
   ```

2. Add to your INSTALLED_APPS in settings.py:
   ```python
   INSTALLED_APPS = [
       # ...
       'lfs_stripe',
       # ...
   ]
   ```

3. Configure Stripe in settings.py (best read from environment variables):
   ```python
   STRIPE_SECRET_KEY = os.environ["STRIPE_SECRET_KEY"]            # sk_..., stays on the server
   STRIPE_PUBLISHABLE_KEY = os.environ["STRIPE_PUBLISHABLE_KEY"]  # pk_..., sent to the browser
   STRIPE_SHOP_NAME = "My shop"  # prefix of the cart and order references shown in Stripe
   ```
   Both keys must belong to the same Stripe account.

4. Include the URLs in your project's urls.py:
   ```python
   urlpatterns = [
       # ...
       path('stripe/', include('lfs_stripe.urls')),
       # ...
   ]
   ```

## Request flow

The URLs must be included under `stripe/`, because the checkout script calls these paths.

1. The checkout script fetches the publishable key from `/stripe/config/` and starts Stripe Elements.
2. On payment it calls `/stripe/create-payment-intent/`. The server creates a PaymentIntent for the cart total with
   the secret key and returns its client secret.
3. The browser confirms the payment with Stripe (`confirmCardPayment`) using the client secret.
4. On success it calls `/stripe/create-order/` with the PaymentIntent's id. The server retrieves the PaymentIntent
   from Stripe and creates the paid order only if it succeeded for the cart's total and was made for this cart;
   then it adds the order number to the PaymentIntent. Otherwise it answers 400 and logs the reason.
5. The browser goes to the thank-you page.

Payments are in EUR (fixed in `create_payment_intent`). The PaymentIntent is always created on the server: only there is the secret key, and the amount comes from the cart,
so it cannot be changed in the browser.

## Differences from LFS-PayPal

While both lfs-stripe and lfs-paypal provide payment integration for LFS, there are several key differences:

1. **Payment Processing**: 
   - Stripe processes credit card payments directly on your site (with client-side tokenization)

2. **API Integration**:
   - Stripe uses a modern API with Payment Intents

3. **Payment Methods**:
   - Stripe primarily handles credit card payments directly

4. **User Experience**:
   - Stripe allows customers to stay on your site throughout the checkout process
