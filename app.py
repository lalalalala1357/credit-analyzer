import streamlit as st
from PyPDF2 import PdfReader

st.title("📚 學分分析小幫手")

uploaded_file = st.file_uploader("請上傳學分計畫表 PDF", type="pdf")

if uploaded_file is not None:
    st.success(f"已上傳檔案：{uploaded_file.name}")
    reader = PdfReader(uploaded_file)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"
    st.subheader("PDF 內容預覽")
    st.text(text[:1000])  # 顯示前1000字
