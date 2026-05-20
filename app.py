import streamlit as st
import pandas as pd

# Set page layout configuration to wide-screen mode
st.set_page_config(page_title="ILG Auditor Control Center", layout="wide")

# Title Header
st.title("🚚 Intelligent Logistics Gateway (ILG) Auditor")
st.subheader("Enterprise Visual-to-SQL Fleet Reconciliation Matrix")
st.markdown("---")

# ==========================================
# SIDEBAR: INTERACTIVE DATA/VIDEO INPUT LAYER
# ==========================================
st.sidebar.header("🕹️ Gateway Control Panel")

# Feature Request 1: Dynamic Video Selection Methods
video_source = st.sidebar.radio("Select Video Input Feed Source:", ("Upload Local MP4", "Stream via URL Link"))

uploaded_file = None
video_url = ""

if video_source == "Upload Local MP4":
    uploaded_file = st.sidebar.file_uploader("Drag & drop transit gateway video files:", type=["mp4", "avi", "mov"])
    if uploaded_file:
        st.sidebar.success(f"✅ Loaded: {uploaded_file.name}")
else:
    video_url = st.sidebar.text_input("Paste Transit Camera URL Link:", placeholder="https://www.youtube.com/watch?v=...")
    if video_url:
        st.sidebar.success("🔗 External stream link mapped successfully.")

# Custom expected fleet settings widget
st.sidebar.markdown("---")
st.sidebar.subheader("📋 Expected Manifest Settings")
expected_count_input = st.sidebar.number_input("Total Expected Manifest Shipments Today:", min_value=1, value=3)


# ==========================================
# MAIN LAYOUT: EXECUTIVE METRIC CARDS
# ==========================================
# Load your real visual data file captured by your AI pipeline
# Mocking the loaded state matching your exact 48 rows configuration
raw_gold_data = [
    {"Expected_Vehicle": "KW527", "Cargo_Manifest": "General Freight", "AI_Visual_Confirmation": "KW527", "Confidence": 0.995, "Status": "Verified"},
    {"Expected_Vehicle": "TAXI", "Cargo_Manifest": "Priority Courier", "AI_Visual_Confirmation": "TAXI", "Confidence": 0.819, "Status": "Verified"},
    {"Expected_Vehicle": "TRK-9999", "Cargo_Manifest": "High-Value Supply", "AI_Visual_Confirmation": "None (Missing)", "Confidence": 0.000, "Status": "Missing Checkpoint"}
]
df = pd.DataFrame(raw_gold_data)

# Calculate dynamic counts
total_scheduled = expected_count_input
total_verified = len(df[df["Status"] == "Verified"])
missing_count = max(0, total_scheduled - total_verified)
reconciliation_rate = (total_verified / total_scheduled) * 100

# Render top-level KPI metrics grids
col1, col2, col3, col4 = st.columns(4)
col1.metric(label="📊 Total Expected Manifests", value=total_scheduled)
col2.metric(label="✅ Verified Gate Scans", value=total_verified)
col3.metric(label="⚠️ Missing/Bypassed Shipments", value=missing_count, delta="-1 Alert" if missing_count > 0 else "0 Clear", delta_color="inverse")
col4.metric(label="📈 Operational Sync Rate", value=f"{reconciliation_rate:.1f}%")

st.markdown("---")


# ==========================================
# MAIN LAYOUT: SEARCH FILTERS & DATA LOOKUP
# ==========================================
st.header("🔍 Gate Audit Reconciliation Database")

# Feature Request 2: Live custom filter search bar
search_query = st.text_input("Search Database by Vehicle ID / License Plate Number:", placeholder="Type vehicle plate to audit... (e.g. KW527, TAXI)")

# Apply dynamic text filtering rules to your Pandas DataFrame
if search_query:
    filtered_df = df[df["Expected_Vehicle"].str.contains(search_query.upper(), na=False) | 
                     df["AI_Visual_Confirmation"].str.contains(search_query.upper(), na=False)]
else:
    filtered_df = df

# Render the interactive data grid view on the dashboard
st.dataframe(filtered_df, use_container_width=True)


# ==========================================
# OPERATIONAL EXCEPTION ALERTS
# ==========================================
st.markdown("---")
st.subheader("🚨 System Discrepancy Log")

missing_trucks = df[df["Status"] == "Missing Checkpoint"]
if not missing_trucks.empty:
    for _, row in missing_trucks.iterrows():
        st.error(f"**SECURITY BREACH ALERT:** Expected vehicle **{row['Expected_Vehicle']}** carrying **{row['Cargo_Manifest']}** completely skipped the gate checkpoint! Manual audit recommended.")
else:
    st.success("All scheduled operations are 100% synchronized with visual sensor metrics.")