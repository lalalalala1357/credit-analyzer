import re
import pandas as pd
import streamlit as st
import pdfplumber

st.title("📘 PDF 學分資料解析")

uploaded_file = st.file_uploader("請上傳 PDF", type="pdf")

if uploaded_file:
    with pdfplumber.open(uploaded_file) as pdf:
        text = ""
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"

    st.subheader("📄 PDF 原始內容")
    st.text(text)

    # 處理課程資料
    lines = text.split("\n")
    data = []
    current_category = None  # 當前分類區塊

    for line in lines:
        line = line.strip()
        # 如果這一行看起來像是分類標題（不含數字，但又很像標題）
        if re.match(r"^[\u4e00-\u9fa5A-Za-z（）\[\]\s]+$", line) and not re.search(r"\d", line):
            current_category = line
            continue

        # 偵測課程格式（結尾有 3 個數字）
        match = re.match(r"(.+?)\s+(\d+)\s+(\d+)\s+(\d+)$", line)
        if match:
            course_name = match.group(1).strip()
            credit = int(match.group(2))
            data.append({
                "分類": current_category or "未分類",
                "課程": course_name,
                "學分": credit
            })

    if data:
        df = pd.DataFrame(data)
        st.subheader("📊 課程表")
        st.dataframe(df)

        st.markdown("### ✅ 各分類學分總計")
        total_by_category = df.groupby("分類")["學分"].sum()
        for category, total in total_by_category.items():
            st.write(f"📌 {category}：{total} 學分")

        st.success(f"🎯 總學分：{df['學分'].sum()}")

    else:
        st.warning("⚠️ 無法解析課程內容，請檢查格式")
