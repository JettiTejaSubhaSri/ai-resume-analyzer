import streamlit as st
import pdfplumber
import os
import re
from dotenv import load_dotenv
from google import genai

# PDF generation
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

# -----------------------------
# LOAD API KEY
# -----------------------------
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    st.error("❌ API key not found. Add it in .env file")
    st.stop()

# -----------------------------
# CREATE CLIENT
# -----------------------------
client = genai.Client(api_key=api_key)

# -----------------------------
# PDF FUNCTION
# -----------------------------
def create_pdf(score, matched, missing, suggestions):
    doc = SimpleDocTemplate("report.pdf")
    styles = getSampleStyleSheet()
    content = []

    content.append(Paragraph(f"ATS Match Score: {score}%", styles["Title"]))
    content.append(Spacer(1, 10))

    content.append(Paragraph("Matched Skills:", styles["Heading2"]))
    content.append(Paragraph(matched.replace("\n", "<br/>"), styles["BodyText"]))

    content.append(Spacer(1, 10))
    content.append(Paragraph("Missing Skills:", styles["Heading2"]))
    content.append(Paragraph(missing.replace("\n", "<br/>"), styles["BodyText"]))

    content.append(Spacer(1, 10))
    content.append(Paragraph("Suggestions:", styles["Heading2"]))
    content.append(Paragraph(suggestions.replace("\n", "<br/>"), styles["BodyText"]))

    doc.build(content)

    with open("report.pdf", "rb") as f:
        return f.read()

# -----------------------------
# PAGE CONFIG
# -----------------------------
st.set_page_config(page_title="AI Resume Analyzer", page_icon="📄")
st.title("📄 AI Resume Analyzer (ATS System)")

# -----------------------------
# INPUTS
# -----------------------------
job_desc = st.text_area("📌 Paste Job Description")
uploaded_file = st.file_uploader("📂 Upload Resume (PDF)", type="pdf")

# -----------------------------
# PROCESS RESUME
# -----------------------------
if uploaded_file:
    resume_text = ""

    with pdfplumber.open(uploaded_file) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                resume_text += text

    resume_text = resume_text[:5000]

    st.subheader("📄 Resume Preview")
    st.write(resume_text[:1000])

    # -----------------------------
    # ANALYZE
    # -----------------------------
    if job_desc:
        if st.button("🚀 Analyze Resume"):

            with st.spinner("Analyzing..."):

                prompt = f"""
                You are a professional ATS system.

                Analyze the resume against the job description.

                Return output STRICTLY in this format:

                Match Score: <number only>

                Matched Skills:
                - skill1
                - skill2

                Missing Skills:
                - skill1
                - skill2

                Suggestions:
                - suggestion1
                - suggestion2

                Resume:
                {resume_text}

                Job Description:
                {job_desc}
                """

                try:
                    # -----------------------------
                    # AUTO MODEL DETECTION
                    # -----------------------------
                    models = client.models.list()
                    model_name = None

                    for m in models:
                        if "generateContent" in str(m):
                            model_name = m.name
                            break

                    if not model_name:
                        st.error("❌ No supported model found")
                        st.stop()

                    # -----------------------------
                    # CALL API
                    # -----------------------------
                    response = client.models.generate_content(
                        model=model_name,
                        contents=prompt
                    )

                    result = response.text

                    # -----------------------------
                    # PARSE RESULTS
                    # -----------------------------
                    score_match = re.search(r"Match Score:\s*(\d+)", result)
                    score = int(score_match.group(1)) if score_match else 0

                    matched = re.findall(r"Matched Skills:\s*((?:- .*\n?)*)", result)
                    missing = re.findall(r"Missing Skills:\s*((?:- .*\n?)*)", result)
                    suggestions = re.findall(r"Suggestions:\s*((?:- .*\n?)*)", result)

                    matched_text = matched[0] if matched else ""
                    missing_text = missing[0] if missing else ""
                    suggestions_text = suggestions[0] if suggestions else ""

                    # -----------------------------
                    # TABS UI
                    # -----------------------------
                    tab1, tab2, tab3 = st.tabs(["📊 Overview", "🧠 Skills", "💡 Suggestions"])

                    with tab1:
                        st.subheader("ATS Score")
                        st.progress(score / 100)
                        st.success(f"{score}% Match")

                    with tab2:
                        col1, col2 = st.columns(2)

                        with col1:
                            st.markdown("### ✅ Matched Skills")
                            st.write(matched_text if matched_text else "Not found")

                        with col2:
                            st.markdown("### ❌ Missing Skills")
                            st.write(missing_text if missing_text else "Not found")

                    with tab3:
                        st.markdown("### 💡 Suggestions")
                        st.write(suggestions_text if suggestions_text else "Not found")

                    # -----------------------------
                    # DOWNLOAD PDF
                    # -----------------------------
                    pdf_data = create_pdf(score, matched_text, missing_text, suggestions_text)

                    st.download_button(
                        label="📥 Download Report",
                        data=pdf_data,
                        file_name="ATS_Report.pdf",
                        mime="application/pdf"
                    )

                    # optional raw output
                    with st.expander("🔍 Full AI Response"):
                        st.write(result)

                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")