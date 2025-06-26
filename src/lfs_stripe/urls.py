from django.urls import path
from . import views

app_name = "lfs-stripe"

urlpatterns = [
    path("create-payment-intent/", views.create_payment_intent, name="create_payment_intent"),
    path("create-order/", views.create_order, name="create_order"),
]
