
import pandas as pd
import re
import streamlit as st
import plotly.express as px
import numpy as np

# -----------------------------
# DASHBOARD TITLE
# -----------------------------
st.title("📊 Market Price Dashboard")

# -----------------------------
# 1. LOAD DATA FROM EXCEL FILE
# -----------------------------
# file_path = r"C:\Users\kartikey.kumar\OneDrive - Sterlite Power\Desktop\Dashboard\PyPSA_inputs_ts.xlsx"

# @st.cache_data
# def load_data(file):
#     df = pd.read_excel(file, thousands=',')  # handle numbers with commas
#     return df

# df = load_data(file_path)
# st.success(f"Data loaded successfully! Rows: {len(df)} Columns: {len(df.columns)}")



st.subheader("Upload your Excel file (up to 500MB)")
uploaded_file = st.file_uploader("Choose an Excel file", type=["xlsx"], accept_multiple_files=False)

@st.cache_data
def load_data(file):
    df = pd.read_excel(file, thousands=',')  # handle numbers with commas
    return df

if uploaded_file is not None:
    try:
        df = load_data(uploaded_file)
        st.success(f"Data loaded successfully! Rows: {len(df)} Columns: {len(df.columns)}")
    except Exception as e:
        st.error(f"Error loading file: {e}")
        st.stop()
else:
    st.info("Please upload an Excel file to proceed.")
    st.stop()

# -----------------------------
# 2. FILTER REQUIRED COLUMNS
# -----------------------------
patterns = [
    r"AFRYQ125_real_\d{4}",
    r"AuroraQ325_real_\d{4}",
    r"AuroraL_AFRYC_Blended_\d{4}",
    r"AFRYCen_AuroDailyDist_\d{4}",
    r"AURORA_low_\d{4}",
    r"AURORA_high_\d{4}",
    r"Redistributed_real_\d{4}",
    r"AFRYQ126_Central_\d{4}",
    r"AFRYQ126_High_\d{4}",
    r"AFRYQ126_Low_\d{4}"
]

cols = [col for col in df.columns if any(re.fullmatch(p, col) for p in patterns)]
if not cols:
    st.error("No valid columns found in your Excel file!")
    st.stop()
df = df[cols]

# -----------------------------
# 3. PREPARE DATAFRAME WITH VENDOR & SCENARIO
# -----------------------------
data = []
for col in df.columns:
    year = int(col.split("_")[-1])
    avg_price = pd.to_numeric(df[col], errors='coerce').mean()
    if col.startswith("AFRYQ125"):
        vendor, scenario = "AFRY", "Q125_real"
    elif col.startswith("AFRYQ126_Central"):
        vendor, scenario = "AFRY", "Q126_Central"
    elif col.startswith("AFRYQ126_High"):
        vendor, scenario = "AFRY", "Q126_High"
    elif col.startswith("AFRYQ126_Low"):
        vendor, scenario = "AFRY", "Q126_Low"
    elif col.startswith("AuroraQ325"):
        vendor, scenario = "Aurora", "Q325_real"
    elif col.startswith("AuroraL_AFRYC_Blended"):
        vendor, scenario = "Aurora", "Blended"
    elif col.startswith("AFRYCen_AuroDailyDist"):
        vendor, scenario = "AFRY", "Cen_AuroDailyDist"
    elif col.startswith("AURORA_low"):
        vendor, scenario = "Aurora", "low"
    elif col.startswith("AURORA_high"):
        vendor, scenario = "Aurora", "high"
    elif col.startswith("Redistributed"):
        vendor, scenario = "Redistributed", "real"
    else:
        continue
    data.append([vendor, scenario, year, col, avg_price])

df_long = pd.DataFrame(data, columns=["Vendor", "Scenario", "Year", "Column", "Price"])

# -----------------------------
# 4. VIEW SELECTION
# -----------------------------
view = st.sidebar.selectbox("Select View", [
    "Average Price Curve",
    "Heatmap",
    "Hourly Average Price",
    "Solar Hour Average Yearly Price"
])

# -----------------------------
# 5. AVERAGE PRICE CURVE
# -----------------------------
if view == "Average Price Curve":
    st.subheader("📈 Average Yearly Price Curve")
    vendors = st.sidebar.multiselect(
        "Select Vendor",
        df_long["Vendor"].unique(),
        default=list(df_long["Vendor"].unique())
    )
    scenarios = st.sidebar.multiselect(
        "Select Scenario",
        df_long[df_long["Vendor"].isin(vendors)]["Scenario"].unique(),
        default=list(df_long[df_long["Vendor"].isin(vendors)]["Scenario"].unique())
    )
    filtered = df_long[(df_long["Vendor"].isin(vendors)) & (df_long["Scenario"].isin(scenarios))]
    if filtered.empty:
        st.warning("No data for selected filters.")
        st.stop()
    filtered["Label"] = filtered["Vendor"] + " - " + filtered["Scenario"]
    fig = px.line(filtered, x="Year", y="Price", color="Label", markers=True)
    fig.update_layout(xaxis_title="Year", yaxis_title="Average Price (Rs/MWh)",
                      legend_title="Curve", template="plotly_white")
    st.plotly_chart(fig, use_container_width=True)
    with st.expander("See Data Table"):
        st.dataframe(filtered)

# -----------------------------
# 6. HEATMAP VIEW
# -----------------------------
elif view == "Heatmap":
    st.subheader("🔥 Vendor Heatmaps (Month × Hourly Average)")
    show_values = st.sidebar.checkbox("Show Values in Cells", value=False)
    heatmap_height = st.sidebar.slider("Heatmap Height (px)", 300, 800, 500, 50)
    heatmap_width = st.sidebar.slider("Heatmap Width (px)", 300, 1200, 600, 50)
    vendor1 = st.sidebar.selectbox("Select Vendor 1", df_long["Vendor"].unique(), index=0)
    scenario1 = st.sidebar.selectbox("Select Scenario 1", df_long[df_long["Vendor"]==vendor1]["Scenario"].unique(), index=0)
    vendor2 = st.sidebar.selectbox("Select Vendor 2", df_long["Vendor"].unique(), index=1)
    scenario2 = st.sidebar.selectbox("Select Scenario 2", df_long[df_long["Vendor"]==vendor2]["Scenario"].unique(), index=0)
    period_options = ["2026-2030","2031-2035","2036-2040","2041-2045","2046-2050","2051-2055","2056-2060"]
    period = st.sidebar.selectbox("Select 5-Year Period", period_options)
    start_year, end_year = map(int, period.split("-"))
    period_cols = df_long[(df_long["Year"]>=start_year) & (df_long["Year"]<=end_year)]

    def compute_heatmap(vendor_name, scenario_name):
        vendor_cols = period_cols[(period_cols["Vendor"]==vendor_name) & (period_cols["Scenario"]==scenario_name)]["Column"].tolist()
        if not vendor_cols: return None
        df_subset = df[vendor_cols].apply(pd.to_numeric, errors='coerce')
        total_hours = df_subset.shape[0]
        hours_in_day, month_hours = 24, 30*24
        months = [(i // month_hours) % 12 + 1 for i in range(total_hours)]
        hours = [i % hours_in_day for i in range(total_hours)]
        df_subset["Month"] = months
        df_subset["Hour"] = hours
        df_melt = df_subset.melt(id_vars=["Month","Hour"], value_vars=vendor_cols, var_name="Column", value_name="Price")
        df_grouped = df_melt.groupby(["Month","Hour"])["Price"].mean().reset_index()
        return df_grouped.pivot(index="Hour", columns="Month", values="Price")

    col1, col2 = st.columns(2, gap="medium")
    heatmap1 = compute_heatmap(vendor1, scenario1)
    heatmap2 = compute_heatmap(vendor2, scenario2)

    if heatmap1 is not None:
        with col1:
            st.markdown(f"**{vendor1} - {scenario1}**")
            fig1 = px.imshow(heatmap1, labels=dict(x="Month",y="Hour",color="Avg Price"),
                             aspect="auto", text_auto=".0f" if show_values else False,
                             color_continuous_scale="RdYlBu_r")
            fig1.update_layout(height=heatmap_height,width=heatmap_width,margin=dict(l=60,r=60,t=40,b=40))
            fig1.update_xaxes(side="bottom", dtick=1)
            fig1.update_yaxes(dtick=2)
            st.plotly_chart(fig1, use_container_width=False)
    else:
        with col1:
            st.warning(f"No data for {vendor1} - {scenario1} in selected period")

    if heatmap2 is not None:
        with col2:
            st.markdown(f"**{vendor2} - {scenario2}**")
            fig2 = px.imshow(heatmap2, labels=dict(x="Month",y="Hour",color="Avg Price"),
                             aspect="auto", text_auto=".0f" if show_values else False,
                             color_continuous_scale="RdYlBu_r")
            fig2.update_layout(height=heatmap_height,width=heatmap_width,margin=dict(l=60,r=60,t=40,b=40))
            fig2.update_xaxes(side="bottom", dtick=1)
            fig2.update_yaxes(dtick=2)
            st.plotly_chart(fig2, use_container_width=False)
    else:
        with col2:
            st.warning(f"No data for {vendor2} - {scenario2} in selected period")

# -----------------------------
# 7. HOURLY AVERAGE PRICE WITH 5-YEAR AGGREGATE
# -----------------------------
elif view == "Hourly Average Price":
    st.subheader("⏱️ Hourly Average Price Curve (5-Year Average)")

    vendors = st.sidebar.multiselect(
        "Select Vendor", df_long["Vendor"].unique(), default=list(df_long["Vendor"].unique())
    )
    scenarios = st.sidebar.multiselect(
        "Select Scenario", df_long[df_long["Vendor"].isin(vendors)]["Scenario"].unique(),
        default=list(df_long[df_long["Vendor"].isin(vendors)]["Scenario"].unique())
    )

    filtered = df_long[(df_long["Vendor"].isin(vendors)) & (df_long["Scenario"].isin(scenarios))]
    if filtered.empty:
        st.warning("No data for selected filters.")
        st.stop()

    period_options = ["2026-2030","2031-2035","2036-2040","2041-2045","2046-2050","2051-2055","2056-2060"]
    period = st.sidebar.selectbox("Select 5-Year Period", period_options)
    start_year, end_year = map(int, period.split("-"))
    filtered_period = filtered[(filtered["Year"] >= start_year) & (filtered["Year"] <= end_year)]
    if filtered_period.empty:
        st.warning("No data for selected 5-year period.")
        st.stop()

    month_options = ["Overall"] + list(range(1,13))
    month_sel = st.sidebar.selectbox("Select Month (Hourly Price)", month_options)

    data = []
    for vendor in vendors:
        for scenario in scenarios:
            cols = filtered_period[(filtered_period["Vendor"] == vendor) & (filtered_period["Scenario"] == scenario)]["Column"].tolist()
            if not cols: continue
            df_subset = df[cols].apply(pd.to_numeric, errors='coerce')
            total_hours = df_subset.shape[0]
            hours_in_day, month_hours = 24, 30*24
            months = [(i // month_hours) % 12 + 1 for i in range(total_hours)]
            hours = [i % hours_in_day for i in range(total_hours)]
            df_subset["Month"] = months
            df_subset["Hour"] = hours
            df_subset["Price_Avg"] = df_subset[cols].mean(axis=1)
            if month_sel != "Overall":
                df_subset = df_subset[df_subset["Month"] == month_sel]
            df_hourly = df_subset.groupby("Hour")["Price_Avg"].mean().reset_index()
            df_hourly["Label"] = f"{vendor} - {scenario}"
            data.append(df_hourly)
    df_plot = pd.concat(data)
    fig = px.line(df_plot, x="Hour", y="Price_Avg", color="Label", markers=True)
    fig.update_layout(xaxis_title="Hour of Day", yaxis_title="Average Price (Rs/MWh)",
                      legend_title="Vendor - Scenario", template="plotly_white")
    st.plotly_chart(fig, use_container_width=True)
    with st.expander("See Data Table"):
        st.dataframe(df_plot)


# -----------------------------
# 8. SOLAR HOUR AVERAGE YEARLY PRICE
# -----------------------------
elif view == "Solar Hour Average Yearly Price":
    st.subheader(" Solar Hour Average Yearly Price Curve (6 AM - 5PM)")

    vendors = st.sidebar.multiselect(
        "Select Vendor", df_long["Vendor"].unique(), default=list(df_long["Vendor"].unique())
    )
    scenarios = st.sidebar.multiselect(
        "Select Scenario", df_long[df_long["Vendor"].isin(vendors)]["Scenario"].unique(),
        default=list(df_long[df_long["Vendor"].isin(vendors)]["Scenario"].unique())
    )

    filtered = df_long[(df_long["Vendor"].isin(vendors)) & (df_long["Scenario"].isin(scenarios))]
    if filtered.empty:
        st.warning("No data for selected filters.")
        st.stop()

    # Prepare data for plotting
    data = []
    solar_hours = list(range(6,18))  # 6 AM to 5 PM (hour index 6-17)
    for _, row in filtered.iterrows():
        col_name = row["Column"]
        year = row["Year"]
        vendor = row["Vendor"]
        scenario = row["Scenario"]

        df_col = pd.to_numeric(df[col_name], errors='coerce')
        hours_in_day = 24
        total_hours = len(df_col)
        hours = [i % hours_in_day for i in range(total_hours)]
        df_hourly = pd.DataFrame({"Hour": hours, "Price": df_col})
        df_solar = df_hourly[df_hourly["Hour"].isin(solar_hours)]
        avg_solar_price = df_solar["Price"].mean()
        data.append([vendor, scenario, year, avg_solar_price])

    df_plot = pd.DataFrame(data, columns=["Vendor", "Scenario", "Year", "Price"])
    df_plot["Label"] = df_plot["Vendor"] + " - " + df_plot["Scenario"]

    fig = px.line(df_plot, x="Year", y="Price", color="Label", markers=True)
    fig.update_layout(
        xaxis_title="Year",
        yaxis_title="Solar Hour Average Price (Rs/MWh)",
        legend_title="Vendor - Scenario",
        template="plotly_white"
    )
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("See Data Table"):
        st.dataframe(df_plot)
