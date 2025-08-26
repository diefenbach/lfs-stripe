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
        const style = {
            base: {
              fontSize: '16px',
              color: '#495057',
              lineHeight: '1.5',
              '::placeholder': {
                color: '#6c757d',
              },
              backgroundColor: '#fff',
            },
        };        

        // Only initialize if we have a credit card form
        this.creditCardForm = document.querySelector('.creditcard-form');
        if (!this.creditCardForm) {
            return;
        }
        
        this.stripe = Stripe('pk_live_51RTKp9GCoWo6ClVxD1fIaLqXPIxF3YhmrwJEQM1ewrJqBHeQqOwyC74TdPOZq5oFRZHAEPStp0WrKAU6WNhuvgtH00bCnirnKN');
        this.elements = this.stripe.elements();

        this.cardNumberElement = this.elements.create('cardNumber', {
            style: style,
            disableLink: true
        });
        this.cardExpiryElement = this.elements.create('cardExpiry', {style});
        this.cardCvcElement = this.elements.create('cardCvc', {style});

        this.cardNumberElement.mount('#card-number-element');
        this.cardExpiryElement.mount('#card-expiry-element');
        this.cardCvcElement.mount('#card-cvc-element');

        // Error handling stripe elements
        [this.cardNumberElement, this.cardExpiryElement, this.cardCvcElement].forEach(element => {
            element.on('change', ({error}) => {
                this.displayError(error ? error.message : '');
            });
        });

        // Error handling cardholder name (which is not a stripe element)
        const cardholderNameInput = document.querySelector('input[name="cardholder_name"]');
        if (cardholderNameInput) {
            cardholderNameInput.addEventListener('blur', (event) => {
                if (!event.target.value.trim()) {
                    this.displayError('Bitte geben Sie den Namen des Karteninhabers ein.');
                } else {
                    this.displayError('');
                }
            });
            
            // Clear error when user starts typing
            cardholderNameInput.addEventListener('input', () => {
                this.displayError('');
            });
        }

        // Form submit
        this.creditCardForm.addEventListener('submit', (event) => this.handleFormSubmit(event));
    }

    async handleFormSubmit(event) {
        event.preventDefault();

        const valid_customer = document.querySelector('#id_valid_customer')
        if (!valid_customer.checked) {
            // Display error message for unchecked terms
            const errorElement = document.createElement('div');
            errorElement.className = 'age-error text-danger mb-2';
            errorElement.textContent = 'Bitte bestätigen sie dieses Feld.';
            
            // Insert the error message before the checkbox
            const existingError = valid_customer.parentElement.querySelector('.age-error');
            if (!existingError) {
                valid_customer.parentElement.insertBefore(errorElement, valid_customer);
            }
            return;
        }

        // Get form data to send to the backend
        const formData = new FormData(this.creditCardForm);
    
        // Convert FormData to JSON object
        const formDataObj = Object.fromEntries(formData.entries());
        const csrfToken = getCsrfToken();

        try {
            // Payment Intent vom Backend holen
            const clientSecret = await this.createPaymentIntent(formData, csrfToken);

            // Validate cardholder name before submission
            const cardholderName = document.querySelector('input[name="cardholder_name"]').value.trim();
            if (!cardholderName) {
                this.displayError('Bitte geben Sie den Namen des Karteninhabers ein.');
                return;
            }
            
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
