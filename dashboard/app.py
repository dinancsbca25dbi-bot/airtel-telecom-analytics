import os, sqlite3
import gzip
import tempfile
import requests
import re
from pathlib import Path
from string import Template
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ====================== AIRTEL | REVENUE COMMAND CENTER ======================
ROOT = Path(__file__).resolve().parent.parent
DB = Path(os.environ.get('AIRTEL_DB', ROOT / 'data' / 'airtel.db'))
LOGO = Path(os.environ.get('AIRTEL_LOGO', ROOT / 'dashboard' / 'airtel-logo.png'))
YEAR = 2025
MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun']
RED, TEAL, GOLD = '#E40000', '#00B894', '#F5A623'
PAL = [RED, '#2F6FED', TEAL, GOLD, '#8B5CF6', '#EC4899', '#14B8A6', '#64748B']
st.set_page_config(page_title='Airtel | Revenue Command Center', page_icon='📡', layout='wide')

# ---------------------------- THEME ----------------------------
THEMES = {
    'light': dict(bg='#F4F6F9', card='#FFFFFF', border='#E5EAF1', text='#101828', muted='#667085', side='#111827',
                  tpl='plotly_white', grid='#E5EAF1', dfilter='none', scale='Reds'),
    'dark':  dict(bg='#0B1220', card='#151E2F', border='#263247', text='#E6EAF2', muted='#9AA7BD', side='#070C16',
                  tpl='plotly_dark', grid='#263247', dfilter='invert(.9) hue-rotate(180deg)', scale='Magma'),
}
with st.sidebar:
    if LOGO.exists():
        st.image(str(LOGO), width=150)
    st.markdown('<div class="brand">airtel<span>.</span></div>'
                '<p style="font-size:11px;letter-spacing:1px;color:#9CA3AF;margin:0 0 6px">REVENUE COMMAND CENTER</p>',
                unsafe_allow_html=True)
    dark = st.toggle('🌙 Dark mode', value=False)
T = THEMES['dark' if dark else 'light']

CSS = Template('''<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');
html,body,[class*="css"]{font-family:Inter,sans-serif}
.stApp{background:$bg;color:$text}
.stApp p,.stApp label,.stApp h1,.stApp h2,.stApp h3,.stApp h4,.stApp li{color:$text}
header[data-testid="stHeader"]{background:transparent;height:2rem}footer,#MainMenu{visibility:hidden}
.block-container{max-width:1750px;padding:.6rem 1.2rem .4rem}
[data-testid="stSidebar"]{background:$side}[data-testid="stSidebar"] *{color:#fff!important}
[data-testid="stSidebar"] [data-baseweb="select"] *{color:#111827!important}
[data-testid="stSidebar"] [data-baseweb="select"]>div{background:#fff;border-radius:10px}
[data-testid="stSidebar"] .stCaption,[data-testid="stSidebar"] small{color:#9CA3AF!important}
[data-testid="stVerticalBlock"]{gap:.4rem}
[data-testid="stPopoverBody"]{background:$card;border:1px solid $border}
[data-testid="stPopoverBody"] label p{color:$text!important}
[data-testid="stPopoverBody"] [data-baseweb="select"]>div{background:$bg}
[data-testid="stPopoverBody"] input{color:$text!important}
[data-testid="stPopover"] button{padding:.05rem .6rem;min-height:1.7rem;font-size:12px;font-weight:700;border-radius:8px;
background:$card;border:1px solid $border;color:$text}
@keyframes rise{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:translateY(0)}}
.brand{font-size:30px;font-weight:900;letter-spacing:-2px;color:#fff}.brand span{color:#ff3030}
.hero{display:flex;justify-content:space-between;align-items:center;background:linear-gradient(115deg,#111827 0%,#202B40 55%,#E40000 150%);
border-radius:16px;padding:10px 20px;animation:rise .5s ease-out;box-shadow:0 8px 24px #10182822}
.hero .t{font-size:20px;font-weight:850;color:#fff!important;letter-spacing:-.5px}.hero .s{font-size:11px;color:#CBD5E1!important}
.hero .r{text-align:right;font-size:11px;color:#CBD5E1!important}
.kpi{background:$card;border:1px solid $border;border-radius:14px;padding:8px 16px;animation:rise .55s ease-out;transition:.25s}
.kpi:hover{transform:translateY(-2px);box-shadow:0 8px 20px #00000018}
.k-label{font-size:10.5px;color:$muted!important;font-weight:700;text-transform:uppercase;letter-spacing:.6px}
.k-value{font-size:23px;font-weight:850;letter-spacing:-1px;color:$text!important;margin:1px 0 0}
.tlabel{font-size:13px;font-weight:700;padding-top:.35rem;color:$text}
.k-note{font-size:10.5px;color:$muted!important}
[data-baseweb="tab-list"]{gap:8px}[data-baseweb="tab"]{font-weight:700;border-radius:10px;padding:5px 14px;color:$muted}
[aria-selected="true"]{color:#E40000!important}
.stDataFrame{border-radius:12px;border:1px solid $border;filter:$dfilter}
[data-testid="stPlotlyChart"]{background:$card;border:1px solid $border;border-radius:14px;padding:2px}
.stDownloadButton button{border-radius:10px;font-weight:700;width:100%}
@media(prefers-reduced-motion:reduce){*,*::before,*::after{animation:none!important;transition:none!important}}
</style>''')
st.markdown(CSS.substitute(T), unsafe_allow_html=True)

CH = 255  # chart height (keeps each tab on one screen)

def style(fig, h=CH, legend=False):
    fig.update_layout(template=T['tpl'], height=h, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                      margin=dict(l=8, r=10, t=36, b=6), font_family='Inter', font_color=T['text'],
                      title_font_size=13, showlegend=legend)
    fig.update_xaxes(gridcolor=T['grid'], title_font_size=11)
    fig.update_yaxes(gridcolor=T['grid'], title_font_size=11)
    return fig

def show(fig): st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
def empty(msg='No data for this filter.'): st.info(msg)

# ---------------------------- DATA ----------------------------
@st.cache_resource
def conn():
    if not DB.exists():
        archive_path = None
        temp_db = DB.with_suffix('.db.tmp')
        try:
            file_id = '1n0i2UU2U95sKEe28d7jYCl2Q0NJufwO3'
            download_url = f'https://drive.google.com/uc?export=download&id={file_id}'
            with tempfile.NamedTemporaryFile(prefix='airtel-download-', suffix='.gz', delete=False) as temp:
                archive_path = Path(temp.name)
                session = requests.Session()
                response = session.get(download_url, stream=True, timeout=(20, 180))
                confirmation = next((value for key, value in response.cookies.items()
                                     if key.startswith('download_warning')), None)
                if confirmation:
                    response.close()
                    response = session.get(download_url, params={'export': 'download', 'id': file_id,
                                                                 'confirm': confirmation},
                                           stream=True, timeout=(20, 180))
                elif 'text/html' in response.headers.get('Content-Type', '').lower():
                    page = response.text
                    response.close()
                    match = re.search(r'name=[\"\']confirm[\"\']\s+value=[\"\']([^\"\']+)', page)
                    confirmation = match.group(1) if match else 't'
                    response = session.get(download_url, params={'export': 'download', 'id': file_id,
                                                                 'confirm': confirmation},
                                           stream=True, timeout=(20, 180))
                with response:
                    response.raise_for_status()
                    if 'text/html' in response.headers.get('Content-Type', '').lower():
                        raise ValueError('Google Drive returned a sharing or confirmation page instead of the file.')
                    for chunk in response.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            temp.write(chunk)
            with archive_path.open('rb') as archive:
                if archive.read(2) != b'\x1f\x8b':
                    raise ValueError('The Drive download is not a gzip file.')
            DB.parent.mkdir(parents=True, exist_ok=True)
            with gzip.open(archive_path, 'rb') as compressed, temp_db.open('wb') as database:
                while chunk := compressed.read(1024 * 1024):
                    database.write(chunk)
            archive_path.unlink(missing_ok=True)
            with sqlite3.connect(f'file:{temp_db.resolve().as_posix()}?mode=ro', uri=True) as downloaded:
                result = downloaded.execute('PRAGMA integrity_check').fetchone()[0]
                names = {row[0] for row in downloaded.execute("select name from sqlite_master where type in ('table','view')")}
            required = {'customers', 'circles', 'plans', 'recharges'}
            if result != 'ok' or not required.issubset(names):
                temp_db.unlink(missing_ok=True)
                raise ValueError('The downloaded file is not a valid Airtel database.')
            temp_db.replace(DB)
        except Exception as exc:
            if archive_path:
                archive_path.unlink(missing_ok=True)
            temp_db.unlink(missing_ok=True)
            st.error('Google Drive did not provide the database file. Check that its link opens the .gz download in a private browser window, then reboot this app.')
            st.stop()
    c = sqlite3.connect(str(DB), check_same_thread=False)
    names = {r[0] for r in c.execute("select name from sqlite_master where type in ('table','view')")}
    miss = {'customers', 'circles', 'plans', 'recharges'} - names
    if miss:
        st.error('Database missing tables: ' + ', '.join(sorted(miss))); st.stop()
    return c

@st.cache_data(show_spinner=False)
def load():
    c = conn()
    cust = pd.read_sql_query('''select c.customer_id, c.connection_type, ci.region, p.plan_name, p.price_inr,
        c.arpu_inr as stated_arpu from customers c join circles ci on ci.circle_id=c.circle_id
        join plans p on p.plan_id=c.current_plan_id''', c)
    rech = pd.read_sql_query('select customer_id, recharge_date, amount_inr, channel from recharges', c)
    rech['recharge_date'] = pd.to_datetime(rech['recharge_date'])
    rech = rech.merge(cust[['customer_id', 'connection_type', 'region', 'plan_name']], on='customer_id')
    order = pd.read_sql_query('select plan_name from plans group by plan_name order by min(price_inr)', c)['plan_name'].tolist()
    return cust, rech, order

cust_all, rech_all, plan_order = load()

def build_cf(c, r, nm):
    agg = r.groupby('customer_id').agg(recharge_count=('amount_inr', 'size'), recharge_total=('amount_inr', 'sum'))
    cf = c.merge(agg, how='left', left_on='customer_id', right_index=True).fillna({'recharge_count': 0, 'recharge_total': 0})
    cf['actual_arpu'] = cf.recharge_total / max(nm, 1)
    cf['no_pay'] = (cf.recharge_count == 0).astype(int)
    return cf

def summarize(cf, key):
    g = cf.groupby(key).agg(subscribers=('customer_id', 'size'), revenue=('recharge_total', 'sum'),
                            arpu=('actual_arpu', 'mean'), no_pay_pct=('no_pay', 'mean')).reset_index()
    g['no_pay_pct'] = g.no_pay_pct * 100
    return g.sort_values('revenue', ascending=False)

# ---------------------------- GLOBAL FILTERS (sidebar) ----------------------------
with st.sidebar:
    st.markdown('### Global filters')
    ct = st.multiselect('Customer type', sorted(cust_all.connection_type.unique()), placeholder='All')
    rg = st.multiselect('Circle / Region', sorted(cust_all.region.unique()), placeholder='All')
    pl = st.multiselect('Plan', plan_order, placeholder='All')
    ch = st.multiselect('Recharge channel', sorted(rech_all.channel.dropna().unique()), placeholder='All')
    start, end = st.select_slider('Analysis period', options=MONTHS, value=(MONTHS[0], MONTHS[-1]))
    st.caption('Empty = all. Each chart also has its own ⚙ Filter that narrows further inside these global filters.')

mi, mj = MONTHS.index(start), MONTHS.index(end)
d0 = pd.Timestamp(YEAR, mi + 1, 1)
d1 = pd.Timestamp(YEAR, mj + 1, 1) + pd.offsets.MonthEnd(0) + pd.Timedelta(hours=23, minutes=59, seconds=59)
nmonths = mj - mi + 1
period = f'{start}–{end} {YEAR}'

cust = cust_all
if ct: cust = cust[cust.connection_type.isin(ct)]
if rg: cust = cust[cust.region.isin(rg)]
if pl: cust = cust[cust.plan_name.isin(pl)]
if cust.empty:
    st.warning('No records match these filters. Adjust your selection.'); st.stop()

rech_g = rech_all[(rech_all.recharge_date >= d0) & (rech_all.recharge_date <= d1) & rech_all.customer_id.isin(cust.customer_id)]
if ch: rech_g = rech_g[rech_g.channel.isin(ch)]
cf_g = build_cf(cust, rech_g, nmonths)

# ---------------------------- PER-CHART FILTERS ----------------------------
def ms(label, options, key):
    if key in st.session_state:
        st.session_state[key] = [v for v in st.session_state[key] if v in options]
    return st.multiselect(label, options, key=key, placeholder='All')

def scoped(key, dims=('type', 'region', 'plan', 'channel', 'month'), label=None):
    """Shows a small ⚙ Filter popover for ONE chart/table; returns (customer-level df, transaction-level df)."""
    c, r = cust, rech_g
    mo = list(range(mi, mj + 1))
    if label:
        host, lab = st.columns([1, 2.4])
        lab.markdown(f'<div class="tlabel">{label}</div>', unsafe_allow_html=True)
    else:
        host = st.container()
    with host, st.popover('⚙ Filter'):
        if 'type' in dims:
            v = ms('Customer type', sorted(cust.connection_type.unique()), f'{key}_t')
            if v: c = c[c.connection_type.isin(v)]
        if 'region' in dims:
            v = ms('Circle', sorted(cust.region.unique()), f'{key}_r')
            if v: c = c[c.region.isin(v)]
        if 'plan' in dims:
            v = ms('Plan', [p for p in plan_order if p in set(cust.plan_name)], f'{key}_p')
            if v: c = c[c.plan_name.isin(v)]
        if 'channel' in dims:
            v = ms('Channel', sorted(rech_g.channel.dropna().unique()), f'{key}_c')
            if v: r = r[r.channel.isin(v)]
        if 'month' in dims and len(mo) > 1:
            opts = MONTHS[mi:mj + 1]
            k = f'{key}_m'
            if k in st.session_state and not set(st.session_state[k]) <= set(opts):
                del st.session_state[k]
            a, b = st.select_slider('Months', options=opts, value=(opts[0], opts[-1]), key=k)
            mo = list(range(MONTHS.index(a), MONTHS.index(b) + 1))
    r = r[r.customer_id.isin(c.customer_id) & r.recharge_date.dt.month.sub(1).isin(mo)]
    return build_cf(c, r, len(mo)), r

# ---------------------------- HEADER + KPIs ----------------------------
def money(x): return f'₹{x/1e7:.2f} Cr' if x >= 1e7 else (f'₹{x/1e5:.2f} L' if x >= 1e5 else f'₹{x:,.0f}')
def kpi(label, value, note): return f'<div class="kpi"><div class="k-label">{label}</div><div class="k-value">{value}</div><div class="k-note">{note}</div></div>'

rev, subs, payments = float(cf_g.recharge_total.sum()), len(cf_g), int(cf_g.recharge_count.sum())
unpaid, arpu = int(cf_g.no_pay.sum()), float(cf_g.actual_arpu.mean())
scope = f"{', '.join(ct) or 'All types'} · {', '.join(rg) if rg and len(rg) < 4 else (f'{len(rg)} circles' if rg else 'All circles')}"

st.markdown(f'<div class="hero"><div><div class="t">Revenue Command Center</div><div class="s">{scope}</div></div>'
            f'<div class="r">📡 FINANCE & COMMERCIAL ANALYTICS<br>{period}</div></div>', unsafe_allow_html=True)
for col, html in zip(st.columns(4), [
    kpi('Received revenue', money(rev), f'{payments:,} recorded payments'),
    kpi('Subscribers', f'{subs:,}', 'In current filter scope'),
    kpi('Revenue / subscriber / month', f'₹{arpu:,.0f}', f'Price-list average ₹{float(cf_g.stated_arpu.mean()):,.0f}'),
    kpi('No-payment subscribers', f'{unpaid:,} · {unpaid/subs*100:.1f}%', 'No payment in selected period')]):
    col.markdown(html, unsafe_allow_html=True)

# ---------------------------- TABS ----------------------------
T1, T2 = st.tabs(['📊 Revenue Flow & Mix', '🎯 Customer Behaviour & Circles'])
export = {}

with T1:
    a, b, c = st.columns([1, 1.3, 1])
    # 1) SUNBURST — customer type -> plan
    with a:
        cf, r = scoped('sun')
        g = cf.groupby(['connection_type', 'plan_name']).recharge_total.sum().reset_index()
        g = g[g.recharge_total > 0]
        if g.empty: empty()
        else:
            f = px.sunburst(g, path=['connection_type', 'plan_name'], values='recharge_total',
                            color_discrete_sequence=PAL, title='Sunburst Chart · type → plan')
            f.update_traces(insidetextorientation='radial', marker_line_color=T['card'])
            show(style(f))
    # 2) SANKEY — customer type -> plan -> channel
    with b:
        cf, r = scoped('san', dims=('type', 'region', 'plan', 'channel', 'month'))
        if r.empty: empty()
        else:
            l1 = r.groupby(['connection_type', 'plan_name']).amount_inr.sum().reset_index()
            l1.columns = ['s', 't', 'v']
            l2 = r.groupby(['plan_name', 'channel']).amount_inr.sum().reset_index()
            l2.columns = ['s', 't', 'v']
            links = pd.concat([l1, l2])
            nodes = list(dict.fromkeys(list(links.s) + list(links.t)))
            idx = {n: i for i, n in enumerate(nodes)}
            f = go.Figure(go.Sankey(
                node=dict(label=nodes, pad=12, thickness=14, color=[PAL[i % len(PAL)] for i in range(len(nodes))],
                          line=dict(color=T['card'], width=.5)),
                link=dict(source=links.s.map(idx), target=links.t.map(idx), value=links.v,
                          color='rgba(150,160,180,.35)')))
            f.update_layout(title='Sankey Diagram · type → plan → channel')
            show(style(f))
    # 3) WATERFALL — month-on-month revenue change
    with c:
        cf, r = scoped('wat', dims=('type', 'region', 'plan', 'channel'))
        mrev = r.groupby(r.recharge_date.dt.month).amount_inr.sum().sort_index()
        if mrev.empty: empty()
        else:
            labels = [MONTHS[m - 1] for m in mrev.index]
            vals = mrev.values
            y = [vals[0]] + list(vals[1:] - vals[:-1])
            f = go.Figure(go.Waterfall(x=labels, y=y, measure=['absolute'] + ['relative'] * (len(y) - 1),
                                       increasing=dict(marker_color=TEAL), decreasing=dict(marker_color=RED),
                                       totals=dict(marker_color=PAL[1]), connector=dict(line=dict(color=T['grid']))))
            f.update_layout(title='Waterfall Chart · monthly change (₹)')
            show(style(f))

    d, e = st.columns([1.5, 1])
    # 4) HEATMAP — circle x month
    with d:
        cf, r = scoped('hm')
        if r.empty: empty()
        else:
            top = r.groupby('region').amount_inr.sum().nlargest(10).index
            pv = (r[r.region.isin(top)].assign(m=r.recharge_date.dt.month)
                  .pivot_table(index='region', columns='m', values='amount_inr', aggfunc='sum', fill_value=0))
            pv = pv.loc[pv.sum(axis=1).sort_values().index]
            pv.columns = [MONTHS[m - 1] for m in pv.columns]
            f = px.imshow(pv, aspect='auto', color_continuous_scale=T['scale'], text_auto='.2s',
                          title='Heatmap Chart · top circles × month (₹)')
            f.update_coloraxes(showscale=False)
            show(style(f))
    # 5) PLAN TABLE
    with e:
        cf, r = scoped('tpl', label='📋 Table · Plan performance')
        pv = summarize(cf, 'plan_name').rename(columns={'plan_name': 'Plan', 'subscribers': 'Subs', 'revenue': 'Revenue (₹)',
                                                       'arpu': 'Rev/sub/mo (₹)', 'no_pay_pct': 'No pay %'}).round(1)
        export['Plan data'] = pv
        st.dataframe(pv, hide_index=True, use_container_width=True, height=CH + 5)

with T2:
    a, b, c = st.columns([1, 1, 1.2])
    # 6) FUNNEL — payment engagement
    with a:
        cf, r = scoped('fun')
        n = [len(cf)] + [int((cf.recharge_count >= k).sum()) for k in (1, 2, 3, 4)]
        f = go.Figure(go.Funnel(y=['All subscribers', '≥1 payment', '≥2 payments', '≥3 payments', '≥4 payments'], x=n,
                                textinfo='value+percent initial', marker=dict(color=PAL[:5])))
        f.update_layout(title='Funnel Chart · payment engagement')
        show(style(f))
    # 7) RADAR — top circles on 4 normalised metrics
    with b:
        cf, r = scoped('rad', dims=('type', 'plan', 'channel', 'month'))
        rp = summarize(cf, 'region').head(5)
        if rp.empty: empty()
        else:
            rp['pay_rate'] = 100 - rp.no_pay_pct
            cols = {'revenue': 'Revenue', 'subscribers': 'Subscribers', 'arpu': 'ARPU', 'pay_rate': 'Pay rate'}
            f = go.Figure()
            for i, row in enumerate(rp.itertuples()):
                vals = [getattr(row, k) / (rp[k].max() or 1) * 100 for k in cols]
                f.add_trace(go.Scatterpolar(r=vals + vals[:1], theta=list(cols.values()) + [list(cols.values())[0]],
                                            fill='toself', opacity=.55, name=row.region, line_color=PAL[i % len(PAL)]))
            f.update_layout(title='Radar Chart · top 5 circles (0–100)',
                            polar=dict(bgcolor='rgba(0,0,0,0)', radialaxis=dict(gridcolor=T['grid'], showticklabels=False),
                                       angularaxis=dict(gridcolor=T['grid'])),
                            legend=dict(orientation='h', y=-.05, font_size=9))
            show(style(f, legend=True))
    # 8) VIOLIN — revenue/subscriber distribution by plan
    with c:
        cf, r = scoped('vio')
        if cf.empty: empty()
        else:
            f = px.violin(cf, x='plan_name', y='actual_arpu', box=True, points=False, color_discrete_sequence=[RED],
                          category_orders={'plan_name': plan_order}, title='Violin Plot · revenue/sub/month by plan',
                          labels={'plan_name': '', 'actual_arpu': '₹ / month'})
            show(style(f))

    d, e = st.columns([1.5, 1])
    # 9) TREEMAP — circle -> plan
    with d:
        cf, r = scoped('tre')
        g = cf.groupby(['region', 'plan_name']).recharge_total.sum().reset_index()
        g = g[g.recharge_total > 0]
        if g.empty: empty()
        else:
            f = px.treemap(g, path=['region', 'plan_name'], values='recharge_total', color='recharge_total',
                           color_continuous_scale=T['scale'], title='Treemap Chart · circle → plan')
            f.update_coloraxes(showscale=False)
            f.update_traces(marker_line_color=T['card'])
            show(style(f))
    # 10) CIRCLE TABLE
    with e:
        cf, r = scoped('tci', label='📋 Table · Circle performance')
        rv = summarize(cf, 'region').rename(columns={'region': 'Circle', 'subscribers': 'Subs', 'revenue': 'Revenue (₹)',
                                                    'arpu': 'Rev/sub/mo (₹)', 'no_pay_pct': 'No pay %'}).round(1)
        export['Circle data'] = rv
        st.dataframe(rv, hide_index=True, use_container_width=True, height=CH + 5)

with st.sidebar:
    st.markdown('### Export tables')
    for name, df in export.items():
        st.download_button(f'⬇ {name}', df.to_csv(index=False).encode(), f'airtel_{name.split()[0].lower()}.csv', 'text/csv')

st.caption('Figures are derived from recorded transactions in the connected SQLite dataset. Not a forecast, bill estimate or causal measure.')
