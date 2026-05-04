// Pro Vibe Life Portal — main app
const { useState: useS, useEffect: useE } = React;

const TWEAK_DEFAULTS = /*EDITMODE-BEGIN*/{
  "theme": "light",
  "density": "comfortable",
  "navStyle": "sidebar",
  "accent": "gold",
  "displayFont": "monasans"
}/*EDITMODE-END*/;

const DISPLAY_FONTS = {
  monasans:   { stack: "'Mona Sans', 'Manrope', sans-serif",       tracking: '-0.028em', weight: 800, label: 'Mona Sans (default)' },
  manrope:    { stack: "'Manrope', sans-serif",                    tracking: '-0.025em', weight: 800, label: 'Manrope' },
  instrument: { stack: "'Instrument Serif', Georgia, serif",       tracking: '-0.018em', weight: 400, label: 'Instrument Serif' },
  fraunces:   { stack: "'Fraunces', Georgia, serif",               tracking: '-0.012em', weight: 500, label: 'Fraunces (classic)' },
};

// Parse hash params: #mobile=1&route=dashboard&role=admin
function parseHash() {
  const h = (window.location.hash || '').replace(/^#/, '');
  const out = {};
  h.split('&').forEach(p => {
    if (!p) return;
    const [k, v=''] = p.split('=');
    out[decodeURIComponent(k)] = decodeURIComponent(v);
  });
  return out;
}

function App() {
  const initialHash = parseHash();
  const [tweaks, setTweak] = useTweaks(TWEAK_DEFAULTS);
  // In mobile preview, skip login UNLESS the requested route IS the login screen.
  const wantLogin = initialHash.route === 'login';
  const [auth, setAuth] = useS(initialHash.mobile === '1' && !wantLogin);
  const [role, setRole] = useS(initialHash.role === 'admin' ? 'admin' : 'customer');
  const [route, setRoute] = useS(wantLogin ? 'dashboard' : (initialHash.route || 'dashboard'));
  const [cart, setCart] = useS({ shilajit: 72, vitalit: 24, bundle: 3 });
  const isMobilePreview = initialHash.mobile === '1';

  useE(() => {
    if (isMobilePreview) {
      document.documentElement.setAttribute('data-mobile-preview', '1');
    }
  }, [isMobilePreview]);

  useE(() => {
    document.documentElement.setAttribute('data-theme', tweaks.theme);
    document.documentElement.setAttribute('data-density', tweaks.density);
    const f = DISPLAY_FONTS[tweaks.displayFont] || DISPLAY_FONTS.instrument;
    document.documentElement.style.setProperty('--pvl-display-font', f.stack);
    document.documentElement.style.setProperty('--pvl-display-tracking', f.tracking);
    document.documentElement.style.setProperty('--pvl-display-weight', String(f.weight));
  }, [tweaks.theme, tweaks.density, tweaks.displayFont]);

  const go = (r, _id) => { setRoute(r); window.scrollTo({top:0, behavior:'instant'}); };

  if (!auth) return <>
    <LoginPage onLogin={() => setAuth(true)}/>
    <PvlTweaksPanel tweaks={tweaks} setTweak={setTweak}/>
  </>;

  let page = null;
  switch (route) {
    case 'dashboard': page = <CustomerDashboard go={go}/>; break;
    case 'order_new': page = <NewOrder go={go} cart={cart} setCart={setCart}/>; break;
    case 'order_review': page = <OrderReview go={go} cart={cart} setCart={setCart}/>; break;
    case 'order_confirmed': page = <OrderConfirmed go={go}/>; break;
    case 'orders': case 'order_history': page = <OrderHistory go={go}/>; break;
    case 'order_detail': page = <OrderDetail go={go} role="customer"/>; break;
    case 'invoices': page = <InvoicesPage/>; break;
    case 'addresses': page = <AddressesPage/>; break;
    case 'account': page = <AccountPage/>; break;
    case 'admin_dashboard': page = <AdminDashboard go={go}/>; break;
    case 'admin_orders': page = <AdminOrders go={go}/>; break;
    case 'admin_order_detail': page = <OrderDetail go={go} role="admin"/>; break;
    case 'admin_fulfillment': page = <AdminFulfillment go={go}/>; break;
    case 'admin_shipments': page = <AdminShipments/>; break;
    case 'admin_invoices': page = <AdminInvoices/>; break;
    case 'admin_customers': page = <AdminCustomers/>; break;
    case 'admin_products': page = <AdminProducts/>; break;
    case 'admin_pricing': page = <AdminPricing/>; break;
    case 'admin_reports': page = <AdminReports/>; break;
    default: page = <CustomerDashboard go={go}/>;
  }

  return (
    <>
      <div className="app" data-screen-label={route}>
        <Sidebar role={role} setRole={setRole} route={route} go={go}/>
        <div className="main">
          <Topbar route={route} role={role}/>
          {page}
        </div>
      </div>
      <TabBar role={role} route={route} go={go}/>
      <PvlTweaksPanel tweaks={tweaks} setTweak={setTweak} role={role} setRole={setRole} go={go}/>
    </>
  );
}

function PvlTweaksPanel({ tweaks, setTweak, role, setRole, go }) {
  return (
    <TweaksPanel title="Tweaks">
      <TweakSection label="Appearance">
        <TweakRadio label="Theme" value={tweaks.theme} options={[{value:'light', label:'Light'},{value:'dark', label:'Dark'}]} onChange={v=>setTweak('theme', v)}/>
        <TweakRadio label="Density" value={tweaks.density} options={[{value:'compact',label:'Compact'},{value:'comfortable',label:'Comfortable'},{value:'spacious',label:'Spacious'}]} onChange={v=>setTweak('density', v)}/>
        <TweakSelect label="Display font" value={tweaks.displayFont} options={Object.entries(DISPLAY_FONTS).map(([v,f])=>({value:v, label:f.label}))} onChange={v=>setTweak('displayFont', v)}/>
      </TweakSection>
      {role && (
        <TweakSection label="Role">
          <TweakRadio label="View as" value={role} options={[{value:'customer',label:'Customer'},{value:'admin',label:'Admin'}]} onChange={v=>{ setRole(v); go(v==='admin' ? 'admin_dashboard' : 'dashboard'); }}/>
        </TweakSection>
      )}
    </TweaksPanel>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(<App/>);
