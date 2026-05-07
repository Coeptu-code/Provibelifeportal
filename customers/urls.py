from django.urls import path

from customers import views as customer_views
from invoicing import views as invoicing_views
from orders import views as order_views

app_name = "customers"

urlpatterns = [
    path("", customer_views.dashboard, name="dashboard"),
    path("orders/new/", order_views.order_new, name="order_new"),
    path("orders/", order_views.order_history, name="order_history"),
    path("orders/<int:pk>/", order_views.order_detail, name="order_detail"),
    path("orders/<int:pk>/review/", order_views.order_review, name="order_review"),
    path("invoices/", invoicing_views.customer_invoices, name="invoices"),
    path("invoices/<int:pk>/", invoicing_views.customer_invoice_detail, name="invoice_detail"),
    path("shipping-addresses/", customer_views.shipping_addresses, name="shipping_addresses"),
    path("shipping-addresses/new/", customer_views.shipping_address_new, name="shipping_address_new"),
    path("activity/", customer_views.activity, name="activity"),
    path("account/", customer_views.account, name="account"),
]
