// Customer-side pages
const { useState: useStateC } = React;

function StatusPill({ status }) {
  const tone = window.STATUS_PILLS[status] || 'muted';
  return <span className={'pill ' + tone}><span className="dot"/>{status.replace(/_/g,' ')}</span>;
}
window.StatusPill = StatusPill;

// LOGIN
function LoginPage({ onLogin }) {
  const [u, setU] = useStateC('sarah@thewellness.co');
  const [p, setP] = useStateC('••••••••');
  return (
    <div className="login-shell">
      <div className="login-art">
        <div className="marble"/>
        <div className="top">
          <BrandMark size={44}/>
          <div>
            <div style={{fontFamily:'var(--pvl-display-font)', fontSize:26, fontWeight:800, letterSpacing:'-0.028em'}}>provibe<span style={{color:'#c9a04a'}}>life</span></div>
            <div style={{fontSize:10.5, letterSpacing:'0.22em', textTransform:'uppercase', color:'#c9a04a', marginTop:3}}>Wholesale Portal</div>
          </div>
        </div>
        <div className="pitch">
          <div className="eyebrow">Trusted by 800+ retailers</div>
          <h2>The wellness shelf, restocked.</h2>
          <p>Place wholesale orders, track shipments, and manage invoices for the Pro Vibe Life line — all in one workspace.</p>
        </div>
        <div className="meta">
          <span>Net-30 terms</span>
          <span>·</span>
          <span>Free freight over $700</span>
          <span>·</span>
          <span>Lab-tested batches</span>
        </div>
      </div>
      <div className="login-form">
        <div className="inner">
          <div className="eyebrow">Sign in</div>
          <h1 className="font-display" style={{fontSize:32, margin:'6px 0 6px', letterSpacing:'-0.015em'}}>Welcome back.</h1>
          <p className="muted" style={{margin:'0 0 26px'}}>Enter your credentials to continue.</p>
          <form onSubmit={e => { e.preventDefault(); onLogin(); }} className="vstack" style={{gap:14}}>
            <div className="field">
              <label className="label">Email</label>
              <input className="input" value={u} onChange={e=>setU(e.target.value)} autoFocus/>
            </div>
            <div className="field">
              <label className="label" style={{display:'flex', justifyContent:'space-between'}}>
                <span>Password</span>
                <a className="muted" style={{textTransform:'none', letterSpacing:0, fontSize:11.5, fontWeight:500}}>Forgot?</a>
              </label>
              <input className="input" type="password" value={p} onChange={e=>setP(e.target.value)}/>
            </div>
            <button type="submit" className="btn gold lg block" style={{marginTop:6}}>Sign in to portal <Ico.arrow width="16" height="16"/></button>
            <div className="muted" style={{fontSize:12, textAlign:'center', marginTop:6}}>
              Not a wholesale partner yet? <a style={{color:'var(--pvl-text)', fontWeight:600}}>Apply for an account →</a>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
window.LoginPage = LoginPage;

// CUSTOMER DASHBOARD
function CustomerDashboard({ go }) {
  return (
    <div className="page">
      <div className="page-head">
        <div>
          <div className="eyebrow">The Wellness Co. — Tier B retailer</div>
          <h1>Good afternoon, Sarah.</h1>
          <p className="lede">Your reorder window is open through May 12. Two invoices need attention.</p>
        </div>
        <div className="right">
          <button className="btn">Download statement <Ico.download width="14" height="14"/></button>
          <button className="btn gold" onClick={()=>go('order_new')}><Ico.plus width="14" height="14"/> New order</button>
        </div>
      </div>

      <div className="stats">
        <div className="stat feature">
          <div className="lbl">Lifetime spend</div>
          <div className="v tabular">$48,209</div>
          <div className="delta" style={{color:'rgba(247,241,222,0.6)'}}>—You're 12% from <b style={{color:'#c9a04a'}}>Tier A pricing</b></div>
          <div className="gold-line"/>
        </div>
        <div className="stat">
          <div className="lbl">Open orders</div>
          <div className="v tabular">2</div>
          <div className="delta">1 packed · 1 in review</div>
        </div>
        <div className="stat">
          <div className="lbl">Open invoices</div>
          <div className="v tabular">2</div>
          <div className="delta down">$3,186 · 1 due May 27</div>
        </div>
        <div className="stat">
          <div className="lbl">Avg cycle time</div>
          <div className="v tabular">3.4d</div>
          <div className="delta up">Order → ship</div>
        </div>
      </div>

      <div className="grid-2">
        <div className="vstack" style={{gap:18}}>
          <div className="card flush">
            <div className="card-head">
              <h3>Recent orders</h3>
              <a className="muted" style={{fontSize:12.5, fontWeight:600}} onClick={()=>go('orders')}>View all →</a>
            </div>
            <div className="tbl-wrap">
              <table className="tbl">
                <thead><tr><th>Order</th><th>Items</th><th>Status</th><th className="num">Total</th><th>Submitted</th></tr></thead>
                <tbody>
                  {window.ORDERS.slice(0,4).map(o => (
                    <tr key={o.id} onClick={()=>go('order_detail', o.id)}>
                      <td className="strong mono">{o.id}</td>
                      <td className="muted">{o.items} SKUs</td>
                      <td><StatusPill status={o.status}/></td>
                      <td className="num strong">${o.total.toLocaleString(undefined,{minimumFractionDigits:2})}</td>
                      <td className="muted">{o.submitted}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="card">
            <h3 style={{margin:'0 0 10px', fontSize:15}}>Account snapshot</h3>
            <div className="grid-3">
              <div className="kv"><div className="k">Payment terms</div><div className="v">{window.PAYMENT_TERMS_LABEL[window.ME_CUSTOMER.payment_terms]}</div></div>
              <div className="kv"><div className="k">Credit limit</div><div className="v">{window.money(window.ME_CUSTOMER.credit_limit)}</div></div>
              <div className="kv"><div className="k">Preferred carrier</div><div className="v">{window.ME_CUSTOMER.preferred_carrier || '—'}</div></div>
            </div>
            <div className="thin-divider"/>
            <div className="kv"><div className="k">Billing address</div><div className="v muted">{window.ME_CUSTOMER.billing_address}</div></div>
          </div>

          <div className="promo">
            <div className="marble"/>
            <div style={{position:'relative', flex:1}}>
              <div className="eyebrow" style={{color:'#c9a04a'}}>Spring restock</div>
              <h3>Shilajit batch SHJ-441 has arrived.</h3>
              <p>Fresh fulvic-acid potency tested at 78%. Reorder before May 5 to lock in current pricing.</p>
            </div>
            <button className="btn gold" onClick={()=>go('order_new')}>Reorder <Ico.arrow width="14" height="14"/></button>
          </div>
        </div>

        <div className="vstack" style={{gap:18}}>
          <div className="card">
            <div className="hstack" style={{justifyContent:'space-between', marginBottom:10}}>
              <h3 style={{margin:0, fontSize:15}}>Pay invoices</h3>
              <span className="pill amber"><span className="dot"/>2 open</span>
            </div>
            <ul className="activity">
              {window.INVOICES.filter(i=>i.status!=='PAID').slice(0,3).map(inv => (
                <li key={inv.id}>
                  <div className="when mono" style={{width:78, flex:'0 0 78px'}}>{inv.due}</div>
                  <div className="what">
                    <div><b className="mono">{inv.id}</b> · ${inv.total.toLocaleString(undefined,{minimumFractionDigits:2})}</div>
                    <div className="muted" style={{fontSize:12}}>Order {inv.order}</div>
                  </div>
                  <button className="btn sm">Pay <Ico.external width="11" height="11"/></button>
                </li>
              ))}
            </ul>
          </div>

          <div className="card">
            <h3 style={{margin:'0 0 10px', fontSize:15}}>Quick reorder</h3>
            <p className="muted" style={{fontSize:12.5, margin:'0 0 12px'}}>Your last 30-day mix.</p>
            {window.PRODUCTS.slice(0,2).map(p => (
              <div key={p.id} style={{display:'flex', alignItems:'center', gap:12, padding:'10px 0', borderTop:'1px dashed var(--pvl-paper-3)'}}>
                <div style={{width:40, height:40, borderRadius:8, background:'var(--pvl-ink)', display:'grid', placeItems:'center', overflow:'hidden'}}>
                  {p.img ? <img src={p.img} style={{width:'90%', height:'90%', objectFit:'contain'}}/> : <Ico.pkg style={{color:'#c9a04a'}} width="18" height="18"/>}
                </div>
                <div style={{flex:1}}>
                  <div style={{fontWeight:600, fontSize:13.5}}>{p.name}</div>
                  <div className="muted mono" style={{fontSize:11}}>{p.sku} · ${p.wholesale.toFixed(2)}</div>
                </div>
                <button className="btn sm" onClick={()=>go('order_new')}><Ico.plus width="12" height="12"/></button>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
window.CustomerDashboard = CustomerDashboard;

// NEW ORDER
function NewOrder({ go, cart, setCart }) {
  const [po, setPo] = useStateC('PO-44211');
  const [shipDate, setShipDate] = useStateC('2026-05-08');
  const [addr, setAddr] = useStateC('a1');

  const updateQty = (id, q) => {
    const next = { ...cart };
    if (q <= 0) delete next[id]; else next[id] = q;
    setCart(next);
  };
  const total = window.PRODUCTS.reduce((s, p) => s + (cart[p.id] || 0) * p.wholesale, 0);
  const lineCount = Object.values(cart).reduce((a,b)=>a+b,0);

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <div className="eyebrow">Order · Step 1 of 3</div>
          <h1>New order</h1>
          <p className="lede">Pricing reflects your active contract through October 2026. Add quantities below; minimums shown per SKU.</p>
        </div>
      </div>

      <div className="steps">
        <div className="step active"><span className="num">1</span> Build cart</div>
        <span className="arrow">›</span>
        <div className="step"><span className="num">2</span> Verify & freight</div>
        <span className="arrow">›</span>
        <div className="step"><span className="num">3</span> Submit</div>
      </div>

      <div className="grid-2">
        <div className="vstack" style={{gap:16}}>
          <div className="card">
            <div className="grid-3">
              <div className="field">
                <label className="label">PO Number</label>
                <input className="input" value={po} onChange={e=>setPo(e.target.value)}/>
              </div>
              <div className="field">
                <label className="label">Requested ship date</label>
                <input className="input" type="date" value={shipDate} onChange={e=>setShipDate(e.target.value)}/>
              </div>
              <div className="field">
                <label className="label">Ship to</label>
                <select className="input" value={addr} onChange={e=>setAddr(e.target.value)}>
                  {window.ADDRESSES.map(a => <option key={a.id} value={a.id}>{a.label} — {a.city}, {a.state}</option>)}
                </select>
              </div>
            </div>
          </div>

          <div className="hstack" style={{justifyContent:'space-between'}}>
            <div className="eyebrow">Approved catalog · 4 SKUs</div>
            <button className="menu"><Ico.filter width="13" height="13"/> All categories</button>
          </div>

          <div className="grid-cards">
            {window.PRODUCTS.map(p => (
              <div key={p.id} className="product">
                <div className="img">
                  <div className="gold-glow"/>
                  {p.img ? <img src={p.img} alt={p.name}/> : <BrandMark size={56}/>}
                </div>
                <div className="meta">
                  <div className="sku">{p.sku}</div>
                  <h4>{p.name}</h4>
                  <div className="muted" style={{fontSize:12.5}}>{p.tagline}</div>
                </div>
                <div className="price-row">
                  <span className="price">${p.wholesale.toFixed(2)}</span>
                  <span className="per">/unit</span>
                  <span className="muted" style={{fontSize:11.5, marginLeft:'auto', textDecoration:'line-through'}}>MSRP ${p.msrp}</span>
                </div>
                {p.available ? (
                  <div className="row">
                    <div className="muted" style={{fontSize:11.5}}>Min {p.minQty} · {p.lead}</div>
                    {(cart[p.id] || 0) === 0 ? (
                      <button className="btn sm" onClick={()=>updateQty(p.id, p.minQty)}><Ico.plus width="12" height="12"/> Add</button>
                    ) : (
                      <div className="qty">
                        <button onClick={()=>updateQty(p.id, Math.max(0, (cart[p.id]||0) - 1))}>−</button>
                        <input value={cart[p.id]} onChange={e=>updateQty(p.id, Math.max(0, parseInt(e.target.value||'0',10)))}/>
                        <button onClick={()=>updateQty(p.id, (cart[p.id]||0) + 1)}>+</button>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="note amber" style={{fontSize:12}}><Ico.shield width="14" height="14"/>{p.reason}</div>
                )}
              </div>
            ))}
          </div>
        </div>

        <div className="summary">
          <div className="eyebrow">Order summary</div>
          <div className="row"><span className="muted">Line items</span><span className="v tabular">{lineCount}</span></div>
          <div className="row"><span className="muted">Subtotal</span><span className="v tabular">${total.toFixed(2)}</span></div>
          <div className="row"><span className="muted">Estimated freight</span><span className="v tabular muted">Calculated next</span></div>
          <div className="row"><span className="muted">Tax</span><span className="v tabular muted">—</span></div>
          <hr/>
          <div className="row total"><span className="l">Subtotal due</span><span className="v">${total.toFixed(2)}</span></div>
          <button className="btn gold lg block" disabled={lineCount===0} onClick={()=>go('order_review')}>
            Continue to verify <Ico.arrow width="14" height="14"/>
          </button>
          <div className="note gray">
            <Ico.shield width="14" height="14"/>
            <span>Net-30 terms · contract pricing locked through Oct 31, 2026 · all batches lab-tested.</span>
          </div>
        </div>
      </div>
    </div>
  );
}
window.NewOrder = NewOrder;

// ORDER REVIEW
function OrderReview({ go, cart, setCart }) {
  const lines = window.PRODUCTS.filter(p => cart[p.id]).map(p => ({ ...p, q: cart[p.id], ext: p.wholesale * cart[p.id] }));
  const subtotal = lines.reduce((s,l) => s + l.ext, 0);
  const freight = subtotal > 700 ? 0 : 38.40;
  const tax = subtotal * 0.0725;
  const total = subtotal + freight + tax;
  return (
    <div className="page">
      <div className="page-head">
        <div>
          <button className="btn ghost sm" onClick={()=>go('order_new')} style={{marginBottom:8, padding:'4px 8px'}}><Ico.back width="13" height="13"/> Back to cart</button>
          <div className="eyebrow">Order · Step 2 of 3</div>
          <h1>Verify & confirm</h1>
          <p className="lede">Freight has been quoted via UPS Ground. Review pricing, terms, and ship-to before submitting.</p>
        </div>
      </div>

      <div className="steps">
        <div className="step done"><span className="num"><Ico.check width="12" height="12"/></span> Build cart</div>
        <span className="arrow">›</span>
        <div className="step active"><span className="num">2</span> Verify & freight</div>
        <span className="arrow">›</span>
        <div className="step"><span className="num">3</span> Submit</div>
      </div>

      <div className="grid-2">
        <div className="vstack" style={{gap:16}}>
          <div className="card">
            <div className="grid-3">
              <div className="kv"><div className="k">PO Number</div><div className="v mono">PO-44211</div></div>
              <div className="kv"><div className="k">Requested ship</div><div className="v">May 8, 2026</div></div>
              <div className="kv"><div className="k">Terms</div><div className="v">Net-30 · contract pricing</div></div>
            </div>
            <div className="thin-divider"/>
            <div className="grid-3">
              <div className="kv" style={{gridColumn:'span 2'}}>
                <div className="k">Ship to</div>
                <div className="v"><b>Main Warehouse</b> — 2410 Industry Way, Bay 14<br/><span className="muted">Sacramento, CA 95815 · Sarah Hayes · (916) 555-0142</span></div>
              </div>
              <div className="kv">
                <div className="k">Carrier (quoted)</div>
                <div className="v">UPS Ground · 3 day<br/><span className="muted mono" style={{fontSize:11.5}}>RATE-Q-44832 · USD</span></div>
              </div>
            </div>
          </div>

          <div className="card flush">
            <div className="card-head"><h3>Line items</h3></div>
            <div className="tbl-wrap">
              <table className="tbl">
                <thead><tr><th>SKU</th><th>Item</th><th className="num">Qty</th><th className="num">Unit</th><th className="num">Extended</th></tr></thead>
                <tbody>
                  {lines.length === 0 ? (
                    <tr><td colSpan="5"><div className="empty">Your cart is empty. <a onClick={()=>go('order_new')} style={{color:'var(--pvl-gold-deep)', fontWeight:600}}>Add items →</a></div></td></tr>
                  ) : lines.map(l => (
                    <tr key={l.id}>
                      <td className="mono">{l.sku}</td>
                      <td className="strong">{l.name}<div className="muted" style={{fontSize:12, fontWeight:400}}>{l.tagline}</div></td>
                      <td className="num strong">{l.q}</td>
                      <td className="num">${l.wholesale.toFixed(2)}</td>
                      <td className="num strong">${l.ext.toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <div className="summary">
          <div className="eyebrow">Order summary</div>
          <div className="row"><span className="muted">Subtotal</span><span className="v tabular">${subtotal.toFixed(2)}</span></div>
          <div className="row"><span className="muted">Estimated freight</span><span className="v tabular">{freight === 0 ? <span style={{color:'var(--pvl-success)', fontWeight:600}}>FREE</span> : `$${freight.toFixed(2)}`}</span></div>
          <div className="row"><span className="muted">Tax (CA · 7.25%)</span><span className="v tabular">${tax.toFixed(2)}</span></div>
          <hr/>
          <div className="row total"><span className="l">Estimated total</span><span className="v">${total.toFixed(2)}</span></div>
          <button className="btn gold lg block" disabled={lines.length===0} onClick={() => { setCart({}); go('order_confirmed'); }}>
            Submit order <Ico.check width="14" height="14"/>
          </button>
          <button className="btn block" onClick={()=>go('order_new')}>Edit cart</button>
          <div className="note gray">By submitting, you accept Pro Vibe Life wholesale Terms & MAP policy.</div>
        </div>
      </div>
    </div>
  );
}
window.OrderReview = OrderReview;

// CONFIRMATION
function OrderConfirmed({ go }) {
  return (
    <div className="page" style={{maxWidth:720}}>
      <div className="card" style={{textAlign:'center', padding:'48px 32px', position:'relative', overflow:'hidden'}}>
        <div style={{position:'absolute', inset:0, background:'radial-gradient(circle at 50% 0%, color-mix(in srgb, var(--pvl-gold) 12%, transparent), transparent 60%)', pointerEvents:'none'}}/>
        <div style={{position:'relative'}}>
          <div style={{width:72, height:72, margin:'0 auto 18px', borderRadius:'50%', border:'1.5px solid var(--pvl-gold)', display:'grid', placeItems:'center', color:'var(--pvl-gold-deep)'}}>
            <Ico.check width="36" height="36"/>
          </div>
          <div className="eyebrow">Order received</div>
          <h1 className="font-display" style={{fontSize:34, margin:'8px 0 10px', letterSpacing:'-0.015em'}}>Order PVL-1043 is in.</h1>
          <p className="muted" style={{margin:'0 auto 22px', maxWidth:'46ch'}}>We'll review and approve within one business hour. You'll get a tracking number once it ships from Sacramento.</p>
          <div className="hstack" style={{justifyContent:'center', gap:10, flexWrap:'wrap'}}>
            <button className="btn" onClick={()=>go('orders')}>View order history</button>
            <button className="btn gold" onClick={()=>go('dashboard')}>Back to dashboard</button>
          </div>
        </div>
      </div>
    </div>
  );
}
window.OrderConfirmed = OrderConfirmed;

// ORDER HISTORY
function OrderHistory({ go }) {
  const [filter, setFilter] = useStateC('all');
  const filtered = filter === 'all' ? window.ORDERS : window.ORDERS.filter(o => {
    if (filter === 'open') return ['SUBMITTED','APPROVED','PACKED','ON_HOLD'].includes(o.status);
    if (filter === 'shipped') return o.status === 'SHIPPED';
    if (filter === 'paid') return o.status === 'PAID';
    return true;
  });
  return (
    <div className="page">
      <div className="page-head">
        <div>
          <div className="eyebrow">All time · 24 orders</div>
          <h1>Order history</h1>
        </div>
        <div className="right">
          <button className="btn">Export CSV <Ico.download width="13" height="13"/></button>
          <button className="btn gold" onClick={()=>go('order_new')}><Ico.plus width="13" height="13"/> New order</button>
        </div>
      </div>
      <div className="hstack" style={{gap:6, marginBottom:14, flexWrap:'wrap'}}>
        {[['all','All'],['open','Open'],['shipped','Shipped'],['paid','Paid']].map(([k,l]) => (
          <button key={k} className="btn sm" style={{background: filter===k ? 'var(--pvl-ink)' : 'var(--pvl-bone)', color: filter===k ? 'var(--pvl-paper)' : 'var(--pvl-text)', borderColor: filter===k ? 'var(--pvl-ink)' : 'var(--pvl-paper-3)'}} onClick={()=>setFilter(k)}>{l}</button>
        ))}
      </div>
      <div className="card flush">
        <div className="tbl-wrap">
          <table className="tbl">
            <thead><tr><th>Order</th><th>PO</th><th>Submitted</th><th>Items</th><th>Status</th><th className="num">Total</th><th></th></tr></thead>
            <tbody>
              {filtered.map(o => (
                <tr key={o.id} onClick={()=>go('order_detail', o.id)}>
                  <td className="strong mono">{o.id}</td>
                  <td className="mono muted">{o.po}</td>
                  <td className="muted">{o.submitted}</td>
                  <td>{o.items} SKUs</td>
                  <td><StatusPill status={o.status}/></td>
                  <td className="num strong">${o.total.toLocaleString(undefined,{minimumFractionDigits:2})}</td>
                  <td className="num"><button className="btn sm ghost"><Ico.arrow width="13" height="13"/></button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
window.OrderHistory = OrderHistory;

// ORDER DETAIL
function OrderDetail({ go, role }) {
  const o = window.ORDERS[0];
  return (
    <div className="page">
      <div className="page-head">
        <div>
          <button className="btn ghost sm" onClick={()=>go(role==='admin' ? 'admin_orders' : 'orders')} style={{marginBottom:8, padding:'4px 8px'}}><Ico.back width="13" height="13"/> Back</button>
          <div className="eyebrow">Order detail</div>
          <h1 style={{display:'flex', alignItems:'center', gap:14, flexWrap:'wrap'}}>
            <span className="mono">{o.id}</span>
            <StatusPill status={o.status}/>
          </h1>
          <p className="lede">Submitted {o.submitted} · PO {o.po} · {o.customer}</p>
        </div>
        <div className="right">
          <button className="btn">Print packing slip</button>
          {role === 'admin' && <button className="btn primary"><Ico.check width="13" height="13"/> Approve order</button>}
        </div>
      </div>

      <div className="grid-2">
        <div className="vstack" style={{gap:16}}>
          <div className="card flush">
            <div className="card-head"><h3>Line items</h3><span className="muted" style={{fontSize:12.5}}>{o.items} SKUs · 124 units</span></div>
            <div className="tbl-wrap">
              <table className="tbl">
                <thead><tr><th>SKU</th><th>Item</th><th className="num">Qty</th><th className="num">Unit</th><th className="num">Extended</th></tr></thead>
                <tbody>
                  <tr><td className="mono">PVL-SHJ-60</td><td className="strong">Shilajit Resin Tablets<div className="muted" style={{fontSize:12, fontWeight:400}}>Pure Mountain Resin · 60 tablets</div></td><td className="num strong">72</td><td className="num">$14.40</td><td className="num strong">$1,036.80</td></tr>
                  <tr><td className="mono">PVL-VTT-90</td><td className="strong">Vitali-T<div className="muted" style={{fontSize:12, fontWeight:400}}>Natural Testosterone Support · 90 caps</div></td><td className="num strong">24</td><td className="num">$28.32</td><td className="num strong">$679.68</td></tr>
                  <tr><td className="mono">PVL-BUN-01</td><td className="strong">Performance Bundle</td><td className="num strong">3</td><td className="num">$41.50</td><td className="num strong">$124.50</td></tr>
                </tbody>
              </table>
            </div>
          </div>

          <div className="card">
            <h3 style={{margin:'0 0 14px', fontSize:15}}>Activity</h3>
            <ul className="activity">
              <li><div className="when">Today, 2:14p</div><div className="what"><b>Sarah Hayes</b> submitted order via portal</div></li>
              <li><div className="when">Today, 2:18p</div><div className="what">Freight quoted: UPS Ground · 3 day · <span className="mono">$38.40</span></div></li>
              <li><div className="when">Today, 2:21p</div><div className="what">Contract pricing applied · <b className="gold-text">12% volume discount</b> qualified</div></li>
              <li><div className="when">Today, 3:02p</div><div className="what"><b>Mason Cole</b> assigned to fulfillment queue</div></li>
            </ul>
          </div>
        </div>

        <div className="vstack" style={{gap:16}}>
          <div className="summary" style={{position:'static'}}>
            <div className="eyebrow">Totals</div>
            <div className="row"><span className="muted">Subtotal</span><span className="v tabular">$1,840.98</span></div>
            <div className="row"><span className="muted">Volume discount</span><span className="v tabular" style={{color:'var(--pvl-success)'}}>−$220.92</span></div>
            <div className="row"><span className="muted">Freight</span><span className="v tabular">$38.40</span></div>
            <div className="row"><span className="muted">Tax</span><span className="v tabular">$183.94</span></div>
            <hr/>
            <div className="row total"><span className="l">Order total</span><span className="v">${o.total.toFixed(2)}</span></div>
          </div>
          <div className="card">
            <div className="eyebrow" style={{marginBottom:10}}>Ship to</div>
            <div style={{fontSize:13.5, lineHeight:1.55}}>
              <b>Main Warehouse</b><br/>
              2410 Industry Way, Bay 14<br/>
              Sacramento, CA 95815<br/>
              <span className="muted">Sarah Hayes · (916) 555-0142</span>
            </div>
            <div className="thin-divider"/>
            <div className="kv"><div className="k">Carrier</div><div className="v">UPS Ground · 3 day</div></div>
            <div className="kv" style={{marginTop:8}}><div className="k">Tracking</div><div className="v muted">Available after pack</div></div>
          </div>

          {role === 'admin' && (
            <div className="card dark" style={{padding:18}}>
              <div className="eyebrow" style={{color:'rgba(247,241,222,0.55)', marginBottom:10}}>Admin · Workflow</div>
              <div className="vstack" style={{gap:8}}>
                <button className="btn gold block">Approve & release to warehouse</button>
                <button className="btn block" style={{background:'transparent', color:'#f7f1de', borderColor:'#2a2a30'}}>Place on hold</button>
                <button className="btn block danger" style={{background:'transparent'}}>Cancel order</button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
window.OrderDetail = OrderDetail;

// INVOICES
function InvoicesPage() {
  return (
    <div className="page">
      <div className="page-head">
        <div>
          <div className="eyebrow">Billing</div>
          <h1>Invoices</h1>
          <p className="lede">2 open · $3,186.00 outstanding · oldest due May 27.</p>
        </div>
        <div className="right">
          <button className="btn">Download statement <Ico.download width="13" height="13"/></button>
        </div>
      </div>

      <div className="card flush">
        <div className="tbl-wrap">
          <table className="tbl">
            <thead><tr><th>Invoice</th><th>Order</th><th>Issued</th><th>Due</th><th>Status</th><th className="num">Total</th><th></th></tr></thead>
            <tbody>
              {window.INVOICES.map(inv => (
                <tr key={inv.id}>
                  <td className="strong mono">{inv.id}</td>
                  <td className="mono muted">{inv.order}</td>
                  <td className="muted">{inv.issued}</td>
                  <td className="muted">{inv.due}</td>
                  <td><StatusPill status={inv.status}/></td>
                  <td className="num strong">${inv.total.toLocaleString(undefined,{minimumFractionDigits:2})}</td>
                  <td className="num">
                    {inv.status !== 'PAID'
                      ? <a className="btn sm gold" href={inv.stripe_hosted_invoice_url} target="_blank" rel="noreferrer">Pay <Ico.external width="11" height="11"/></a>
                      : <a className="btn sm ghost" href={inv.stripe_invoice_pdf || '#'} target="_blank" rel="noreferrer"><Ico.download width="13" height="13"/></a>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
window.InvoicesPage = InvoicesPage;

// ADDRESSES
function AddressesPage() {
  return (
    <div className="page">
      <div className="page-head">
        <div>
          <div className="eyebrow">Logistics</div>
          <h1>Shipping addresses</h1>
          <p className="lede">Default ship-to is used for new orders. Add up to 10 active locations.</p>
        </div>
        <div className="right">
          <button className="btn gold"><Ico.plus width="13" height="13"/> Add address</button>
        </div>
      </div>
      <div className="grid-cards">
        {window.ADDRESSES.map(a => (
          <div key={a.id} className={'addr-card' + (a.isDefault ? ' default' : '')}>
            <div className="lbl-row">
              <b>{a.label}</b>
              {a.isDefault && <span className="pill gold"><span className="dot"/>Default</span>}
            </div>
            <div className="lines">
              {a.line1}{a.line2 ? <>, {a.line2}</> : ''}<br/>
              <span className="mute">{a.city}, {a.state} {a.zip}</span>
            </div>
            <div className="actions">
              <button className="btn sm">Edit</button>
              {!a.isDefault && <button className="btn sm ghost">Set default</button>}
              {!a.isDefault && <button className="btn sm ghost danger">Remove</button>}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
window.AddressesPage = AddressesPage;

// ACCOUNT
function AccountPage() {
  return (
    <div className="page">
      <div className="page-head">
        <div>
          <div className="eyebrow">Profile</div>
          <h1>Account</h1>
        </div>
      </div>
      <div className="grid-2">
        <div className="card">
          <h3 style={{margin:'0 0 14px', fontSize:15}}>Business</h3>
          <div className="vstack" style={{gap:14}}>
            <div className="field"><label className="label">Company</label><input className="input" defaultValue="The Wellness Co."/></div>
            <div className="field"><label className="label">Resale certificate</label><input className="input" defaultValue="CA-SR-44210-981"/></div>
            <div className="field"><label className="label">Payment terms</label><input className="input" defaultValue={window.PAYMENT_TERMS_LABEL[window.ME_CUSTOMER.payment_terms]} disabled/></div>
            <div className="field"><label className="label">Credit limit</label><input className="input" defaultValue={window.money(window.ME_CUSTOMER.credit_limit)} disabled/></div>
            <div className="field"><label className="label">Preferred carrier</label><input className="input" defaultValue={window.ME_CUSTOMER.preferred_carrier || '—'} disabled/></div>
            <div className="field"><label className="label">Stripe customer ID</label><input className="input mono" defaultValue={window.ME_CUSTOMER.stripe_customer_id || '—'} disabled/></div>
          </div>
        </div>
        <div className="card">
          <h3 style={{margin:'0 0 14px', fontSize:15}}>Primary contact</h3>
          <div className="vstack" style={{gap:14}}>
            <div className="field"><label className="label">Name</label><input className="input" defaultValue="Sarah Hayes"/></div>
            <div className="field"><label className="label">Email</label><input className="input" defaultValue="sarah@thewellness.co"/></div>
            <div className="field"><label className="label">Phone</label><input className="input" defaultValue="(916) 555-0142"/></div>
          </div>
        </div>
      </div>
    </div>
  );
}
window.AccountPage = AccountPage;
