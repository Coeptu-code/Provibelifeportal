// Pro Vibe Life Portal — data, mapped to Django backend schema
// Field names + enums match models exactly. Money as decimal strings (Django Decimal style).

const { useState, useEffect, useMemo } = React;

// ───────────────────────────────────────────────────────────────
// Customers
const CUSTOMERS = [
  { id: 1, name: 'The Wellness Co.', billing_address: '14 Howard St, Sacramento CA 95814', payment_terms: 'NET_30', credit_limit: '25000.00', is_active: true, stripe_customer_id: 'cus_Q9aB1c2D3eF4', preferred_carrier: 'UPS' },
  { id: 2, name: 'Bay Apothecary', billing_address: '901 Mission St, San Francisco CA 94103', payment_terms: 'NET_30', credit_limit: '60000.00', is_active: true, stripe_customer_id: 'cus_KkLlMm77Nn', preferred_carrier: 'UPS' },
  { id: 3, name: 'NorthStar Health', billing_address: '4400 N Cascade Ave, Colorado Springs CO 80907', payment_terms: 'NET_30', credit_limit: '15000.00', is_active: true, stripe_customer_id: 'cus_ZzYyXx88Ww', preferred_carrier: 'FEDEX' },
  { id: 4, name: 'Iron Roots Clinic', billing_address: '210 Pine St, Reno NV 89501', payment_terms: 'PREPAID', credit_limit: '0.00', is_active: true, stripe_customer_id: '', preferred_carrier: '' },
  { id: 5, name: 'Vista Naturals', billing_address: '88 Coastal Hwy, Encinitas CA 92024', payment_terms: 'NET_15', credit_limit: '10000.00', is_active: true, stripe_customer_id: 'cus_Vv5T6r7Q8p', preferred_carrier: 'USPS' },
];

// Currently signed-in customer (for customer-side views)
const ME_CUSTOMER = CUSTOMERS[0];
const ME_USER = {
  id: 11, username: 'sarah.hayes', email: 'sarah@thewellness.co', first_name: 'Sarah', last_name: 'Hayes',
  role: 'customer_user', is_customer_user: true, is_warehouse_staff: false, is_ops_user: false,
  customer: ME_CUSTOMER.id,
};
const ME_ADMIN = {
  id: 2, username: 'mason.cole', email: 'ops@provibelife.com', first_name: 'Mason', last_name: 'Cole',
  role: 'admin', is_customer_user: false, is_warehouse_staff: false, is_ops_user: true, customer: null,
};

// ShippingAddress (customer=ME_CUSTOMER)
const SHIPPING_ADDRESSES = [
  { id: 101, customer: 1, label: 'Main Warehouse', line1: '2410 Industry Way', line2: 'Bay 14', city: 'Sacramento', state: 'CA', postal_code: '95815', country: 'US', is_default: true,  is_active: true },
  { id: 102, customer: 1, label: 'Retail — Folsom', line1: '105 E Bidwell St',  line2: '',       city: 'Folsom',     state: 'CA', postal_code: '95630', country: 'US', is_default: false, is_active: true },
  { id: 103, customer: 1, label: 'Retail — Tahoe',  line1: '935 Emerald Bay Rd', line2: '',       city: 'South Lake Tahoe', state: 'CA', postal_code: '96150', country: 'US', is_default: false, is_active: true },
];

// Products (matches products.Product)
const PRODUCTS = [
  {
    id: 1, sku: 'PVB-100001', name: 'Shilajit Resin Tablets',
    description: 'Pure Mountain Resin · 60 tablets · 200mg · fulvic-acid tested at 78%',
    image: null, image_url: 'assets/shilajit.png',
    case_quantity: 12,
    shipping_weight: '0.42', shipping_weight_unit: 'lb',
    shipping_length: '4.0', shipping_width: '4.0', shipping_height: '5.0', shipping_dimension_unit: 'in',
    shipping_package_type: 'BOX',
    active: true,
  },
  {
    id: 2, sku: 'PVB-100002', name: 'Vitali-T',
    description: 'Natural Testosterone Support · 90 capsules · 3rd-party verified',
    image: null, image_url: 'assets/vitali-t.png',
    case_quantity: 6,
    shipping_weight: '0.55', shipping_weight_unit: 'lb',
    shipping_length: '4.5', shipping_width: '4.5', shipping_height: '5.5', shipping_dimension_unit: 'in',
    shipping_package_type: 'BOX',
    active: true,
  },
  {
    id: 3, sku: 'PVB-100003', name: 'Performance Bundle',
    description: 'Shilajit + Vitali-T (1 each) · co-packed · ships in single carton',
    image: null, image_url: null,
    case_quantity: 6,
    shipping_weight: '1.05', shipping_weight_unit: 'lb',
    shipping_length: '8.0', shipping_width: '5.0', shipping_height: '6.0', shipping_dimension_unit: 'in',
    shipping_package_type: 'BOX',
    active: true,
  },
  {
    id: 4, sku: 'PVB-100004', name: 'Shilajit Powder',
    description: 'Bulk powder · 50g pouch · resealable',
    image: null, image_url: null,
    case_quantity: 12,
    shipping_weight: '0.18', shipping_weight_unit: 'lb',
    shipping_length: '5.0', shipping_width: '3.5', shipping_height: '1.0', shipping_dimension_unit: 'in',
    shipping_package_type: 'POUCH',
    active: false, // surfaces as "Restocking" in UI
  },
];

// CustomerProduct approvals (only approved products show in catalog for the customer)
const CUSTOMER_PRODUCTS = [
  { id: 501, customer: 1, product: 1, active: true },
  { id: 502, customer: 1, product: 2, active: true },
  { id: 503, customer: 1, product: 3, active: true },
  { id: 504, customer: 1, product: 4, active: true },
];

// CustomerPrice — contract pricing
const CUSTOMER_PRICES = [
  { id: 901, customer: 1, product: 1, unit_price: '14.40', minimum_quantity: 12, effective_date: '2025-11-01', expiration_date: '2026-10-31' },
  { id: 902, customer: 1, product: 2, unit_price: '28.32', minimum_quantity: 6,  effective_date: '2025-11-01', expiration_date: '2026-10-31' },
  { id: 903, customer: 1, product: 3, unit_price: '41.50', minimum_quantity: 6,  effective_date: '2025-11-01', expiration_date: '2026-10-31' },
  { id: 904, customer: 1, product: 4, unit_price: '22.10', minimum_quantity: 12, effective_date: '2025-11-01', expiration_date: '2026-10-31' },
  { id: 910, customer: 2, product: 1, unit_price: '13.80', minimum_quantity: 24, effective_date: '2025-09-15', expiration_date: '2026-09-14' },
  { id: 911, customer: 2, product: 2, unit_price: '26.50', minimum_quantity: 12, effective_date: '2025-09-15', expiration_date: '2026-09-14' },
  { id: 920, customer: 3, product: 1, unit_price: '15.00', minimum_quantity: 12, effective_date: '2026-01-01', expiration_date: null },
];

// Orders (orders.Order)
const ORDERS = [
  {
    id: 1042, po_number: 'PO-44210', customer: 1, customer_name: 'The Wellness Co.',
    shipping_address: 101, status: 'SUBMITTED',
    requested_ship_date: '2026-05-08', subtotal: '1620.06', total: '1842.40',
    submitted_at: '2026-04-28T14:14:00Z', created_at: '2026-04-28T14:10:00Z', updated_at: '2026-04-28T14:14:00Z',
    item_count: 4,
  },
  {
    id: 1041, po_number: 'PO-7711', customer: 2, customer_name: 'Bay Apothecary',
    shipping_address: null, status: 'APPROVED',
    requested_ship_date: '2026-05-04', subtotal: '870.00', total: '936.00',
    submitted_at: '2026-04-27T10:02:00Z', created_at: '2026-04-27T09:50:00Z', updated_at: '2026-04-27T11:30:00Z',
    item_count: 2,
  },
  {
    id: 1039, po_number: 'PO-2090', customer: 3, customer_name: 'NorthStar Health',
    shipping_address: null, status: 'PACKED',
    requested_ship_date: '2026-05-02', subtotal: '2110.00', total: '2250.00',
    submitted_at: '2026-04-26T08:11:00Z', created_at: '2026-04-26T08:00:00Z', updated_at: '2026-04-27T16:40:00Z',
    item_count: 6,
  },
  {
    id: 1037, po_number: 'PO-501', customer: 4, customer_name: 'Iron Roots Clinic',
    shipping_address: null, status: 'SHIPPED',
    requested_ship_date: '2026-04-29', subtotal: '480.00', total: '522.40',
    submitted_at: '2026-04-25T13:00:00Z', created_at: '2026-04-25T12:55:00Z', updated_at: '2026-04-26T09:00:00Z',
    item_count: 1,
  },
  {
    id: 1034, po_number: 'PO-7704', customer: 2, customer_name: 'Bay Apothecary',
    shipping_address: null, status: 'SHIPPED',
    requested_ship_date: '2026-04-25', subtotal: '1200.00', total: '1296.00',
    submitted_at: '2026-04-22T15:30:00Z', created_at: '2026-04-22T15:20:00Z', updated_at: '2026-04-23T10:00:00Z',
    item_count: 3,
  },
  {
    id: 1031, po_number: 'PO-110', customer: 5, customer_name: 'Vista Naturals',
    shipping_address: null, status: 'ON_HOLD',
    requested_ship_date: '2026-04-30', subtotal: '380.00', total: '410.00',
    submitted_at: '2026-04-20T09:00:00Z', created_at: '2026-04-20T08:55:00Z', updated_at: '2026-04-21T11:00:00Z',
    item_count: 1,
  },
];

// OrderItems for the focus order (PVL-1042)
const ORDER_ITEMS_1042 = [
  { id: 9001, order: 1042, product: 1, sku: 'PVB-100001', name: 'Shilajit Resin Tablets', quantity: 72, locked_unit_price: '14.40', unit_price: '14.40', extended_price: '1036.80' },
  { id: 9002, order: 1042, product: 2, sku: 'PVB-100002', name: 'Vitali-T',                quantity: 24, locked_unit_price: '28.32', unit_price: '28.32', extended_price: '679.68'  },
  { id: 9003, order: 1042, product: 3, sku: 'PVB-100003', name: 'Performance Bundle',     quantity: 3,  locked_unit_price: '41.50', unit_price: '41.50', extended_price: '124.50'  },
];

// Invoices (invoicing.Invoice)
const INVOICES = [
  {
    id: 2027, invoice_number: 'INV-2027', invoice_kind: 'PRIMARY', parent_invoice: null,
    order: 1041, customer: 2, customer_name: 'Bay Apothecary',
    subtotal: '870.00', shipping_total: '38.40', tax_total: '27.60', total: '936.00',
    status: 'OPEN', due_date: '2026-05-27',
    shipping_carrier: 'UPS', shipping_service: 'Ground', shipping_rate_id: 'rate_01H7XZ', shipping_currency: 'USD',
    shipping_quoted_at: '2026-04-27T10:01:00Z', shipping_quote_status: 'SUCCESS', shipping_input_source: 'ESTIMATED_API', shipping_quote_reason: '',
    pdf_file: null, stripe_invoice_id: 'in_1OqAaa', stripe_hosted_invoice_url: 'https://invoice.stripe.com/i/test_OqAaa', stripe_invoice_pdf: 'https://stripe.com/pdf/OqAaa.pdf',
    created_at: '2026-04-27T10:00:00Z', paid_at: null,
  },
  {
    id: 2025, invoice_number: 'INV-2025', invoice_kind: 'PRIMARY', parent_invoice: null,
    order: 1039, customer: 3, customer_name: 'NorthStar Health',
    subtotal: '2110.00', shipping_total: '92.00', tax_total: '48.00', total: '2250.00',
    status: 'SENT', due_date: '2026-05-26',
    shipping_carrier: 'FEDEX', shipping_service: 'Ground', shipping_rate_id: 'rate_01H8AB', shipping_currency: 'USD',
    shipping_quoted_at: '2026-04-26T08:14:00Z', shipping_quote_status: 'SUCCESS', shipping_input_source: 'ESTIMATED_API', shipping_quote_reason: '',
    pdf_file: null, stripe_invoice_id: 'in_1OqBbb', stripe_hosted_invoice_url: 'https://invoice.stripe.com/i/test_OqBbb', stripe_invoice_pdf: null,
    created_at: '2026-04-26T08:13:00Z', paid_at: null,
  },
  {
    id: 2022, invoice_number: 'INV-2022', invoice_kind: 'PRIMARY', parent_invoice: null,
    order: 1037, customer: 4, customer_name: 'Iron Roots Clinic',
    subtotal: '480.00', shipping_total: '22.40', tax_total: '20.00', total: '522.40',
    status: 'PAID', due_date: '2026-05-25',
    shipping_carrier: 'UPS', shipping_service: 'Ground', shipping_rate_id: 'rate_01H8CD', shipping_currency: 'USD',
    shipping_quoted_at: '2026-04-25T13:01:00Z', shipping_quote_status: 'SUCCESS', shipping_input_source: 'ESTIMATED_API', shipping_quote_reason: '',
    pdf_file: null, stripe_invoice_id: 'in_1OqCcc', stripe_hosted_invoice_url: 'https://invoice.stripe.com/i/test_OqCcc', stripe_invoice_pdf: null,
    created_at: '2026-04-25T13:00:00Z', paid_at: '2026-04-30T09:14:00Z',
  },
  {
    id: 2018, invoice_number: 'INV-2018', invoice_kind: 'PRIMARY', parent_invoice: null,
    order: 1034, customer: 2, customer_name: 'Bay Apothecary',
    subtotal: '1200.00', shipping_total: '46.00', tax_total: '50.00', total: '1296.00',
    status: 'PAID', due_date: '2026-05-22',
    shipping_carrier: 'UPS', shipping_service: 'Ground', shipping_rate_id: 'rate_01H8EF', shipping_currency: 'USD',
    shipping_quoted_at: '2026-04-22T15:32:00Z', shipping_quote_status: 'SUCCESS', shipping_input_source: 'ESTIMATED_API', shipping_quote_reason: '',
    pdf_file: null, stripe_invoice_id: 'in_1OqDdd', stripe_hosted_invoice_url: 'https://invoice.stripe.com/i/test_OqDdd', stripe_invoice_pdf: null,
    created_at: '2026-04-22T15:31:00Z', paid_at: '2026-04-29T11:02:00Z',
  },
  {
    id: 2010, invoice_number: 'INV-2010', invoice_kind: 'PRIMARY', parent_invoice: null,
    order: 1029, customer: 5, customer_name: 'Vista Naturals',
    subtotal: '580.00', shipping_total: '20.00', tax_total: '12.50', total: '612.50',
    status: 'OVERDUE', due_date: '2026-04-18',
    shipping_carrier: 'USPS', shipping_service: 'Priority', shipping_rate_id: 'rate_01H7GG', shipping_currency: 'USD',
    shipping_quoted_at: '2026-03-18T11:00:00Z', shipping_quote_status: 'SUCCESS', shipping_input_source: 'ESTIMATED_API', shipping_quote_reason: '',
    pdf_file: null, stripe_invoice_id: 'in_1OqEee', stripe_hosted_invoice_url: 'https://invoice.stripe.com/i/test_OqEee', stripe_invoice_pdf: null,
    created_at: '2026-03-18T10:55:00Z', paid_at: null,
  },
];

// Shipments (fulfillment.Shipment)
const SHIPMENTS = [
  { id: 8821, order: 1037, carrier: 'UPS',   tracking_number: '1Z999AA10123456784', shipped_at: '2026-04-25T17:00:00Z', status: 'SHIPPED', created_at: '2026-04-25T16:30:00Z' },
  { id: 8819, order: 1039, carrier: 'FEDEX', tracking_number: '781234567890',       shipped_at: null,                    status: 'PACKED',  created_at: '2026-04-27T16:40:00Z' },
  { id: 8815, order: 1034, carrier: 'UPS',   tracking_number: '1Z999AA10123456790', shipped_at: '2026-04-23T15:00:00Z', status: 'SHIPPED', created_at: '2026-04-23T14:30:00Z' },
];

// Payments (payments.Payment)
const PAYMENTS = [
  { id: 7301, invoice: 2022, amount: '522.40',  method: 'STRIPE', reference_number: 'pi_3PqrstUVW', received_at: '2026-04-30T09:14:00Z', stripe_payment_intent_id: 'pi_3PqrstUVW', created_at: '2026-04-30T09:14:00Z' },
  { id: 7280, invoice: 2018, amount: '1296.00', method: 'ACH',    reference_number: 'ACH-77321',   received_at: '2026-04-29T11:02:00Z', stripe_payment_intent_id: '',          created_at: '2026-04-29T11:02:00Z' },
];

// Activity feed (admin dashboard) — derived/audit-style entries
const ACTIVITY = [
  { when: 'Today, 2:14p',  what: <span><b>Order #1042</b> submitted by sarah.hayes at <b>The Wellness Co.</b></span> },
  { when: 'Today, 11:02a', what: <span><b>INV-2025</b> emailed to NorthStar Health · Stripe hosted link active</span> },
  { when: 'Apr 28',        what: <span><b>Order #1041</b> approved · UPS Ground rate <span className="mono">rate_01H7XZ</span> locked</span> },
  { when: 'Apr 27',        what: <span>Bay Apothecary <b>CustomerPrice</b> for Shilajit renewed through Oct 2026</span> },
  { when: 'Apr 26',        what: <span><b>Order #1039</b> packed · 6 cartons released to UPS</span> },
];

// ───────────────────────────────────────────────────────────────
// Status -> pill tone mapping (uses backend enum values verbatim)
const STATUS_PILLS = {
  // Order
  DRAFT: 'muted', SUBMITTED: 'blue', UNDER_REVIEW: 'blue',
  APPROVED: 'gold', RELEASED_TO_WAREHOUSE: 'amber',
  PICKING: 'amber', PACKED: 'amber', PARTIALLY_SHIPPED: 'amber',
  SHIPPED: 'green',
  ON_HOLD: 'amber', CANCELLED: 'red',
  // Invoice
  SENT: 'blue', OPEN: 'blue',
  PAID: 'green', PARTIALLY_PAID: 'amber',
  OVERDUE: 'red', VOID: 'red',
  // Shipment / Payment
  PENDING: 'muted',
};

// Human-friendly label for an enum value
const labelize = (v) => (v || '').replace(/_/g, ' ').toLowerCase().replace(/\b\w/g, c => c.toUpperCase());
window.labelize = labelize;

// Money formatter (input is decimal string like "1842.40")
const money = (v, currency = 'USD') => {
  const n = typeof v === 'string' ? parseFloat(v) : (v || 0);
  return n.toLocaleString('en-US', { style: 'currency', currency });
};
window.money = money;

// Format a date string (YYYY-MM-DD or ISO) to "Apr 28"
const fmtDate = (iso) => {
  if (!iso) return '—';
  const d = new Date(iso.length === 10 ? iso + 'T00:00:00' : iso);
  if (isNaN(d)) return iso;
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
};
window.fmtDate = fmtDate;

// Payment-terms label
const PAYMENT_TERMS_LABEL = { NET_15: 'Net-15', NET_30: 'Net-30', PREPAID: 'Prepaid' };
window.PAYMENT_TERMS_LABEL = PAYMENT_TERMS_LABEL;

// ───────────────────────────────────────────────────────────────
// Brand mark
function BrandMark({ size = 32 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 40 40" aria-hidden="true">
      <circle cx="20" cy="20" r="18.5" fill="none" stroke="#c9a04a" strokeWidth="1.4"/>
      <path d="M11 27 C 14 20, 19 15, 28 13 C 27 22, 22 27, 13 28 Z" fill="none" stroke="#c9a04a" strokeWidth="1.5" strokeLinejoin="round"/>
      <path d="M11 27 C 16 23, 22 19, 28 13" fill="none" stroke="#c9a04a" strokeWidth="1.2" strokeLinecap="round"/>
    </svg>
  );
}
window.BrandMark = BrandMark;

// ───────────────────────────────────────────────────────────────
// Sidebar
const NAV_CUSTOMER = [
  { id: 'dashboard', label: 'Dashboard', icon: 'dashboard' },
  { id: 'order_new', label: 'New Order', icon: 'plus' },
  { id: 'orders', label: 'Order History', icon: 'history' },
  { id: 'invoices', label: 'Invoices', icon: 'invoice', badge: 2 },
  { id: 'addresses', label: 'Shipping Addresses', icon: 'pin' },
  { id: 'account', label: 'Account', icon: 'user' },
];
const NAV_ADMIN = [
  { id: 'admin_dashboard', label: 'Operations', icon: 'dashboard' },
  { id: 'admin_orders', label: 'Orders', icon: 'cart', badge: 3 },
  { id: 'admin_fulfillment', label: 'Fulfillment', icon: 'box' },
  { id: 'admin_shipments', label: 'Shipments', icon: 'truck' },
  { id: 'admin_invoices', label: 'Invoices', icon: 'invoice' },
  { id: 'admin_customers', label: 'Customers', icon: 'users' },
  { id: 'admin_products', label: 'Products', icon: 'pkg' },
  { id: 'admin_pricing', label: 'Pricing', icon: 'tag' },
  { id: 'admin_reports', label: 'Reports', icon: 'chart' },
];

function Sidebar({ role, setRole, route, go }) {
  const items = role === 'admin' ? NAV_ADMIN : NAV_CUSTOMER;
  const me = role === 'admin' ? ME_ADMIN : ME_USER;
  return (
    <aside className="sidebar">
      <div className="brand">
        <BrandMark size={36}/>
        <div className="brand-text">
          <div className="pn">provibe<span style={{color:'#c9a04a'}}>life</span></div>
          <div className="ps">Wholesale Portal</div>
        </div>
      </div>
      <div className="role-switch">
        <button className={role === 'customer' ? 'active' : ''} onClick={() => { setRole('customer'); go('dashboard'); }}>Customer</button>
        <button className={role === 'admin' ? 'active' : ''} onClick={() => { setRole('admin'); go('admin_dashboard'); }}>Admin</button>
      </div>
      <nav>
        <div className="nav-section">{role === 'admin' ? 'Operations' : 'My Account'}</div>
        {items.map(it => {
          const I = Ico[it.icon];
          return (
            <a key={it.id} className={'nav-item' + (route === it.id ? ' active' : '')} onClick={() => go(it.id)}>
              <I className="ico"/>
              <span>{it.label}</span>
              {it.badge && <span className="badge">{it.badge}</span>}
            </a>
          );
        })}
        <div className="nav-section">Resources</div>
        <a className="nav-item"><Ico.shield className="ico"/><span>COA / Lab Reports</span></a>
        <a className="nav-item"><Ico.download className="ico"/><span>Marketing Assets</span></a>
        <a className="nav-item"><Ico.cog className="ico"/><span>Settings</span></a>
      </nav>
      <div className="footer">
        <div className="avatar">{(me.first_name?.[0] || '') + (me.last_name?.[0] || '')}</div>
        <div className="who">
          <div className="n">{me.first_name} {me.last_name}</div>
          <div className="e">{me.email}</div>
        </div>
        <button className="icon-btn" title="Sign out"><Ico.external width="14" height="14"/></button>
      </div>
    </aside>
  );
}

// Topbar
function Topbar({ route, role, openMenu, onMenu }) {
  const titles = {
    dashboard: 'Dashboard', order_new: 'New Order', order_review: 'Verify Order', order_history: 'Order History',
    orders: 'Order History', order_detail: 'Order Detail',
    invoices: 'Invoices', invoice_detail: 'Invoice', addresses: 'Shipping Addresses', account: 'Account',
    admin_dashboard: 'Operations', admin_orders: 'Orders', admin_order_detail: 'Order Detail',
    admin_fulfillment: 'Fulfillment', admin_shipments: 'Shipments', admin_invoices: 'Invoices',
    admin_customers: 'Customers', admin_products: 'Products', admin_pricing: 'Pricing', admin_reports: 'Reports',
  };
  return (
    <header className="topbar">
      <button className="icon-btn menu-btn" onClick={onMenu} aria-label="Menu" style={{display:'none'}}><Ico.menu width="18" height="18"/></button>
      <div className="crumb">
        <span>{role === 'admin' ? 'Operations' : 'Wholesale'}</span>
        <span>›</span>
        <b>{titles[route] || ''}</b>
      </div>
      <div className="search">
        <Ico.search width="14" height="14"/>
        <input placeholder={role === 'admin' ? 'Search orders, customers, SKUs…' : 'Search your orders, invoices…'}/>
        <kbd>⌘K</kbd>
      </div>
      <div className="actions">
        <button className="icon-btn" title="Notifications"><Ico.bell width="16" height="16"/></button>
      </div>
    </header>
  );
}

// Mobile tab bar
function TabBar({ role, route, go }) {
  const tabs = role === 'admin'
    ? [
        { id: 'admin_dashboard', label: 'Ops', icon: 'dashboard' },
        { id: 'admin_orders', label: 'Orders', icon: 'cart' },
        { id: 'admin_fulfillment', label: 'Fulfill', icon: 'box' },
        { id: 'admin_invoices', label: 'Invoices', icon: 'invoice' },
        { id: 'admin_customers', label: 'Customers', icon: 'users' },
      ]
    : [
        { id: 'dashboard', label: 'Home', icon: 'dashboard' },
        { id: 'order_new', label: 'Order', icon: 'plus' },
        { id: 'orders', label: 'History', icon: 'history' },
        { id: 'invoices', label: 'Invoices', icon: 'invoice' },
        { id: 'account', label: 'Account', icon: 'user' },
      ];
  return (
    <nav className="tabbar">
      {tabs.map(t => {
        const I = Ico[t.icon];
        return (
          <button key={t.id} className={'t' + (route === t.id ? ' active' : '')} onClick={() => go(t.id)}>
            <I className="ico"/>
            <span>{t.label}</span>
          </button>
        );
      })}
    </nav>
  );
}

window.Sidebar = Sidebar;
window.Topbar = Topbar;
window.TabBar = TabBar;
// ───────────────────────────────────────────────────────────────
// UI compatibility shims: existing components reference legacy field names
// (p.img, p.wholesale, p.msrp, p.minQty, p.tagline, p.available, p.reason, p.lead;
//  o.id, o.po, o.submitted, o.items, o.total, o.customer;
//  inv.id, inv.order, inv.issued, inv.due, inv.total;
//  a.zip, a.isDefault, a.id).
// We map Django fields onto these names so the UI keeps working without changes.
const SUGGESTED_MSRP = { 1: 30, 2: 74, 3: 99, 4: 49 };
const SUGGESTED_LEAD = { BOX: '2–3 days', POUCH: '3–5 days' };
const PRODUCTS_UI = PRODUCTS.map(p => {
  const price = CUSTOMER_PRICES.find(cp => cp.customer === ME_CUSTOMER.id && cp.product === p.id);
  return {
    ...p,
    img: p.image_url,
    tagline: p.description,
    wholesale: price ? parseFloat(price.unit_price) : 0,
    msrp: SUGGESTED_MSRP[p.id] || null,
    minQty: price ? price.minimum_quantity : p.case_quantity,
    available: p.active,
    reason: p.active ? null : `Restocking — ${p.name} back online soon`,
    lead: SUGGESTED_LEAD[p.shipping_package_type] || '2–3 days',
  };
});
const ORDERS_UI = ORDERS.map(o => ({
  ...o,
  id: `PVL-${o.id}`,
  po: o.po_number,
  customer: o.customer_name,
  submitted: fmtDate(o.submitted_at),
  items: o.item_count,
  total: parseFloat(o.total),
}));
const INVOICES_UI = INVOICES.map(inv => ({
  ...inv,
  id: inv.invoice_number,
  order: `PVL-${inv.order}`,
  issued: fmtDate(inv.created_at),
  due: fmtDate(inv.due_date),
  total: parseFloat(inv.total),
}));
const ADDRESSES_UI = SHIPPING_ADDRESSES.map(a => ({
  ...a,
  zip: a.postal_code,
  isDefault: a.is_default,
}));

window.PRODUCTS = PRODUCTS_UI;
window.PRODUCTS_RAW = PRODUCTS;
window.CUSTOMERS = CUSTOMERS;
window.CUSTOMER_PRODUCTS = CUSTOMER_PRODUCTS;
window.CUSTOMER_PRICES = CUSTOMER_PRICES;
window.ORDERS = ORDERS_UI;
window.ORDERS_RAW = ORDERS;
window.ORDER_ITEMS_1042 = ORDER_ITEMS_1042;
window.INVOICES = INVOICES_UI;
window.INVOICES_RAW = INVOICES;
window.SHIPMENTS = SHIPMENTS;
window.PAYMENTS = PAYMENTS;
window.SHIPPING_ADDRESSES = SHIPPING_ADDRESSES;
window.ADDRESSES = ADDRESSES_UI;
window.ACTIVITY = ACTIVITY;
window.STATUS_PILLS = STATUS_PILLS;
window.ME_USER = ME_USER;
window.ME_ADMIN = ME_ADMIN;
window.ME_CUSTOMER = ME_CUSTOMER;
