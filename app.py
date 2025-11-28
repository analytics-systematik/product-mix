import streamlit as st
import pandas as pd
import io

# --- 1. CONFIGURATION & BRANDING ---
st.set_page_config(
    page_title="Product Mix Analyzer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS: Fonts, Colors, and Clean UI
# Fonts: 'Outfit' (Geomanist alternative) for Headers, 'Source Sans Pro' for Body
hide_streamlit_style = """
<style>
    /* 1. Import Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Source+Sans+Pro:wght@400;600&family=Outfit:wght@400;700&display=swap');

    /* 2. Apply Source Sans Pro to the body/text */
    html, body, [class*="css"] {
        font-family: 'Source Sans Pro', sans-serif;
        color: #1A1A1A;
    }

    /* 3. Apply the Geometric Font (Outfit) to Headers */
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Outfit', sans-serif !important;
        font-weight: 700;
        color: #1A1A1A !important;
    }

    /* 4. Custom Styling for Lines/Dividers */
    hr {
        border-color: #1A1A1A !important;
        opacity: 1; /* Make sure it's solid */
        margin: 2em 0;
    }

    /* 5. Custom Button Styling (Systematik Purple Pill) */
    div.stButton > button:first-child {
        background-color: #7030A0;
        color: white;
        border-radius: 4px;
        border: none;
        padding: 0.5em 1em;
        font-weight: 600;
    }
    div.stButton > button:hover {
        background-color: #582480; /* Slightly darker purple on hover */
        color: white;
        border-color: #582480;
    }
    
    /* 6. Clean up UI (Hide Footer & Menu) */
    footer {visibility: hidden;}
    #MainMenu {visibility: hidden;}
    .stDeployButton {display:none;}
    
    /* 7. Adjust Expander Borders to be cleaner */
    .streamlit-expanderHeader {
        font-family: 'Source Sans Pro', sans-serif;
        font-weight: 600;
        color: #1A1A1A;
    }
</style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# Constants & Config
INCLUDE_PAYMENT_STATUSES = ['paid', 'partially_paid']

# Expanded Column Candidates
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

# --- 2. HELPER FUNCTIONS ---
def normalize_header(h):
    return str(h).lower().replace('_', ' ').replace('-', ' ').strip()

def find_column(df_cols, candidates):
    """Finds the first matching column name from candidates."""
    # 1. Exact match
    for c in candidates:
        if c in df_cols:
            return c
    # 2. Case-insensitive match
    lower_cols = {col.lower(): col for col in df_cols}
    for c in candidates:
        if c.lower() in lower_cols:
            return lower_cols[c.lower()]
    # 3. Fuzzy/Normalized match
    norm_cols = {normalize_header(col): col for col in df_cols}
    for cand in candidates:
        norm_cand = normalize_header(cand)
        for norm_col, original_col in norm_cols.items():
            if norm_cand == norm_col:
                return original_col
    return None

def parse_money(val):
    if pd.isna(val): return 0.0
    s = str(val).replace(',', '').replace('$', '').strip()
    if '(' in s and ')' in s:
        s = '-' + s.replace('(', '').replace(')', '')
    try:
        return float(s)
    except:
        return 0.0

# --- 3. SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Settings")
    
    # Identifier Mode
    st.subheader("1. Identifier Mode")
    id_mode = st.radio(
        "How to identify products:",
        ('SKU', 'Product + Variant', 'Product Name'),
        index=0,
        help="Determines how items are named in the mix (e.g. 'Red Shirt' vs 'Shirt')."
    )
    
    st.divider()
    
    # Ignore Rules
    st.subheader("2. Ignore Items")
    st.caption("Filters applied before calculating mixes (e.g., gift cards, freebies).")
    
    ignore_skus_input = st.text_area("Ignore SKUs (Exact match)", height=80, placeholder="GIFT-CARD-001")
    ignore_titles_input = st.text_area("Ignore Product Titles (Contains)", height=80, placeholder="Gift Card")
    ignore_vars_input = st.text_area("Ignore 'Product (Variant)' (Contains)", height=80, placeholder="T-Shirt (Sample)")

    # Process inputs
    ignore_skus = set(x.strip().upper() for x in ignore_skus_input.split('\n') if x.strip() and not x.strip().startswith('#'))
    ignore_titles = [x.strip().lower() for x in ignore_titles_input.split('\n') if x.strip() and not x.strip().startswith('#')]
    ignore_vars = [x.strip().lower() for x in ignore_vars_input.split('\n') if x.strip() and not x.strip().startswith('#')]

    st.divider()

    # Systematik Branding
    st.markdown("### ⚡ Powered by Systematik")
    st.info("Full-stack data agency for ecommerce brands earning $5M-100M annually.")
    st.markdown("""
    **Free Resources:**
    * [Automated GA4 Audit](https://systematikdata.com)
    * [Data Strategy Guide](https://systematikdata.com)
    * [Looker Studio Templates](https://systematikdata.com)
    
    Need a custom build?  
    📧 [info@systematikdata.com](mailto:info@systematikdata.com)
    """)

# --- 4. MAIN CONTENT ---
st.title("Product Mix Analyzer")
st.caption("Turn your raw order exports into clear bundle & cross-sell insights.")

# INSTRUCTIONS EXPANDER
with st.expander("📖 Instructions & Export Guide", expanded=False):
    st.markdown("""
    ### How it works
    1. **Upload Data:** Drag & drop your "Raw Orders" export below.
    2. **Clean & Filter:** The tool automatically removes canceled orders and applies your "Ignore Items" rules.
    3. **Analyze:** It generates two reports:
        * **Order Product Mix:** Distinct product combos across all orders.
        * **First Order Mix:** The product combo in the very first order of each customer.

    ### 🛠 Export Instructions (Platform Specific)
    """)
    
    tab_shopify, tab_bc, tab_woo = st.tabs(["Shopify", "BigCommerce", "WooCommerce"])
    
    with tab_shopify:
        st.markdown("""
        **Exporting from Shopify:**
        1. Go to **Analytics → Reports** (or Orders).
        2. Create a report with these columns: `Order id`, `Customer id` (or email), `Created at`, `Product title`, `Product variant title`, `Product variant sku`, `Order payment status`, `Is canceled order`, `Net sales`.
        3. **Crucial:** Ensure the report is "Flat" (one row per line item).
        4. Export as CSV.
        """)
        
    with tab_bc:
        st.markdown("""
        **Exporting from BigCommerce:**
        1. Go to **Orders → Export**.
        2. Use a template that includes: `Order ID`, `Date`, `Customer Email`, `SKU`, `Product Name`, `Variant Option`, `Payment Status`, `Order Status` (for cancellations), `Net Sales` (or Subtotal).
        3. Ensure it exports "Line Items" (one row per product).
        """)
        
    with tab_woo:
        st.markdown("""
        **Exporting from WooCommerce:**
        1. Use **Analytics → Orders → Export** (or a CSV plugin).
        2. Include: `order_id`, `date`, `customer_id` (or email), `line_item_sku`, `line_item_name`, `line_item_variation`, `status`, `net_total`.
        """)

    st.markdown("""
    ### ⚠️ Technical Notes
    * **Canceled Orders:** Lines where "Is canceled" is true/yes/1 are removed.
    * **Payment Status:** Only `paid` and `partially_paid` are included by default.
    * **Combos:** Quantities are ignored (buying 2x "Shirt" counts as just "Shirt").
    """)

# FILE UPLOADER
uploaded_file = st.file_uploader("Upload CSV File", type=['csv', 'xlsx'])

if uploaded_file:
    with st.spinner("Analyzing your data..."):
        try:
            # LOAD DATA
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)
            
            # COLUMN MAPPING
            col_map = {}
            for key, candidates in COL_CANDIDATES.items():
                found = find_column(df.columns, candidates)
                if found:
                    col_map[key] = found
            
            # CRITICAL CHECK
            if 'order_id' not in col_map:
                st.error("❌ Error: Could not detect an 'Order ID' column. Please check your headers.")
                st.stop()

            # RENAME & NORMALIZE
            df = df.rename(columns={v: k for k, v in col_map.items() if k in col_map})
            
            # 1. FILTER CANCELED
            if 'canceled' in df.columns:
                df['canceled_norm'] = df['canceled'].astype(str).str.lower()
                df = df[~df['canceled_norm'].isin(['true', 'yes', '1', 't', 'y'])]
            
            # 2. FILTER FINANCIAL STATUS
            if 'financial_status' in df.columns:
                df['financial_status'] = df['financial_status'].astype(str).str.lower()
                if INCLUDE_PAYMENT_STATUSES:
                    df = df[df['financial_status'].isin(INCLUDE_PAYMENT_STATUSES)]

            # 3. PREPARE DATA
            if 'net_sales' in df.columns:
                df['net_sales'] = df['net_sales'].apply(parse_money)
            else:
                df['net_sales'] = 0.0

            # 4. IGNORE LOGIC (Apply Filters)
            # SKU Filter
            if 'sku' in df.columns and ignore_skus:
                df = df[~df['sku'].astype(str).str.upper().isin(ignore_skus)]
            
            # Title Filter (Contains)
            if 'product_title' in df.columns and ignore_titles:
                for ignore_str in ignore_titles:
                    df = df[~df['product_title'].astype(str).str.lower().str.contains(ignore_str, na=False)]
            
            # Variant Combo Filter (Contains)
            if 'product_title' in df.columns:
                p_titles = df['product_title'].astype(str)
                v_titles = df['variant_title'].astype(str) if 'variant_title' in df.columns else pd.Series([""] * len(df))
                
                # Create composite "Product (Variant)" for checking
                combo_check = p_titles + " (" + v_titles + ")"
                
                if ignore_vars:
                    for ignore_str in ignore_vars:
                        # Check against composite string
                        mask = combo_check.str.lower().str.contains(ignore_str, na=False)
                        df = df[~mask]

            # 5. IDENTIFIER GENERATION
            def get_identifier(row):
                p = str(row.get('product_title', '')).strip()
                v = str(row.get('variant_title', '')).strip()
                s = str(row.get('sku', '')).strip()
                
                # Handle NaNs
                if p == 'nan': p = ''
                if v == 'nan': v = ''
                if s == 'nan': s = ''

                if id_mode == 'SKU':
                    return s if s else p
                elif id_mode == 'Product + Variant':
                    return f"{p} ({v})" if v else p
                else:
                    return p

            df['identifier'] = df.apply(get_identifier, axis=1)
            # Drop empty identifiers
            df = df[df['identifier'] != '']
            df = df[df['identifier'] != 'nan']

            # 6. AGGREGATION
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'], utc=True, errors='coerce')

            # Determine customer ID (ID > Email > Unknown)
            if 'customer_id' not in df.columns:
                df['customer_id'] = None
            if 'email' not in df.columns:
                df['email'] = None
                
            df['final_cust_id'] = df['customer_id'].fillna(df['email']).fillna('(unknown)')

            # Group by Order
            order_groups = df.groupby('order_id').agg({
                'identifier': lambda x: sorted(list(set(x))), # Unique items, sorted
                'net_sales': 'sum',
                'final_cust_id': 'first',
                'date': 'min'
            }).reset_index()

            # Create Combo String
            order_groups['product_mix'] = order_groups['identifier'].apply(lambda x: ' + '.join(x))
            order_groups = order_groups[order_groups['product_mix'] != '']

            # --- OUTPUT 1: ORDER PRODUCT MIX ---
            mix_df = order_groups.groupby('product_mix').agg({
                'order_id': 'count',
                'net_sales': 'sum'
            }).reset_index()
            
            mix_df.columns = ['product_mix', 'orders', 'net_sales']
            
            total_orders = mix_df['orders'].sum()
            total_net = mix_df['net_sales'].sum()
            
            mix_df['% of total'] = mix_df['orders'] / total_orders
            mix_df['% of net sales'] = mix_df['net_sales'] / total_net
            
            # Reorder columns to match instructions: mix, orders, %, net, % net
            mix_df = mix_df[['product_mix', 'orders', '% of total', 'net_sales', '% of net sales']]
            mix_df = mix_df.sort_values('orders', ascending=False)
            
            # --- OUTPUT 2: FIRST ORDER MIX ---
            # Sort by date, keep first per customer
            first_orders = order_groups.sort_values('date').drop_duplicates(subset=['final_cust_id'], keep='first')
            first_orders_out = first_orders[['final_cust_id', 'order_id', 'date', 'product_mix']].copy()
            first_orders_out.columns = ['customer_id', 'first_order_id', 'first_order_date', 'first_order_product_mix']

            # --- DISPLAY ---
            st.success(f"✅ Analysis Complete! Processed {total_orders} orders.")
            
            # Metrics
            c1, c2, c3 = st.columns(3)
            c1.metric("Unique Orders", total_orders)
            c2.metric("Unique Mixes", len(mix_df))
            c3.metric("Total Net Sales", f"${total_net:,.2f}")
            
            st.divider()

            tab1, tab2 = st.tabs(["📊 Order Product Mix", "👤 First Order Mix"])
            
            with tab1:
                st.dataframe(
                    mix_df.style.format({
                        '% of total': '{:.2%}', 
                        'net_sales': '${:,.2f}', 
                        '% of net sales': '{:.2%}'
                    }), 
                    use_container_width=True,
                    hide_index=True
                )
                st.download_button(
                    "Download Order Mix CSV",
                    mix_df.to_csv(index=False).encode('utf-8'),
                    "order_product_mix.csv",
                    "text/csv"
                )

            with tab2:
                st.dataframe(first_orders_out, use_container_width=True, hide_index=True)
                st.download_button(
                    "Download First Order Mix CSV",
                    first_orders_out.to_csv(index=False).encode('utf-8'),
                    "first_order_mix.csv",
                    "text/csv"
                )

        except Exception as e:
            st.error(f"Something went wrong: {e}")
            st.warning("Double-check that your export has the required columns (Order ID, Product Name, etc).")
