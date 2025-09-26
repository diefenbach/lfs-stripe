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

3. Configure your Stripe API keys in settings.py:
   ```python
   STRIPE_SECRET_KEY = 'your_stripe_secret_key'
   STRIPE_PUBLISHABLE_KEY = 'your_stripe_publishable_key'
   ```

4. Include the URLs in your project's urls.py:
   ```python
   urlpatterns = [
       # ...
       path('stripe/', include('lfs_stripe.urls')),
       # ...
   ]
   ```

## Request Flow 
1. fetch to backend to: /stripe/create-payment-intent/ 
2. API Call to stripe to: confirmCardPayment
3. fetch to backend to: /stripe/create-order
4. Redirect to thank-you page

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

## Notes: 
- create payment intent muss immer im BE aufgerufen werden. Das verlangt Stripe zur Sicherheit, weil so keine Daten im Browser manipuliert werden können. Außerdem liegt nur dort der private key.
- Im BE wird also intent = stripe.PaymentIntent.create(...) aufgerufen mit dem Betrag und dem private key
- Das gibt wiederum ein client secret zurück
- Mit diesem client secrect wird this.stripe.confirmCardPayment(clientSecret, {...}) aufgerufen
- Wenn das erfolgreich ist 
