import streamlit as st
import pandas as pd
import pdfplumber
import matplotlib.pyplot as plt
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
import tempfile

st.set_page_config(page_title="Credic Financial Solutions - Underwriting Portal", layout="wide")

MASTER_PASSWORD = "credic@123"

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    password = st.text_input("Enter Password", type="password")
    if st.button("Login"):
        if password == MASTER_PASSWORD:
            st.session_state.authenticated = True
        else:
            st.error("Incorrect Password")
    st.stop()

st.title("🏦 Credic Financial Solutions")
st.subheader("Underwriting & CAM Generation Portal")

uploaded_file = st.file_uploader("Upload Bank Statement (Excel or PDF)", type=["xlsx", "pdf"])

def extract_pdf_data(pdf_file):
    data = []
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            table = page.extract_table()
            if table:
                for row in table[1:]:
                    try:
                        date = pd.to_datetime(row[0], errors="coerce")
                        debit = float(str(row[2]).replace(",", "")) if row[2] else 0
                        credit = float(str(row[3]).replace(",", "")) if row[3] else 0
                        balance = float(str(row[4]).replace(",", "")) if row[4] else 0
                        narration = row[1]
                        data.append([date, narration, debit, credit, balance])
                    except:
                        pass
    df = pd.DataFrame(data, columns=["Date", "Narration", "Debit", "Credit", "Balance"])
df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
df = df.dropna(subset=["Date"])   
# Remove unwanted header rows
# Remove commas and spaces
for col in ["Debit", "Credit", "Balance"]:
    df[col] = df[col].astype(str).str.replace(",", "", regex=False)
    df[col] = df[col].str.replace(" ", "", regex=False)

# Convert to numeric
df["Debit"] = pd.to_numeric(df["Debit"], errors="coerce")
df["Credit"] = pd.to_numeric(df["Credit"], errors="coerce")
df["Balance"] = pd.to_numeric(df["Balance"], errors="coerce")

# Fill NaN
df = df.fillna(0
    df = df.dropna(subset=["Date"])
    return df

if uploaded_file:
    if uploaded_file.name.endswith(".xlsx"):
        df = pd.read_excel(uploaded_file)
    else:
        df = extract_pdf_data(uploaded_file)

    df["Date"] = pd.to_datetime(df["Date"])
    df = df.sort_values(by="Date")

    st.subheader("Data Preview")
    st.dataframe(df.head())

    abb = df["Balance"].mean()

    df["Month"] = df["Date"].dt.to_period("M")
    monthly_credit = df.groupby("Month")["Credit"].sum()
    avg_monthly_credit = monthly_credit.mean()

    bounce_count = df["Narration"].str.contains("return|bounce", case=False, na=False).sum()
    negative_days = (df["Balance"] < 0).sum()

    emi_total = df[df["Narration"].str.contains("emi", case=False, na=False)]["Debit"].sum()
    emi_ratio = (emi_total / (avg_monthly_credit * 6)) * 100 if avg_monthly_credit > 0 else 0

    cash_deposit = df[df["Narration"].str.contains("cash", case=False, na=False)]["Credit"].sum()
    total_credit = df["Credit"].sum()
    cash_ratio = (cash_deposit / total_credit) * 100 if total_credit > 0 else 0

    score = 0
    if abb > 150000: score += 20
    if bounce_count <= 1: score += 20
    if negative_days < 5: score += 15
    if emi_ratio < 40: score += 20
    if cash_ratio < 30: score += 10
    if avg_monthly_credit > 200000: score += 15

    if score >= 80:
        grade = "A"
    elif score >= 65:
        grade = "B"
    elif score >= 50:
        grade = "C"
    else:
        grade = "Reject"

    st.subheader("📊 Analysis Summary")

    col1, col2, col3 = st.columns(3)
    col1.metric("6M ABB", f"₹ {round(abb,2)}")
    col2.metric("Avg Monthly Credit", f"₹ {round(avg_monthly_credit,2)}")
    col3.metric("Bounce Count", bounce_count)

    col1.metric("Negative Days", negative_days)
    col2.metric("EMI Ratio %", round(emi_ratio,2))
    col3.metric("Cash Deposit %", round(cash_ratio,2))

    st.subheader(f"🔥 Final Risk Grade: {grade} (Score: {score}/100)")

    st.subheader("Monthly Credit Trend")
    fig, ax = plt.subplots()
    monthly_credit.plot(kind="bar", ax=ax)
    st.pyplot(fig)

    if st.button("Download Excel Report"):
        temp_excel = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
        df.to_excel(temp_excel.name, index=False)
        st.download_button("Download Excel File", open(temp_excel.name, "rb"), file_name="Credic_Analysis.xlsx")

    if st.button("Generate CAM PDF"):
        temp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        doc = SimpleDocTemplate(temp_pdf.name, pagesize=A4)
        elements = []
        styles = getSampleStyleSheet()

        elements.append(Paragraph("Credic Financial Solutions", styles['Heading1']))
        elements.append(Spacer(1, 12))

        data = [
            ["Parameter", "Value"],
            ["6M ABB", str(round(abb,2))],
            ["Avg Monthly Credit", str(round(avg_monthly_credit,2))],
            ["Bounce Count", str(bounce_count)],
            ["Negative Days", str(negative_days)],
            ["EMI Ratio %", str(round(emi_ratio,2))],
            ["Cash Deposit %", str(round(cash_ratio,2))],
            ["Final Grade", grade]
        ]

        table = Table(data)
        table.setStyle([
            ('BACKGROUND',(0,0),(-1,0),colors.grey),
            ('GRID',(0,0),(-1,-1),1,colors.black)
        ])

        elements.append(table)
        doc.build(elements)

        st.download_button("Download CAM Report", open(temp_pdf.name, "rb"), file_name="Credic_CAM_Report.pdf")
