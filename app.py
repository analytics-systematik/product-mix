import streamlit as st
import pandas as pd
import io

# ==========================================
# TEXT CONFIGURATION
# ==========================================
APP_CONFIG = {
    "title": "Product Mix Analyzer",
    
    # Exciting, benefit-driven description
    "subtitle": """
    Discover hidden revenue opportunities in your order data. 
    Instantly see which products your customers actually buy together and identify the exact items that hook new customers on their first purchase.
    """,
    
    "privacy_notice": "**Your data is safe. The analysis runs entirely in this secure session — we never see, store, or save your files.**",
    
    # Sidebar Text
    "sidebar_header": "Settings",
    "id_mode_label": "How to identify products:",
    "id_mode_help": "Determines how items are named in the mix (e.g. 'Red Shirt' vs 'Shirt').",
    
    "ignore_header": "2. Ignore Items",
    "ignore_caption": "Filters applied before calculating mixes (e.g., gift cards, freebies).",
    
    # Branding
    "brand_header": "Powered by Systematik",
    "brand_info": "Full-stack data agency for ecommerce brands earning $5M-100M annually.",
    "brand_email": "info@systematikdata.com",
    
    # Instructions
    "instructions_title": "Instructions & Video Tutorial",
    "video_link": "https://www.youtube.com", # Update this link later
    "video_text": "Watch the video walkthrough",
    
    "instructions_intro": """
    **How it works**
    1. Upload your "Raw Orders" export below.
    2. The tool automatically cleans the data (removes canceled orders, applies filters).
    3. You get two instant reports:
        * **Order Product Mix:** The most popular product combinations.
        * **First Order Mix:** What customers buy in their very first order.
    """,
    
    "success_msg": "Analysis Complete. Processed {n} orders.",
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

# Custom CSS: Fonts, Colors, and Clean UI
hide_streamlit_style = """
<style>
    /* Import Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Source+Sans+Pro:wght@400;600&family=Outfit:wght@400;700&display=swap');
    
    /* Body Styling */
    html, body, [class*="css"] { 
        font-family: 'Source Sans Pro', sans-serif; 
        color: #1A1A1A; 
        background-color: #F3F3F3; /* Ensure fallback color matches */
    }
    
    /* Headers (Outfit font) */
    h1, h2, h3, h4, h5, h6 { 
        font-family: 'Outfit', sans-serif !important; 
        font-weight: 700; 
        color: #1A1A1A !important; 
    }
    
    /* Custom Lines/Dividers */
    hr { 
        border-color: #1A1A1A !important; 
        opacity: 1; 
        margin: 2em 0; 
    }
    
    /* Button Styling (Purple Pill) */
    div.stButton > button:first-child { 
        background-color: #7030A0; 
        color: white; 
        border-radius: 4px; 
        border: none; 
        padding: 0.5em 1em; 
        font-weight: 600; 
    }
    div.stButton > button:hover { 
        background-color: #582480; 
        color: white; 
        border-color: #582480; 
    }
    
    /* Hide Streamlit Branding */
    footer {visibility: hidden;}
    #MainMenu {visibility: hidden;}
    .stDeployButton {display:none;}
    
    /* Clean up Expander */
    .streamlit-expanderHeader { 
        font-family: 'Source Sans Pro', sans-serif; 
        font-weight: 600; 
        color: #1A1A1A; 
        background-color: #F3F3F3;
    }
    
    /* Upload Box Styling - Transparent/Gray to match background */
    [data-testid="stFileUploader"] {
        border: 1px dashed #7030A0;
        padding: 10px;
        border-radius: 5px;
        background-color: #F3F3F3; /* Matches main background */
    }
    
    /* Sidebar specific tweaks */
    [data-testid="stSidebar"] {
        background-color: #F3F3F3;
        border-right: 1px solid #E0E0E0; /* Subtle separator line */
    }
</style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

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
    
    st.subheader("1. Identifier Mode")
    id_mode = st.radio(
        APP_CONFIG["id_mode_label"],
        ('SKU', 'Product + Variant', 'Product Name'),
        index=0,
        help=APP_CONFIG["id_mode_help"]
    )
    
    st.divider()
    
    st.subheader(APP_CONFIG["ignore_header"])
    st.caption(APP_CONFIG["ignore_caption"])
    
    ignore_skus_input = st.text_area("Ignore SKUs (Exact match)", height=80, placeholder="GIFT-CARD-001")
    ignore_titles_input = st.text_area("Ignore Product Titles (Contains)", height=80, placeholder="Gift Card")
    ignore_vars_input = st.text_area("Ignore 'Product (Variant)' (Contains)", height=80, placeholder="T-Shirt (Sample)")

    ignore_skus = set(x.strip().upper() for x in ignore_skus_input.split('\n') if x.strip() and not x.strip().startswith('#'))
    ignore_titles = [x.strip().lower() for x in ignore_titles_input.split('\n') if x.strip() and not x.strip().startswith('#')]
    ignore_vars = [x.strip().lower() for x in ignore_vars_input.split('\n') if x.strip() and not x.strip().startswith('#')]

    st.divider()

    # Systematik Branding (Purple)
    st.markdown(f"""
    <div style="color: #7030A0;">
        <h3>{APP_CONFIG['brand_header']}</h3>
        <p><strong>{APP_CONFIG['brand_info']}</strong></p>
        <p><strong>Free Resources:</strong></p>
        <ul>
            <li><a href="https://systematikdata.com" style="color: #7030A0;">Automated GA4 Audit</a></li>
            <li><a href="https://systematikdata.com" style="color: #7030A0;">Data Strategy Guide</a></li>
            <li><a href="https://systematikdata.com" style="color: #7030A0;">Looker Studio Templates</a></li>
        </ul>
        <p>Need a custom build?<br>
        <a href="mailto:{APP_CONFIG['brand_email']}" style="color: #7030A0;">{APP_CONFIG['brand_email']}</a></p>
    </div>
    """, unsafe_allow_html=True)

# --- MAIN PAGE ---
st.title(APP_CONFIG["title"])
st.markdown(APP_CONFIG["subtitle"])
st.markdown(APP_CONFIG["privacy_notice"])

# Instructions Expander
with st.expander(APP_CONFIG["instructions_title"], expanded=False):
    # Video Link
    st.markdown(f"**🎥 [{APP_CONFIG['video_text']}]({APP_CONFIG['video_link']})**")
    st.markdown("---")
    st.markdown(APP_CONFIG["instructions_intro"])
    
    tab_shopify, tab_bc, tab_woo = st.tabs(["Shopify", "BigCommerce", "WooCommerce"])
    with tab_shopify:
        st.markdown("**Exporting from Shopify:** Go to Analytics → Reports. Export a 'Flat' CSV with Order ID, Product Title, SKU, etc.")
    with tab_bc:
        st.markdown("**Exporting from BigCommerce:** Go to Orders → Export. Use a template with Line Items (SKU, Product Name).")
    with tab_woo:
        st.markdown("**Exporting from WooCommerce:** Use Analytics → Orders → Export with line_item fields.")

    st.markdown("### Technical Notes\n* Canceled orders are removed.\n* Only `paid`/`partially_paid` included.\n* Quantities are ignored in mix.")

st.divider()

# Upload Section (Styled to be obvious)
st.subheader("Upload Order Export")
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
            c1.metric("Unique Orders", total_orders)
            c2.metric("Unique Mixes", len(mix_df))
            c3.metric("Total Net Sales", f"${total_net:,.2f}")
            st.divider()

            tab1, tab2 = st.tabs(["Order Product Mix", "First Order Mix"])
            with tab1:
                st.dataframe(mix_df.style.format({'% of total': '{:.2%}', 'net_sales': '${:,.2f}', '% of net sales': '{:.2%}'}), use_container_width=True, hide_index=True)
                st.download_button("Download CSV", mix_df.to_csv(index=False).encode('utf-8'), "order_mix.csv", "text/csv")
            with tab2:
                st.dataframe(first_orders_out, use_container_width=True, hide_index=True)
                st.download_button("Download CSV", first_orders_out.to_csv(index=False).encode('utf-8'), "first_order_mix.csv", "text/csv")

        except Exception as e:
            st.error(f"Something went wrong: {e}")
