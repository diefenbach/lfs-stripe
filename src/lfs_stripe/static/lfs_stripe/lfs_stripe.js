class StripeCheckoutHandler {
    constructor() {
        this.stripe = null;
        this.elements = null;
        this.cardNumberElement = null;
        this.cardExpiryElement = null;
        this.cardCvcElement = null;
        this.creditCardForm = null;
        
        this.initialize();
    }

    initialize() {
        // Only initialize if we have a credit card form
        this.creditCardForm = document.querySelector('.creditcard-form');
        if (!this.creditCardForm) {
            return;
        }

        this.stripe = Stripe('pk_test_51RTKpW6d4o9XkCFXTgKjU8BQUQ6pkA8FH5y4BGmgnejBn5hQEHU8JK0g8ikkIjxxwHK3N9xKV7dWLHJDAnQKPgkn00z5BISmCm');
        this.elements = this.stripe.elements();

        this.cardNumberElement = this.elements.create('cardNumber');
        this.cardExpiryElement = this.elements.create('cardExpiry');
        this.cardCvcElement = this.elements.create('cardCvc');

        this.cardNumberElement.mount('#card-number-element');
        this.cardExpiryElement.mount('#card-expiry-element');
        this.cardCvcElement.mount('#card-cvc-element');

        // Error handling für alle Elemente
        [this.cardNumberElement, this.cardExpiryElement, this.cardCvcElement].forEach(element => {
            element.on('change', ({error}) => {
                this.displayError(error ? error.message : '');
            });
        });

        // Form submit
        this.creditCardForm.addEventListener('submit', (event) => this.handleFormSubmit(event));
    }

    async handleFormSubmit(event) {
        event.preventDefault();
                            
        // Get form data to send to the backend
        const formData = new FormData(this.creditCardForm);
    
        // Convert FormData to JSON object
        const formDataObj = Object.fromEntries(formData.entries());
        const csrfToken = getCsrfToken();

        try {
            // Payment Intent vom Backend holen
            const clientSecret = await this.createPaymentIntent(formData, csrfToken);
            
            if (clientSecret) {
                const paymentResult = await this.confirmPayment(clientSecret);
                
                if (paymentResult.success) {
                    await this.createOrder(formDataObj, csrfToken);
                } else {
                    this.displayError(paymentResult.error);
                }
            }
        } catch (error) {
            console.error('Error:', error);
            this.displayError('Ein Fehler ist aufgetreten.');
        }
    }

    async createPaymentIntent(formData, csrfToken) {
        try {
            const response = await fetch('/stripe/create-payment-intent/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-CSRFToken': csrfToken
                },
                body: new URLSearchParams(formData)
            });
                                                
            if (response.ok) {
                const {clientSecret} = await response.json();
                return clientSecret;
            } else {
                const error = await response.json();
                console.error('Payment Intent creation failed:', error);
                return null;
            }
        } catch (error) {
            console.error('Error creating payment intent:', error);
            throw error;
        }
    }

    async confirmPayment(clientSecret) {
        const customerFirstName = this.getCustomerData('first_name');
        const customerLastName = this.getCustomerData('last_name');
        
        const {error} = await this.stripe.confirmCardPayment(clientSecret, {
            payment_method: {
                card: this.cardNumberElement,
                billing_details: {
                    name: `${customerFirstName} ${customerLastName}`,
                }
            }
        });
                                                    
        return {
            success: !error,
            error: error ? error.message : null
        };
    }

    async createOrder(formDataObj, csrfToken) {
        try {
            const response = await fetch('/stripe/create-order/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-CSRFToken': csrfToken
                },
                body: new URLSearchParams(formDataObj)
            });

            if (response.ok) {
                window.location.href = '/thank-you/';
            } else {
                const errorData = await response.json();
                console.error('Order creation failed:', errorData);
                this.displayError('Bestellerstellung fehlgeschlagen: ' + (errorData.error || 'Unbekannter Fehler'));
            }
        } catch (err) {
            console.error('Error creating order:', err);
            this.displayError('Ein Fehler ist aufgetreten.');
        }
    }

    displayError(message) {
        const displayError = document.getElementById('card-errors');
        if (displayError) {
            displayError.textContent = message;
        }
    }

    getCustomerData(field) {
        const customerElement = document.querySelector(`[data-customer-${field}]`);
        if (customerElement) {
            return customerElement.getAttribute(`data-customer-${field}`);
        }                
        return '';
    }
}

document.addEventListener('DOMContentLoaded', function() {
    new StripeCheckoutHandler();
});
