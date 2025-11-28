import streamlit as st
import pandas as pd
import io

# --- 1. CONFIGURATION & SETUP ---
st.set_page_config(page_title="Shopify Product Mix Analyzer", layout="wide")

# Constants matching your GAS config
INCLUDE_PAYMENT_STATUSES = ['paid', 'partially_paid']
COL_CANDIDATES = {
    'order_id': ['order id', 'name', 'order', 'order number', 'order_id'],
    'customer_id': ['customer id', 'customer_id', 'customer', 'email'], # Added email as fallback in logic
    'date': ['created at', 'created_at', 'processed at', 'order date', 'day', 'date'],
    'product_title': ['product title', 'lineitem name', 'title', 'product name'],
    'variant_title': ['variant title', 'variant', 'lineitem variant'],
    'sku': ['product variant sku', 'variant sku', 'sku', 'lineitem sku'],
    'net_sales': ['net sales', 'total sales', 'total price'],
    'financial_status': ['financial status', 'payment status'],
    'canceled': ['cancelled', 'canceled', 'is canceled']
}

# --- 2. HELPER FUNCTIONS ---
def normalize_header(h):
    return str(h).lower().replace('_', ' ').strip()

def find_column(df_cols, candidates):
    """Finds the first matching column name from candidates."""
    # Exact match first
    for c in candidates:
        if c in df_cols:
            return c
    # Fuzzy match
    norm_cols = {col: normalize_header(col) for col in df_cols}
    for cand in candidates:
        for col, norm in norm_cols.items():
            if cand in norm:
                return col
    return None

def parse_money(val):
    """Cleans currency strings to floats."""
    if pd.isna(val): return 0.0
    s = str(val).replace(',', '').replace('$', '').strip()
    if '(' in s and ')' in s:
        s = '-' + s.replace('(', '').replace(')', '')
    try:
        return float(s)
    except:
        return 0.0

# --- 3. UI & INPUTS ---
st.title("🛍️ Shopify Product Mix Analyzer")
st.markdown("""
Upload your Shopify Order Export (CSV) to analyze which products are frequently bought together.
**Data stays in your browser session and is not stored.**
""")

# Sidebar: Settings
with st.sidebar:
    st.header("Settings")
    
    # Identifier Mode
    id_mode = st.radio(
        "Identifier Mode",
        ('SKU', 'Product + Variant', 'Product Name'),
        index=0
    )
    
    st.divider()
    
    # Ignore Rules (Replicating ignore_items.js)
    st.subheader("Ignore Items")
    ignore_skus_input = st.text_area("Ignore SKUs (one per line)", height=100, help="Exact match, case-insensitive")
    ignore_titles_input = st.text_area("Ignore Titles (contains)", height=100, help="Partial match on Product Title")
    
    ignore_skus = set(x.strip().upper() for x in ignore_skus_input.split('\n') if x.strip() and not x.strip().startswith('#'))
    ignore_titles = [x.strip().lower() for x in ignore_titles_input.split('\n') if x.strip() and not x.strip().startswith('#')]

# Main File Uploader
uploaded_file = st.file_uploader("Upload 'Raw Orders' CSV", type=['csv', 'xlsx'])

if uploaded_file:
    with st.spinner("Processing data..."):
        try:
            # Load Data
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)
            
            # --- 4. DATA PREPARATION ---
            # Map columns
            col_map = {}
            missing_cols = []
            for key, candidates in COL_CANDIDATES.items():
                found = find_column(df.columns, candidates)
                if found:
                    col_map[key] = found
                elif key not in ['variant_title', 'sku', 'canceled', 'financial_status']: 
                    # specific optional cols dont trigger critical error
                    missing_cols.append(key)

            if 'order_id' not in col_map:
                st.error("Could not find 'Order ID' column. Please check your CSV.")
                st.stop()

            # Rename columns for internal use
            df = df.rename(columns={v: k for k, v in col_map.items() if k in col_map})
            
            # --- 5. FILTERING ---
            # Filter Canceled
            if 'canceled' in df.columns:
                # Check for truthy values (yes, true, 1)
                df['canceled_norm'] = df['canceled'].astype(str).str.lower()
                df = df[~df['canceled_norm'].isin(['true', 'yes', '1', 't'])]
            
            # Filter Financial Status
            if 'financial_status' in df.columns:
                df['financial_status'] = df['financial_status'].astype(str).str.lower()
                if INCLUDE_PAYMENT_STATUSES:
                    df = df[df['financial_status'].isin(INCLUDE_PAYMENT_STATUSES)]

            # Clean Money
            if 'net_sales' in df.columns:
                df['net_sales'] = df['net_sales'].apply(parse_money)
            else:
                df['net_sales'] = 0.0

            # --- 6. IGNORE LOGIC ---
            # SKU Ignore
            if 'sku' in df.columns and ignore_skus:
                df = df[~df['sku'].astype(str).str.upper().isin(ignore_skus)]
            
            # Title Ignore (Contains)
            if 'product_title' in df.columns and ignore_titles:
                for ignore_str in ignore_titles:
                    df = df[~df['product_title'].astype(str).str.lower().str.contains(ignore_str, na=False)]

            # --- 7. IDENTIFIER GENERATION ---
            # Create the 'Item Name' based on user selection
            def get_identifier(row):
                p = str(row.get('product_title', ''))
                v = str(row.get('variant_title', '')) if 'variant_title' in df.columns else ''
                s = str(row.get('sku', '')) if 'sku' in df.columns else ''
                
                if id_mode == 'SKU':
                    return s if s and s.lower() != 'nan' else p
                elif id_mode == 'Product + Variant':
                    return f"{p} ({v})" if v and v.lower() != 'nan' else p
                else:
                    return p

            df['identifier'] = df.apply(get_identifier, axis=1)
            # Remove rows where identifier is empty or NaN
            df = df[df['identifier'].str.strip() != '']
            df = df[df['identifier'] != 'nan']

            # --- 8. AGGREGATION (Core Logic) ---
            
            # Group by Order ID to get Mixes
            # We aggregate: Combine identifiers into a list, Sum net sales, Take first date/customer
            
            # Ensure date format
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'], utc=True, errors='coerce')

            order_groups = df.groupby('order_id').agg({
                'identifier': lambda x: sorted(list(set(x))), # Unique items, sorted
                'net_sales': 'sum',
                'customer_id': 'first', # Or email fallback
                'date': 'min'
            }).reset_index()

            # Create the "Combo" string (e.g. "A + B")
            order_groups['combo_string'] = order_groups['identifier'].apply(lambda x: ' + '.join(x))
            
            # Filter out empty combos
            order_groups = order_groups[order_groups['combo_string'] != '']

            # --- 9. OUTPUT 1: PRODUCT MIX ---
            mix_df = order_groups.groupby('combo_string').agg({
                'order_id': 'count',
                'net_sales': 'sum'
            }).reset_index()
            
            mix_df.columns = ['Product Mix', 'Orders', 'Net Sales']
            
            total_orders = mix_df['Orders'].sum()
            total_net = mix_df['Net Sales'].sum()
            
            mix_df['% of Total'] = mix_df['Orders'] / total_orders
            mix_df['% of Net Sales'] = mix_df['Net Sales'] / total_net
            
            # Formatting
            mix_df = mix_df.sort_values('Orders', ascending=False)
            
            # --- 10. OUTPUT 2: FIRST ORDER MIX ---
            # Sort by date, drop duplicates keeping first
            first_orders = order_groups.sort_values('date').drop_duplicates(subset=['customer_id'], keep='first')
            first_orders_out = first_orders[['customer_id', 'order_id', 'date', 'combo_string']].copy()
            first_orders_out.columns = ['Customer ID', 'First Order ID', 'First Order Date', 'First Order Product Mix']
            
            # --- 11. DISPLAY RESULTS ---
            
            st.success(f"Analysis Complete! Analyzed {total_orders} unique orders.")
            
            tab1, tab2 = st.tabs(["📊 Order Product Mix", "👤 First Order Mix"])
            
            with tab1:
                st.dataframe(
                    mix_df.style.format({
                        '% of Total': '{:.2%}', 
                        'Net Sales': '${:,.2f}', 
                        '% of Net Sales': '{:.2%}'
                    }), 
                    use_container_width=True
                )
                
                # CSV Download
                csv_mix = mix_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    "Download Product Mix CSV",
                    csv_mix,
                    "product_mix.csv",
                    "text/csv",
                    key='download-mix'
                )

            with tab2:
                st.dataframe(first_orders_out, use_container_width=True)
                
                csv_first = first_orders_out.to_csv(index=False).encode('utf-8')
                st.download_button(
                    "Download First Order Mix CSV",
                    csv_first,
                    "first_order_mix.csv",
                    "text/csv",
                    key='download-first'
                )

        except Exception as e:
            st.error(f"An error occurred: {e}")
            st.warning("Please check that your CSV file has the required columns (Order ID, Line Item, etc).")