// Admin pages — concise versions
const { useState: useStateA } = React;

function AdminDashboard({ go }) {
  return (
    <div className="page">
      <div className="page-head">
        <div>
          <div className="eyebrow">Wholesale operations</div>
          <h1>Operations</h1>
          <p className="lede">3 new orders need review · 2 invoices overdue · 6 cartons to ship today.</p>
        </div>
        <div className="right">
          <button className="btn">Export day report</button>
          <button className="btn gold"><Ico.plus width="13" height="13"/> Manual order</button>
        </div>
      </div>
      <div className="stats">
        <div className="stat feature">
          <div className="lbl">MTD revenue</div>
          <div className="v tabular">$74,326</div>
          <div className="delta" style={{color:'rgba(247,241,222,0.6)'}}>+18% vs last month</div>
          <div className="gold-line"/>
        </div>
        <div className="stat"><div className="lbl">Open orders</div><div className="v tabular">12</div><div className="delta">3 new · 5 packed · 4 shipping</div></div>
        <div className="stat"><div className="lbl">In fulfillment</div><div className="v tabular">5</div><div className="delta">Avg cycle 3.4d</div></div>
        <div className="stat"><div className="lbl">Open invoices</div><div className="v tabular">8</div><div className="delta down">2 overdue · $1,247</div></div>
      </div>
      <div className="grid-2">
        <div className="card flush">
          <div className="card-head"><h3>New orders awaiting review</h3><a className="muted" style={{fontSize:12.5, fontWeight:600}} onClick={()=>go('admin_orders')}>Open queue →</a></div>
          <div className="tbl-wrap">
            <table className="tbl">
              <thead><tr><th>Order</th><th>Customer</th><th>PO</th><th>Status</th><th className="num">Total</th></tr></thead>
              <tbody>
                {window.ORDERS.slice(0,4).map(o => (
                  <tr key={o.id} onClick={()=>go('admin_order_detail', o.id)}>
                    <td className="strong mono">{o.id}</td>
                    <td className="strong">{o.customer}</td>
                    <td className="mono muted">{o.po}</td>
                    <td><StatusPill status={o.status}/></td>
                    <td className="num strong">${o.total.toLocaleString(undefined,{minimumFractionDigits:2})}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
        <div className="vstack" style={{gap:16}}>
          <div className="card">
            <h3 style={{margin:'0 0 14px', fontSize:15}}>Today</h3>
            <ul className="activity">
              {window.ACTIVITY.map((a,i) => (
                <li key={i}><div className="when">{a.when}</div><div className="what">{a.what}</div></li>
              ))}
            </ul>
          </div>
          <div className="promo">
            <div className="marble"/>
            <div style={{position:'relative', flex:1}}>
              <div className="eyebrow" style={{color:'#c9a04a'}}>Inventory alert</div>
              <h3>Vitali-T at 24% par.</h3>
              <p>Reorder PO due to manufacturer by Apr 30 to avoid stockout.</p>
            </div>
            <button className="btn gold">Reorder</button>
          </div>
        </div>
      </div>
    </div>
  );
}
window.AdminDashboard = AdminDashboard;

function GenericTablePage({ title, eyebrow, lede, columns, rows, go, route, primaryAction, statusKey = 'status' }) {
  return (
    <div className="page">
      <div className="page-head">
        <div>
          <div className="eyebrow">{eyebrow}</div>
          <h1>{title}</h1>
          <p className="lede">{lede}</p>
        </div>
        <div className="right">
          {primaryAction}
        </div>
      </div>
      <div className="card flush">
        <div className="tbl-wrap">
          <table className="tbl">
            <thead><tr>{columns.map(c => <th key={c.k} className={c.num ? 'num' : ''}>{c.l}</th>)}</tr></thead>
            <tbody>
              {rows.map((r,i) => (
                <tr key={i} onClick={() => route && go(route, r.id)}>
                  {columns.map(c => (
                    <td key={c.k} className={(c.num ? 'num ' : '') + (c.strong ? 'strong ' : '') + (c.mono ? 'mono ' : '') + (c.muted ? 'muted ' : '')}>
                      {c.k === statusKey ? <StatusPill status={r[c.k]}/> : c.fmt ? c.fmt(r[c.k], r) : r[c.k]}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function AdminOrders({ go }) {
  return GenericTablePage({
    title: 'Orders', eyebrow: '24 orders this month', lede: 'Sorted by submission date. Click any row to open the detail and run workflow actions.',
    primaryAction: <><button className="btn">Filter <Ico.filter width="13" height="13"/></button><button className="btn primary">Export CSV</button></>,
    columns: [
      {k:'id', l:'Order', strong:true, mono:true},
      {k:'customer', l:'Customer', strong:true},
      {k:'po', l:'PO', mono:true, muted:true},
      {k:'submitted', l:'Submitted', muted:true},
      {k:'status', l:'Status'},
      {k:'total', l:'Total', num:true, strong:true, fmt: v => `$${v.toLocaleString(undefined,{minimumFractionDigits:2})}`},
    ],
    rows: window.ORDERS, go, route: 'admin_order_detail',
  });
}
window.AdminOrders = AdminOrders;

function AdminInvoices() {
  return GenericTablePage({
    title: 'Invoices', eyebrow: 'Billing', lede: '8 open · $9,012 outstanding · 2 overdue.',
    primaryAction: <><button className="btn">Generate batch</button><button className="btn gold"><Ico.plus width="13" height="13"/> New invoice</button></>,
    columns: [
      {k:'id', l:'Invoice', strong:true, mono:true},
      {k:'order', l:'Order', mono:true, muted:true},
      {k:'customer', l:'Customer'},
      {k:'issued', l:'Issued', muted:true},
      {k:'due', l:'Due', muted:true},
      {k:'status', l:'Status'},
      {k:'total', l:'Total', num:true, strong:true, fmt: v => `$${v.toLocaleString(undefined,{minimumFractionDigits:2})}`},
    ],
    rows: window.INVOICES, go: () => {},
  });
}
window.AdminInvoices = AdminInvoices;

function AdminCustomers() {
  const customers = [
    { id:'c1', name:'The Wellness Co.', tier:'Tier B', terms:'Net-30', orders:14, ltd:48209, status:'PAID' },
    { id:'c2', name:'Bay Apothecary', tier:'Tier A', terms:'Net-30', orders:31, ltd:128440, status:'OPEN' },
    { id:'c3', name:'NorthStar Health', tier:'Tier B', terms:'Net-30', orders:9, ltd:22150, status:'SENT' },
    { id:'c4', name:'Iron Roots Clinic', tier:'Tier C', terms:'Prepaid', orders:4, ltd:5024, status:'PAID' },
    { id:'c5', name:'Vista Naturals', tier:'Tier B', terms:'Net-30', orders:6, ltd:9620, status:'OVERDUE' },
  ];
  return GenericTablePage({
    title: 'Customers', eyebrow: '5 active accounts', lede: 'Manage tiers, payment terms, approved SKUs, and contract pricing.',
    primaryAction: <button className="btn gold"><Ico.plus width="13" height="13"/> Add customer</button>,
    columns: [
      {k:'name', l:'Customer', strong:true},
      {k:'tier', l:'Tier'},
      {k:'terms', l:'Terms', muted:true},
      {k:'orders', l:'Orders', num:true},
      {k:'ltd', l:'LTD spend', num:true, strong:true, fmt: v => `$${v.toLocaleString()}`},
      {k:'status', l:'A/R'},
    ],
    rows: customers,
  });
}
window.AdminCustomers = AdminCustomers;

function AdminProducts() {
  return (
    <div className="page">
      <div className="page-head">
        <div><div className="eyebrow">Catalog</div><h1>Products</h1><p className="lede">4 SKUs in active catalog. Edit pricing, batches, and lab reports here.</p></div>
        <div className="right"><button className="btn gold"><Ico.plus width="13" height="13"/> Add product</button></div>
      </div>
      <div className="grid-cards">
        {window.PRODUCTS.map(p => (
          <div key={p.id} className="product">
            <div className="img"><div className="gold-glow"/>{p.img ? <img src={p.img}/> : <BrandMark size={56}/>}</div>
            <div className="meta">
              <div className="sku">{p.sku}</div>
              <h4>{p.name}</h4>
              <div className="muted" style={{fontSize:12.5}}>{p.tagline}</div>
            </div>
            <div className="hstack" style={{justifyContent:'space-between'}}>
              <div>
                <div style={{fontFamily:'var(--pvl-display-font)', fontSize:22, fontWeight:600}}>${p.wholesale.toFixed(2)}</div>
                <div className="muted" style={{fontSize:11.5}}>Wholesale base</div>
              </div>
              {p.available ? <span className="pill green"><span className="dot"/>Active</span> : <span className="pill amber"><span className="dot"/>Restocking</span>}
            </div>
            <div className="hstack" style={{gap:8}}>
              <button className="btn sm block">Edit</button>
              <button className="btn sm block">Lab COA</button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
window.AdminProducts = AdminProducts;

function AdminFulfillment({ go }) {
  return GenericTablePage({
    title: 'Fulfillment queue', eyebrow: 'Warehouse · Sacramento', lede: '5 orders released to warehouse. Pick → pack → ship.',
    primaryAction: <button className="btn primary">Print today's pick tickets</button>,
    columns: [
      {k:'id', l:'Order', strong:true, mono:true},
      {k:'customer', l:'Customer'},
      {k:'items', l:'SKUs / Units', fmt: (v,r) => `${v} SKUs / ${r.items*16} u`},
      {k:'submitted', l:'Submitted', muted:true},
      {k:'status', l:'Status'},
    ],
    rows: window.ORDERS.filter(o => ['APPROVED','PACKED','PARTIALLY_SHIPPED'].includes(o.status)),
    go, route: 'admin_order_detail',
  });
}
window.AdminFulfillment = AdminFulfillment;

function AdminShipments() {
  const shipments = [
    { id:'SH-8821', order:'PVL-1037', customer:'Iron Roots Clinic', carrier:'UPS Ground', tracking:'1Z999AA10123456784', status:'SHIPPED', shipped:'Apr 25' },
    { id:'SH-8819', order:'PVL-1039', customer:'NorthStar Health', carrier:'UPS Ground', tracking:'1Z999AA10123456789', status:'PACKED', shipped:'—' },
    { id:'SH-8815', order:'PVL-1034', customer:'Bay Apothecary', carrier:'FedEx', tracking:'781234567890', status:'SHIPPED', shipped:'Apr 22' },
  ];
  return GenericTablePage({
    title: 'Shipments', eyebrow: 'Outbound logistics', lede: '3 shipments in flight today.',
    primaryAction: <button className="btn">Sync tracking</button>,
    columns: [
      {k:'id', l:'Shipment', strong:true, mono:true},
      {k:'order', l:'Order', mono:true, muted:true},
      {k:'customer', l:'Customer'},
      {k:'carrier', l:'Carrier'},
      {k:'tracking', l:'Tracking', mono:true, muted:true},
      {k:'status', l:'Status'},
      {k:'shipped', l:'Shipped', muted:true},
    ],
    rows: shipments,
  });
}
window.AdminShipments = AdminShipments;

function AdminPricing() {
  const prices = [
    { customer:'The Wellness Co.', sku:'PVL-SHJ-60', price:'$14.40', min:12, eff:'Nov 1, 2025', exp:'Oct 31, 2026' },
    { customer:'The Wellness Co.', sku:'PVL-VTT-90', price:'$28.32', min:6, eff:'Nov 1, 2025', exp:'Oct 31, 2026' },
    { customer:'Bay Apothecary', sku:'PVL-SHJ-60', price:'$13.80', min:24, eff:'Sep 15, 2025', exp:'Sep 14, 2026' },
    { customer:'Bay Apothecary', sku:'PVL-VTT-90', price:'$26.50', min:12, eff:'Sep 15, 2025', exp:'Sep 14, 2026' },
    { customer:'NorthStar Health', sku:'PVL-SHJ-60', price:'$15.00', min:12, eff:'Jan 1, 2026', exp:'Open' },
  ];
  return GenericTablePage({
    title: 'Customer pricing', eyebrow: 'Contracts',
    lede: 'Active contract pricing applies automatically when customers place orders.',
    primaryAction: <><button className="btn">Approve SKU</button><button className="btn gold"><Ico.plus width="13" height="13"/> Add contract</button></>,
    columns: [
      {k:'customer', l:'Customer', strong:true},
      {k:'sku', l:'SKU', mono:true},
      {k:'price', l:'Price', strong:true, num:true},
      {k:'min', l:'Min qty', num:true},
      {k:'eff', l:'Effective', muted:true},
      {k:'exp', l:'Expires', muted:true},
    ],
    rows: prices,
  });
}
window.AdminPricing = AdminPricing;

function AdminReports() {
  return (
    <div className="page">
      <div className="page-head">
        <div><div className="eyebrow">Analytics</div><h1>Reports</h1></div>
      </div>
      <div className="empty card"><div className="glyph"><Ico.chart width="22" height="22"/></div>Reports module coming soon — pre-built views for revenue, AR aging, SKU velocity, and customer cohort.</div>
    </div>
  );
}
window.AdminReports = AdminReports;
