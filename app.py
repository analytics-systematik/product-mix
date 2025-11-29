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
    
    "qty_mode_label": "Differentiate by quantity",
    "qty_mode_help": "If checked, buying 2 items counts as a different mix than buying 1 item. Uncheck to treat them the same.",
    
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
    'quantity': ['lineitem quantity', 'quantity', 'qty', 'count'],
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

# --- EXCEL GENERATOR ---
def convert_to_excel(df, report_type):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Write df starting at Row 4
        df.to_excel(writer, index=False, startrow=3, sheet_name='Report')
        
        workbook = writer.book
        worksheet = writer.sheets['Report']
        
        from openpyxl.styles import Font, Alignment
        
        bold_font = Font(bold=True, name='Arial', size=11)
        regular_font = Font(name='Arial', size=10)
        purple_link_font = Font(name='Arial', size=10, color="7030A0", underline="single")
        header_font = Font(bold=True, name='Arial', size=14)
        text_align = Alignment(wrap_text=True, vertical='top')
        
        def write_side_block(row, title, text, link=None):
            cell_title = worksheet[f'H{row}']
            cell_title.value = title
            cell_title.font = bold_font
            
            cell_text = worksheet[f'H{row+1}']
            cell_text.value = text
            cell_text.font = regular_font if not link else purple_link_font
            cell_text.alignment = text_align
            if link: cell_text.hyperlink = link

        worksheet['H3'] = "SYSTEMATIK DATA — PRODUCT MIX REPORT"
        worksheet['H3'].font = header_font
        worksheet['H4'] = f"Report: {report_type} | Date: {pd.Timestamp.now().strftime('%Y-%m-%d')}"
        worksheet['H4'].font = regular_font

        write_side_block(6, "1. WHAT THIS REPORT SHOWS", 
                         "This table groups your historical orders to reveal unique product combinations.")
        write_side_block(10, "2. ACTIONABLE STRATEGIES", 
                         "• Create 'Power Bundles'\n• Smart Email Flows\n• Inventory Planning")
        write_side_block(16, "3. GO DEEPER (ADVANCED ANALYTICS)", 
                         "Calculate LTV by First Order Mix to find your best customers.")
        write_side_block(20, "4. TIRED OF MANUAL EXPORTS?", 
                         "We can build you a live, automated dashboard that refreshes this data daily.")
        write_side_block(23, "⚡ POWERED BY SYSTEMATIK", 
                         "Full-stack data agency for ecommerce brands ($5M-$100M).")
        write_side_block(25, "Book a strategy call", "info@systematikdata.com", link="mailto:info@systematikdata.com")
        write_side_block(26, "Visit our website", "systematikdata.com", link="https://systematikdata.com")

        worksheet.column_dimensions['H'].width = 60
        worksheet.column_dimensions['F'].width = 5
        worksheet.column_dimensions['G'].width = 5
        for col in ['A', 'B', 'C', 'D', 'E']: worksheet.column_dimensions[col].width = 20

    return output.getvalue()

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
    
    use_quantity = st.checkbox(
        APP_CONFIG["qty_mode_label"],
        value=False,
        help=APP_CONFIG["qty_mode_help"]
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

    st.markdown(f"""
<div>
<h3 style="color: #7030A0; font-family: 'Outfit', sans-serif;">{APP_CONFIG['brand_header']}</h3>
<div style="background-color: #F2E6FF; padding: 12px; border-radius: 6px; margin-bottom: 15px;">
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
st.markdown(APP_CONFIG["subtitle"], unsafe_allow_html=True)
st.markdown(APP_CONFIG["privacy_notice"])

with st.expander(APP_CONFIG["instructions_title"], expanded=False):
    st.markdown(f"""<a href="{APP_CONFIG['video_link']}" style="font-weight: bold; font-size: 1.1em;">🎥 {APP_CONFIG['video_text']}</a>""", unsafe_allow_html=True)
    st.markdown("---")
    st.markdown(APP_CONFIG["instructions_intro"])
    
    tab_shopify, tab_bc, tab_woo = st.tabs(["Shopify", "BigCommerce", "WooCommerce"])
    with tab_shopify:
        st.markdown("**Exporting from Shopify:** Analytics -> Reports. 'Flat' CSV with Order ID, Line Items.")
    with tab_bc:
        st.markdown("**Exporting from BigCommerce:** Orders -> Export. Template with Line Items.")
    with tab_woo:
        st.markdown("**Exporting from WooCommerce:** Analytics -> Orders -> Export with line_item fields.")
    st.markdown("### Technical notes\n* Canceled orders are removed.\n* Only `paid`/`partially_paid` included.\n* Quantities are ignored unless enabled in sidebar.")

st.divider()
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
                if INCLUDE_PAYMENT_STATUSES: df = df[df['financial_status'].isin(INCLUDE_PAYMENT_STATUSES)]

            if 'net_sales' in df.columns: df['net_sales'] = df['net_sales'].apply(parse_money)
            else: df['net_sales'] = 0.0
            
            if 'quantity' in df.columns: 
                df['quantity'] = pd.to_numeric(df['quantity'], errors='coerce').fillna(1).astype(int)
            else: df['quantity'] = 1

            if 'sku' in df.columns and ignore_skus: df = df[~df['sku'].astype(str).str.upper().isin(ignore_skus)]
            if 'product_title' in df.columns and ignore_titles:
                for ignore_str in ignore_titles: df = df[~df['product_title'].astype(str).str.lower().str.contains(ignore_str, na=False)]
            if 'product_title' in df.columns and ignore_vars:
                p_titles = df['product_title'].astype(str)
                v_titles = df['variant_title'].astype(str) if 'variant_title' in df.columns else pd.Series([""] * len(df))
                combo_check = p_titles + " (" + v_titles + ")"
                for ignore_str in ignore_vars: df = df[~combo_check.str.lower().str.contains(ignore_str, na=False)]

            def get_identifier(row):
                p = str(row.get('product_title', '')).strip()
                v = str(row.get('variant_title', '')).strip()
                s = str(row.get('sku', '')).strip()
                if p == 'nan': p = ''
                if v == 'nan': v = ''
                if s == 'nan': s = ''
                base_id = p
                if id_mode == 'SKU': base_id = s if s else p
                elif id_mode == 'Product + Variant': base_id = f"{p} ({v})" if v else p
                if use_quantity and row['quantity'] > 1: return f"{row['quantity']}x {base_id}"
                return base_id

            df['identifier'] = df.apply(get_identifier, axis=1)
            df = df[(df['identifier'] != '') & (df['identifier'] != 'nan')]

            if 'date' in df.columns: df['date'] = pd.to_datetime(df['date'], utc=True, errors='coerce')
            if 'customer_id' not in df.columns: df['customer_id'] = None
            if 'email' not in df.columns: df['email'] = None
            df['final_cust_id'] = df['customer_id'].fillna(df['email']).fillna('(unknown)')

            order_groups = df.groupby('order_id').agg({
                'identifier': lambda x: sorted(list(x)),
                'net_sales': 'sum',
                'final_cust_id': 'first',
                'date': 'min'
            }).reset_index()

            def create_mix_string(items):
                unique_items = sorted(list(set(items)))
                return ' + '.join(unique_items)

            order_groups['product_mix'] = order_groups['identifier'].apply(create_mix_string)
            order_groups = order_groups[order_groups['product_mix'] != '']

            mix_df = order_groups.groupby('product_mix').agg({'order_id': 'count', 'net_sales': 'sum'}).reset_index()
            mix_df.columns = ['Product mix', 'Orders', 'Net sales']
            
            total_orders = mix_df['Orders'].sum()
            total_net = mix_df['Net sales'].sum()
            
            mix_df['% of total'] = mix_df['Orders'] / total_orders
            mix_df['% of net sales'] = mix_df['Net sales'] / total_net
            mix_df = mix_df[['Product mix', 'Orders', '% of total', 'Net sales', '% of net sales']]
            mix_df = mix_df.sort_values('Orders', ascending=False)
            
            first_orders = order_groups.sort_values('date').drop_duplicates(subset=['final_cust_id'], keep='first')
            first_orders_out = first_orders[['final_cust_id', 'order_id', 'date', 'product_mix']].copy()
            first_orders_out.columns = ['Customer ID', 'First order ID', 'First order date', 'First order product mix']

            st.success(APP_CONFIG["success_msg"].format(n=total_orders))
            
            # --- METRICS SECTION (Bold, Formatted, No Divider) ---
            c1, c2, c3 = st.columns(3)
            # Using F-strings to add commas to numbers and currency
            c1.metric("Unique orders", f"{total_orders:,}")
            c2.metric("Unique mixes", f"{len(mix_df):,}")
            c3.metric("Total net sales", f"${total_net:,.2f}")
            
            # --- DATA TABS ---
            tab1, tab2 = st.tabs(["Order product mix", "First order mix"])
            
            # --- HEADER STYLING CONFIG ---
            # We apply this style to the dataframe to make headers Dark Gray
            header_styles = [
                {'selector': 'th', 'props': [
                    ('background-color', '#1A1A1A'), 
                    ('color', '#F3F3F3'), 
                    ('font-weight', 'bold')
                ]}
            ]

            with tab1:
                # Apply styling and format values
                st.dataframe(
                    mix_df.style.set_table_styles(header_styles).format({
                        '% of total': '{:.2%}', 
                        'Net sales': '${:,.2f}', 
                        '% of net sales': '{:.2%}'
                    }), 
                    use_container_width=True, 
                    hide_index=True
                )
                excel_data = convert_to_excel(mix_df, "Order Product Mix")
                st.download_button("Download Excel Report", excel_data, "order_mix_branded.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                
            with tab2:
                st.dataframe(
                    first_orders_out.style.set_table_styles(header_styles), 
                    use_container_width=True, 
                    hide_index=True
                )
                excel_data_first = convert_to_excel(first_orders_out, "First Order Mix")
                st.download_button("Download Excel Report", excel_data_first, "first_order_mix_branded.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        except Exception as e:
            st.error(f"Something went wrong: {e}")

