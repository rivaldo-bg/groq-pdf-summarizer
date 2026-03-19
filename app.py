import streamlit as st
import fitz  # PyMuPDF
import docx
import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="DocSum AI",
    page_icon="📄",
    layout="centered",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Sans:wght@300;400;500&display=swap');

html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
h1, h2, h3 { font-family: 'Syne', sans-serif !important; }

.stApp { background: #0d0d0d; color: #f0ede6; }

section[data-testid="stSidebar"] {
    background: #141414;
    border-right: 1px solid #2a2a2a;
}

.block-container { padding-top: 2.5rem; max-width: 780px; }

div[data-testid="stFileUploader"] {
    background: #161616;
    border: 1.5px dashed #3a3a3a;
    border-radius: 12px;
    padding: 1.2rem;
    transition: border-color 0.2s;
}
div[data-testid="stFileUploader"]:hover { border-color: #e8c547; }

.summary-box {
    background: #161616;
    border: 1px solid #2a2a2a;
    border-left: 4px solid #e8c547;
    border-radius: 10px;
    padding: 1.6rem 1.8rem;
    margin-top: 1.2rem;
    line-height: 1.8;
    font-size: 0.97rem;
    color: #ddd8ce;
}

.meta-chip {
    display: inline-block;
    background: #1e1e1e;
    border: 1px solid #2e2e2e;
    border-radius: 20px;
    padding: 3px 12px;
    font-size: 0.78rem;
    color: #888;
    margin-right: 6px;
    margin-bottom: 8px;
}

.stButton > button {
    background: #e8c547 !important;
    color: #0d0d0d !important;
    font-family: 'Syne', sans-serif !important;
    font-weight: 700 !important;
    border: none !important;
    border-radius: 8px !important;
    padding: 0.55rem 2rem !important;
    font-size: 0.95rem !important;
    letter-spacing: 0.03em !important;
}
.stButton > button:hover { opacity: 0.85 !important; }

.stSelectbox label, .stRadio label {
    color: #888 !important;
    font-size: 0.82rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.08em !important;
}

.title-accent { color: #e8c547; }
hr { border-color: #222 !important; }
</style>
""", unsafe_allow_html=True)

# ── Helpers ───────────────────────────────────────────────────────────────────

def extract_text_from_pdf(file) -> str:
    doc = fitz.open(stream=file.read(), filetype="pdf")
    text = "".join(page.get_text() for page in doc)
    doc.close()
    return text.strip()


def extract_text_from_docx(file) -> str:
    doc = docx.Document(file)
    return "\n".join([p.text for p in doc.paragraphs if p.text.strip()])


def extract_text_from_txt(file) -> str:
    return file.read().decode("utf-8", errors="ignore")


def extract_text(file) -> str:
    name = file.name.lower()
    if name.endswith(".pdf"):
        return extract_text_from_pdf(file)
    elif name.endswith(".docx"):
        return extract_text_from_docx(file)
    elif name.endswith(".txt"):
        return extract_text_from_txt(file)
    return ""


def build_prompt(text: str, style: str, language: str) -> str:
    style_instructions = {
        "Short (2–3 sentences)": "Summarize the document in 2 to 3 concise sentences, capturing only the most essential point.",
        "Detailed paragraph": "Write a thorough, flowing paragraph summary that covers the main ideas, key arguments, and conclusions.",
        "Bullet points": "Summarize the document as a clean bullet-point list. Each bullet should be a distinct key point or finding.",
    }
    lang_note = f" Respond in {language}." if language != "English" else ""
    instruction = style_instructions.get(style, style_instructions["Detailed paragraph"])
    return f"""{instruction}{lang_note}

Document content:
\"\"\"
{text[:12000]}
\"\"\"
"""


def summarize(text: str, style: str, language: str, model: str) -> str:
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    prompt = build_prompt(text, style, language)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "You are an expert document analyst. Your summaries are clear, accurate, and insightful.",
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.4,
        max_tokens=1024,
    )
    return response.choices[0].message.content.strip()


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Settings")
    st.markdown("---")

    model = st.selectbox(
        "Model",
        ["llama3-8b-8192", "llama3-70b-8192", "mixtral-8x7b-32768", "gemma2-9b-it"],
        index=1,
    )

    style = st.radio(
        "Summary Style",
        ["Short (2–3 sentences)", "Detailed paragraph", "Bullet points"],
        index=1,
    )

    language = st.selectbox(
        "Output Language",
        ["English", "French", "Spanish", "German", "Portuguese", "Arabic", "Malagasy"],
        index=0,
    )

    st.markdown("---")
    st.markdown(
        "<span style='color:#555; font-size:0.78rem;'>Powered by Groq · Built with Streamlit</span>",
        unsafe_allow_html=True,
    )

# ── Main UI ───────────────────────────────────────────────────────────────────
st.markdown(
    "<h1 style='margin-bottom:0'>Doc<span class='title-accent'>Sum</span> AI</h1>",
    unsafe_allow_html=True,
)
st.markdown(
    "<p style='color:#666; margin-top:4px; margin-bottom:1.8rem;'>Upload a document — get an instant AI summary.</p>",
    unsafe_allow_html=True,
)

uploaded_file = st.file_uploader(
    "Drop your file here",
    type=["pdf", "docx", "txt"],
    label_visibility="collapsed",
)

if uploaded_file:
    ext = uploaded_file.name.split(".")[-1].upper()
    size_kb = round(uploaded_file.size / 1024, 1)
    st.markdown(
        f"<span class='meta-chip'>📎 {uploaded_file.name}</span>"
        f"<span class='meta-chip'>{ext}</span>"
        f"<span class='meta-chip'>{size_kb} KB</span>",
        unsafe_allow_html=True,
    )

    if st.button("✦ Summarize"):
        with st.spinner("Reading document…"):
            raw_text = extract_text(uploaded_file)

        if not raw_text:
            st.error("Could not extract text from this file. Make sure it's not a scanned/image-only PDF.")
        else:
            word_count = len(raw_text.split())
            st.markdown(
                f"<span class='meta-chip'>~{word_count:,} words extracted</span>",
                unsafe_allow_html=True,
            )

            with st.spinner("Generating summary…"):
                summary = summarize(raw_text, style, language, model)

            st.markdown("#### Summary")
            st.markdown(f"<div class='summary-box'>{summary}</div>", unsafe_allow_html=True)

            st.download_button(
                label="⬇ Download Summary",
                data=summary,
                file_name=f"summary_{uploaded_file.name.rsplit('.', 1)[0]}.txt",
                mime="text/plain",
            )
else:
    st.info("Supported formats: PDF · DOCX · TXT")