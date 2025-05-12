from dotenv import load_dotenv
load_dotenv()

import streamlit as st
import base64
import os
import io
import datetime
import pdf2image
import fitz  # PyMuPDF
from PIL import Image
import google.generativeai as genai
import pdfkit
import pandas as pd
import matplotlib.pyplot as plt
import docx
from docx.shared import Pt

# Configure Gemini API
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# --- Utility Functions ---

def input_pdf_setup(uploaded_file):
    if uploaded_file is not None:
        images = pdf2image.convert_from_bytes(uploaded_file.read())
        first_page = images[0]
        img_byte_arr = io.BytesIO()
        first_page.save(img_byte_arr, format="JPEG")
        img_byte_arr.seek(0)
        final_image = img_byte_arr.getvalue()
        pdf_parts = [{"mime_type": "image/jpeg", "data": base64.b64encode(final_image).decode()}]
        return pdf_parts
    else:
        raise FileNotFoundError("No file uploaded")

def extract_resume_text(uploaded_file):
    text = ""
    with fitz.open(stream=uploaded_file.read(), filetype="pdf") as doc:
        for page in doc:
            text += page.get_text()
    return clean_resume_text(text)

def clean_resume_text(text):
    lines = text.splitlines()
    cleaned = [line.strip() for line in lines if line.strip()]
    return "\n".join(cleaned)

# --- Gemini Functions ---

def get_gemini_response(prompt, pdf_content, jd_text):
    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content([prompt, pdf_content[0], jd_text])
    return response.text

def rewrite_resume(parsed_resume, job_description):
    prompt = f"""
You are a professional resume writer. Improve the following resume to align it better with the given job description.
Include all technical and relevant skills, even if they are implied.

Job Description:
{job_description}

Original Resume:
{parsed_resume}

Rewrite the resume to include:
- A strong Summary (3-4 lines max)
- A detailed Skills section
- Detailed Experience (Role, Company, Duration, Achievements)
- Projects
- Education
"""
    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content(prompt)
    return response.text

def generate_cover_letter(resume_summary, job_description, role, company):
    prompt = f"""
Write a personalized cover letter based on the details below:
Resume Summary:
{resume_summary}

Role: {role}
Company: {company}

Job Description:
{job_description}
"""
    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content(prompt)
    return response.text

# --- UI Sections ---

# def upload_tab():
#     st.subheader("📎 Upload Resume")
#     uploaded_file = st.file_uploader("Upload your resume (PDF only)", type=["pdf"])
#     candidate_name = st.text_input("👤 Candidate Name")
#     return uploaded_file, candidate_name


def upload_tab():
    st.subheader("📎 Upload Resume")
    uploaded_file = st.file_uploader("Upload your resume (PDF only)", type=["pdf"])
    candidate_name = st.text_input("👤 Candidate Name")

    if uploaded_file:
        st.success("✅ Resume uploaded successfully! You can now start the analysis or other features.")

    return uploaded_file, candidate_name

        


   
def analysis_tab(uploaded_file):
    st.subheader("🧠 Multi-Job ATS Analysis")
    jd1 = st.text_area("Job Description 1")
    jd2 = st.text_area("Job Description 2 (optional)")
    jd3 = st.text_area("Job Description 3 (optional)")
    if uploaded_file and jd1:
        st.success("Resume and Job Description Loaded")
        pdf_content = input_pdf_setup(uploaded_file)
        uploaded_file.seek(0)
        resume_text = extract_resume_text(uploaded_file)
        prompt = "You are a tech recruiter. Evaluate this resume image vs job description and provide match score, missing skills, suggestions."
        results = []
        for idx, jd in enumerate([jd1, jd2, jd3]):
            if jd.strip():
                result = get_gemini_response(prompt, pdf_content, jd)
                score = result.split("%")[0].split()[-1] + "%"
                results.append((f"Job {idx+1}", score, result))

        df = pd.DataFrame(results, columns=["Job", "Match Score", "Analysis"])
        st.dataframe(df[["Job", "Match Score"]])
        for job, score, analysis in results:
            with st.expander(f"🔍 {job} Detailed Analysis"):
                st.write(analysis)
    else:
        st.info("Upload resume and at least one JD")

def rewrite_tab(uploaded_file):
    st.subheader("✍️ Resume Improvement")
    jd = st.text_area("Enter Job Description")
    if uploaded_file and jd:
        uploaded_file.seek(0)
        resume_text = extract_resume_text(uploaded_file)
        rewritten = rewrite_resume(resume_text, jd)
        st.code(rewritten, language="markdown")
        st.download_button("📥 Download Resume Text", rewritten, file_name="Improved_Resume.txt")

def cover_letter_tab(uploaded_file):
    st.subheader("📄 Cover Letter Generator")
    role = st.text_input("Job Role")
    company = st.text_input("Company Name")
    jd = st.text_area("Enter Job Description")
    if uploaded_file and role and company and jd:
        uploaded_file.seek(0)
        resume_text = extract_resume_text(uploaded_file)
        summary = resume_text[:500]
        letter = generate_cover_letter(summary, jd, role, company)
        st.code(letter, language="markdown")
        st.download_button("📥 Download Cover Letter", letter, file_name="Cover_Letter.txt")

# def skill_gap_tab():
#     st.subheader("📊 Skill Gap Visualizer")
#     skills = ["Python", "SQL", "ML", "AWS", "Communication", "Teamwork"]
#     required = [8, 7, 6, 5, 7, 6]
#     current = [6, 5, 4, 3, 8, 7]

#     df = pd.DataFrame({"Skill": skills, "Required": required, "Current": current})
#     df.set_index("Skill").plot(kind="bar", figsize=(8,4), colormap="coolwarm")
#     st.pyplot(plt.gcf())
        


# def suggestion_tab():
#     st.subheader("🎯 Tailored Suggestions")
#     st.markdown("""
# - **Skills to Add**: Cloud, Docker, REST APIs
# - **Experience to Elaborate**: Quantify impact in previous roles
# - **Suggested Metrics**: Improved latency by 30%, Automated reporting with 90% efficiency
#     """)


def export_tab():
    st.subheader("🧾 Export Options")
    content = st.text_area("Paste improved resume to export")
    export_format = st.selectbox("Export Format", ["PDF", "DOCX"])
    if st.button("Export") and content:
        if export_format == "PDF":
            pdfkit.from_string(f"<pre>{content}</pre>", "Improved_Resume.pdf")
            with open("Improved_Resume.pdf", "rb") as f:
                st.download_button("📥 Download PDF", f, file_name="Improved_Resume.pdf")
        else:
            doc = docx.Document()
            para = doc.add_paragraph(content)
            para.style.font.size = Pt(11)
            doc.save("Improved_Resume.docx")
            with open("Improved_Resume.docx", "rb") as f:
                st.download_button("📥 Download DOCX", f, file_name="Improved_Resume.docx")

# --- Main App ---
st.set_page_config(page_title="Agentic Resume Expert")
st.title("🤖 Agentic ATS Resume Evaluator")

# Tabbed Layout
with st.sidebar:
    st.header("🔧 Navigation")
    selected_tab = st.radio("Choose a section", [
        "Upload & Extract Resume",
        "Multi-Job ATS Analysis",
        "Improve Resume",
        "Generate Cover Letter",
        "Export Documents"
    ])

# Display Selected Tab
uploaded_file = None
candidate_name = ""

if selected_tab == "Upload & Extract Resume":
    uploaded_file, candidate_name = upload_tab()
elif selected_tab == "Multi-Job ATS Analysis":
    uploaded_file, _ = upload_tab()
    if uploaded_file:
        analysis_tab(uploaded_file)
elif selected_tab == "Improve Resume":
    uploaded_file, _ = upload_tab()
    if uploaded_file:
        rewrite_tab(uploaded_file)
elif selected_tab == "Generate Cover Letter":
    uploaded_file, _ = upload_tab()
    if uploaded_file:
        cover_letter_tab(uploaded_file)

elif selected_tab == "Export Documents":
    export_tab()
