from django.urls import path

from accounts import views as account_views
from customers import views as customer_views
from fulfillment import views as fulfillment_views
from invoicing import views as invoicing_views
from orders import views as order_views
from pricing import views as pricing_views
from products import views as product_views
from reports import views as report_views

app_name = "admin_portal"

urlpatterns = [
    path("", report_views.admin_dashboard, name="dashboard"),
    path("customers/", customer_views.admin_customers, name="customers"),
    path("customers/new/", customer_views.admin_customer_create, name="customer_create"),
    path("customers/<int:pk>/", customer_views.admin_customer_detail, name="customer_detail"),
    path("users/", account_views.admin_internal_users, name="internal_users"),
    path("users/internal/new/", account_views.admin_internal_user_create, name="internal_user_create"),
    path("users/internal/<int:pk>/edit/", account_views.admin_internal_user_edit, name="internal_user_edit"),
    path("users/internal/<int:pk>/activity/", account_views.admin_user_activity, name="user_activity"),
    path("users/new/", account_views.admin_send_invitation, name="customer_user_create"),
    path("users/<int:pk>/edit/", account_views.admin_customer_user_edit, name="customer_user_edit"),
    path("marketing-emails/shilajit/", account_views.admin_marketing_email_shilajit, name="marketing_email_shilajit"),
    path("shipping-addresses/new/", customer_views.admin_shipping_address_create, name="shipping_address_create"),
    path("shipping-addresses/<int:pk>/edit/", customer_views.admin_shipping_address_edit, name="shipping_address_edit"),
    path("products/", product_views.admin_products, name="products"),
    path("products/new/", product_views.admin_product_create, name="product_create"),
    path("products/<int:pk>/edit/", product_views.admin_product_edit, name="product_edit"),
    path("products/<int:pk>/delete/", product_views.admin_product_delete, name="product_delete"),
    path("pricing/", pricing_views.admin_pricing, name="pricing"),
    path("pricing/approvals/new/", pricing_views.admin_customer_product_create, name="customer_product_create"),
    path("pricing/contracts/new/", pricing_views.admin_customer_price_create, name="customer_price_create"),
    path("pricing/contracts/<int:pk>/edit/", pricing_views.admin_customer_price_edit, name="customer_price_edit"),
    path("orders/", order_views.admin_orders, name="orders"),
    path("orders/<int:pk>/", order_views.admin_order_detail, name="order_detail"),
    path("orders/<int:pk>/action/", order_views.admin_order_action, name="order_action"),
    path("orders/<int:pk>/archive/", order_views.admin_order_archive, name="order_archive"),
    path("fulfillment/", fulfillment_views.admin_fulfillment_queue, name="fulfillment_queue"),
    path("pick-ticket/", fulfillment_views.admin_pick_ticket, name="pick_ticket"),
    path("shipments/", fulfillment_views.admin_shipments, name="shipments"),
    path("invoices/", invoicing_views.admin_invoices, name="invoices"),
    path("invoices/<int:pk>/", invoicing_views.admin_invoice_detail, name="invoice_detail"),
    path("payments/", report_views.admin_payments, name="payments"),
    path("reports/", report_views.admin_reports, name="reports"),
]
