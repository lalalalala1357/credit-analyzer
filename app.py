import streamlit as st
import pdfplumber

st.title("📚 學分分析小幫手")

uploaded_file = st.file_uploader("請上傳學分計畫表 PDF", type="pdf")

if uploaded_file is not None:
    st.success(f"已上傳檔案：{uploaded_file.name}")
    with pdfplumber.open(uploaded_file) as pdf:
        text = ""
        for page in pdf.pages:
            text += page.extract_text() + "\n"
    st.subheader("PDF 內容預覽")
    st.text(text)
