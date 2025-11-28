import streamlit as st
import pandas as pd
import io

# ==========================================
# TEXT CONFIGURATION
# ==========================================
APP_CONFIG = {
    "title": "Product Mix Analyzer",
    
    "subtitle": """
    <p style="font-size: 20px; line-height: 1.5; color: #1A1A1A; margin-bottom: 20px;">
    Discover hidden revenue opportunities in your order data. 
    Instantly see which products your customers actually buy together and identify the exact items that hook new customers on their first purchase.
    </p>
    """,
    
    "privacy_notice": "🔒 **Your data is safe. The analysis runs entirely in this secure session — we never see, store, or save your files.**",
    
    # Sidebar Text
    "sidebar_header": "Settings",
    "id_mode_label": "How to identify products:",
    "id_mode_help": "Determines how items are named in the mix (e.g. 'Red Shirt' vs 'Shirt').",
    
    "ignore_header": "2. Ignore items",
    "ignore_caption": "Filters applied before calculating mixes (e.g., gift cards, freebies).",
    
    # Branding
    "brand_header": "Powered by Systematik",
    "brand_info": "Full-stack data agency for ecommerce brands earning $5M-100M annually.",
    "brand_email": "info@systematikdata.com",
    
    # Instructions
    "instructions_title": "Instructions & video tutorial",
    "video_link": "https://www.youtube.com", 
    "video_text": "Watch the video walkthrough",
    
    "instructions_intro": """
    **How it works**
    1. Upload your "Raw Orders" export below.
    2. The tool automatically cleans the data (removes canceled orders, applies filters).
    3. You get two instant reports:
        * **Order product mix:** The most popular product combinations.
        * **First order mix:** What customers buy in their very first order.
    """,
    
    "success_msg": "Analysis complete. Processed {n} orders.",
    "error_msg": "Error: Could not detect an 'Order ID' column. Please check your headers."
}

# ==========================================
# APP LOGIC
# ==========================================

st.set_page_config(
    page_title=APP_CONFIG["title"],
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- LOAD EXTERNAL CSS ---
def local_css(file_name):
    with open(file_name) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

try:
    local_css("style.css")
except FileNotFoundError:
    st.error("Error: style.css file not found. Please ensure it is in the repository.")

# Constants
INCLUDE_PAYMENT_STATUSES = ['paid', 'partially_paid']
COL_CANDIDATES = {
    'order_id': ['order id', 'name', 'order', 'order number', 'order_id'],
    'customer_id': ['customer id', 'customer_id', 'customer'],
    'email': ['customer email', 'email', 'customer_email', 'billing_email'],
    'date': ['created at', 'created_at', 'processed at', 'order date', 'day', 'date', 'hour', 'time'],
    'product_title': ['product title', 'lineitem name', 'title', 'product name', 'line_item_name'],
    'variant_title': ['product variant title', 'variant title', 'variant', 'lineitem variant', 'line_item_variation', 'option'],
    'sku': ['product variant sku', 'variant sku', 'sku', 'lineitem sku', 'line_item_sku'],
    'net_sales': ['net sales', 'total sales', 'total price', 'net_total', 'net revenue'],
    'financial_status': ['order payment status', 'financial status', 'payment status', 'order_status'],
    'canceled': ['is canceled order', 'cancelled', 'canceled', 'is_canceled', 'is_cancelled']
}

# Helper Functions
def normalize_header(h):
    return str(h).lower().replace('_', ' ').replace('-', ' ').strip()

def find_column(df_cols, candidates):
    for c in candidates:
        if c in df_cols: return c
    lower_cols = {col.lower(): col for col in df_cols}
    for c in candidates:
        if c.lower() in lower_cols: return lower_cols[c.lower()]
    norm_cols = {normalize_header(col): col for col in df_cols}
    for cand in candidates:
        norm_cand = normalize_header(cand)
        for norm_col, original_col in norm_cols.items():
            if norm_cand == norm_col: return original_col
    return None

def parse_money(val):
    if pd.isna(val): return 0.0
    s = str(val).replace(',', '').replace('$', '').strip()
    if '(' in s and ')' in s: s = '-' + s.replace('(', '').replace(')', '')
    try: return float(s)
    except: return 0.0

# --- SIDEBAR ---
with st.sidebar:
    st.header(APP_CONFIG["sidebar_header"])
    
    st.subheader("1. Identifier mode")
    id_mode = st.radio(
        APP_CONFIG["id_mode_label"],
        ('SKU', 'Product + Variant', 'Product Name'),
        index=0,
        help=APP_CONFIG["id_mode_help"]
    )
    
    st.divider()
    
    st.subheader(APP_CONFIG["ignore_header"])
    st.caption(APP_CONFIG["ignore_caption"])
    
    ignore_skus_input = st.text_area("Ignore SKUs (exact match)", height=80, placeholder="GIFT-CARD-001")
    ignore_titles_input = st.text_area("Ignore product titles (contains)", height=80, placeholder="Gift Card")
    ignore_vars_input = st.text_area("Ignore 'Product (Variant)' (contains)", height=80, placeholder="T-Shirt (Sample)")

    ignore_skus = set(x.strip().upper() for x in ignore_skus_input.split('\n') if x.strip() and not x.strip().startswith('#'))
    ignore_titles = [x.strip().lower() for x in ignore_titles_input.split('\n') if x.strip() and not x.strip().startswith('#')]
    ignore_vars = [x.strip().lower() for x in ignore_vars_input.split('\n') if x.strip() and not x.strip().startswith('#')]

    st.divider()

    # Systematik Branding
    st.markdown(f"""
    <div>
        <h3 style="color: #7030A0; font-family: 'Outfit', sans-serif;">{APP_CONFIG['brand_header']}</h3>
        
        <div style="background-color: #F2E6FF; padding: 12px; border-radius: 6px; margin-bottom: 15px; border-left: 3px solid #7030A0;">
            <p style="margin: 0; color: #1A1A1A; font-weight: 600;">{APP_CONFIG['brand_info']}</p>
        </div>
        
        <p style="margin-bottom: 5px; color: #1A1A1A; font-weight: 700;">Free resources:</p>
        <ul style="margin-top: 0;">
            <li><a href="https://systematikdata.com">Automated GA4 Audit</a></li>
            <li><a href="https://systematikdata.com">Data Strategy Guide</a></li>
            <li><a href="https://systematikdata.com">Looker Studio Templates</a></li>
        </ul>
        
        <p style="margin-bottom: 5px; color: #1A1A1A; font-weight: 700;">Need a custom build?</p>
        <a href="mailto:{APP_CONFIG['brand_email']}">{APP_CONFIG['brand_email']}</a>
    </div>
    """, unsafe_allow_html=True)

# --- MAIN PAGE ---
st.title(APP_CONFIG["title"])

# Render subtitle with HTML enabled
st.markdown(APP_CONFIG["subtitle"], unsafe_allow_html=True)

st.markdown(APP_CONFIG["privacy_notice"])

# Instructions Expander
with st.expander(APP_CONFIG["instructions_title"], expanded=False):
    # Video Link
    st.markdown(f"""
    <a href="{APP_CONFIG['video_link']}" style="font-weight: bold; font-size: 1.1em;">
        🎥 {APP_CONFIG['video_text']}
    </a>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown(APP_CONFIG["instructions_intro"])
    
    # Platform Specific Instructions
    tab_shopify, tab_bc, tab_woo = st.tabs(["Shopify", "BigCommerce", "WooCommerce"])
    
    with tab_shopify:
        st.markdown("""
        **Exporting from Shopify (Line Items):**
        1. Go to **Analytics → Reports**.
        2. Create a report. Ensure fields include: `Order id`, `Customer id` (or email), `Created at`, `Product title`, `Product variant title`, `Product variant sku`, `Order payment status`, `Is canceled order`, and `Net sales`.
        3. Export as a **CSV**. 
        4. **Crucial:** Make sure the displayed table in Shopify is set to "Flat" (one row per line item).
        """)
        
    with tab_bc:
        st.markdown("""
        **Exporting from BigCommerce:**
        1. Go to **Orders → Export** (or Advanced Reporting).
        2. Export a line-item level CSV or use a template.
        3. Ensure it includes: `Order ID`, `Date/Time`, `Customer ID` (or Email), `SKU`, `Product Name`, `Option/Variant`, `Payment Status`, `Canceled/Refunded`, `Net Sales` (or line net).
        """)
        
    with tab_woo:
        st.markdown("""
        **Exporting from WooCommerce:**
        1. Use **Analytics → Orders → Export** (or a CSV export plugin).
        2. Ensure the export produces **one row per line item**.
        3. Include fields mapping to: `order_id`, `date`, `customer_id` (or email), `line_item_sku`, `line_item_name`, `line_item_variation`, `status`, `is_canceled`, `net_total`.
        """)

    st.markdown("### Technical notes\n* Canceled orders are removed.\n* Only `paid`/`partially_paid` included.\n* Quantities are ignored in mix.")

st.divider()

# Upload Section
st.subheader("Upload order export")
uploaded_file = st.file_uploader("Drag & drop CSV or Excel file here", type=['csv', 'xlsx'], label_visibility="collapsed")

if uploaded_file:
    with st.spinner("Analyzing data..."):
        try:
            if uploaded_file.name.endswith('.csv'): df = pd.read_csv(uploaded_file)
            else: df = pd.read_excel(uploaded_file)
            
            col_map = {}
            for key, candidates in COL_CANDIDATES.items():
                found = find_column(df.columns, candidates)
                if found: col_map[key] = found
            
            if 'order_id' not in col_map:
                st.error(APP_CONFIG["error_msg"])
                st.stop()

            df = df.rename(columns={v: k for k, v in col_map.items() if k in col_map})
            
            if 'canceled' in df.columns:
                df['canceled_norm'] = df['canceled'].astype(str).str.lower()
                df = df[~df['canceled_norm'].isin(['true', 'yes', '1', 't', 'y'])]
            
            if 'financial_status' in df.columns:
                df['financial_status'] = df['financial_status'].astype(str).str.lower()
                if INCLUDE_PAYMENT_STATUSES:
                    df = df[df['financial_status'].isin(INCLUDE_PAYMENT_STATUSES)]

            if 'net_sales' in df.columns: df['net_sales'] = df['net_sales'].apply(parse_money)
            else: df['net_sales'] = 0.0

            if 'sku' in df.columns and ignore_skus:
                df = df[~df['sku'].astype(str).str.upper().isin(ignore_skus)]
            if 'product_title' in df.columns and ignore_titles:
                for ignore_str in ignore_titles:
                    df = df[~df['product_title'].astype(str).str.lower().str.contains(ignore_str, na=False)]
            if 'product_title' in df.columns and ignore_vars:
                p_titles = df['product_title'].astype(str)
                v_titles = df['variant_title'].astype(str) if 'variant_title' in df.columns else pd.Series([""] * len(df))
                combo_check = p_titles + " (" + v_titles + ")"
                for ignore_str in ignore_vars:
                    df = df[~combo_check.str.lower().str.contains(ignore_str, na=False)]

            def get_identifier(row):
                p = str(row.get('product_title', '')).strip()
                v = str(row.get('variant_title', '')).strip()
                s = str(row.get('sku', '')).strip()
                if p == 'nan': p = ''
                if v == 'nan': v = ''
                if s == 'nan': s = ''
                if id_mode == 'SKU': return s if s else p
                elif id_mode == 'Product + Variant': return f"{p} ({v})" if v else p
                else: return p

            df['identifier'] = df.apply(get_identifier, axis=1)
            df = df[(df['identifier'] != '') & (df['identifier'] != 'nan')]

            if 'date' in df.columns: df['date'] = pd.to_datetime(df['date'], utc=True, errors='coerce')
            if 'customer_id' not in df.columns: df['customer_id'] = None
            if 'email' not in df.columns: df['email'] = None
            df['final_cust_id'] = df['customer_id'].fillna(df['email']).fillna('(unknown)')

            order_groups = df.groupby('order_id').agg({
                'identifier': lambda x: sorted(list(set(x))),
                'net_sales': 'sum',
                'final_cust_id': 'first',
                'date': 'min'
            }).reset_index()

            order_groups['product_mix'] = order_groups['identifier'].apply(lambda x: ' + '.join(x))
            order_groups = order_groups[order_groups['product_mix'] != '']

            mix_df = order_groups.groupby('product_mix').agg({'order_id': 'count', 'net_sales': 'sum'}).reset_index()
            mix_df.columns = ['product_mix', 'orders', 'net_sales']
            
            total_orders = mix_df['orders'].sum()
            total_net = mix_df['net_sales'].sum()
            
            mix_df['% of total'] = mix_df['orders'] / total_orders
            mix_df['% of net sales'] = mix_df['net_sales'] / total_net
            mix_df = mix_df[['product_mix', 'orders', '% of total', 'net_sales', '% of net sales']]
            mix_df = mix_df.sort_values('orders', ascending=False)
            
            first_orders = order_groups.sort_values('date').drop_duplicates(subset=['final_cust_id'], keep='first')
            first_orders_out = first_orders[['final_cust_id', 'order_id', 'date', 'product_mix']].copy()
            first_orders_out.columns = ['customer_id', 'first_order_id', 'first_order_date', 'first_order_product_mix']

            st.success(APP_CONFIG["success_msg"].format(n=total_orders))
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Unique orders", total_orders)
            c2.metric("Unique mixes", len(mix_df))
            c3.metric("Total net sales", f"${total_net:,.2f}")
            st.divider()

            tab1, tab2 = st.tabs(["Order product mix", "First order mix"])
            with tab1:
                st.dataframe(mix_df.style.format({'% of total': '{:.2%}', 'net_sales': '${:,.2f}', '% of net sales': '{:.2%}'}), use_container_width=True, hide_index=True)
                st.download_button("Download CSV", mix_df.to_csv(index=False).encode('utf-8'), "order_mix.csv", "text/csv")
            with tab2:
                st.dataframe(first_orders_out, use_container_width=True, hide_index=True)
                st.download_button("Download CSV", first_orders_out.to_csv(index=False).encode('utf-8'), "first_order_mix.csv", "text/csv")

        except Exception as e:
            st.error(f"Something went wrong: {e}")
