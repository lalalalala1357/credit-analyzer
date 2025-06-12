import re
import pandas as pd
import streamlit as st
import pdfplumber

st.title("📘 PDF 學分資料解析 - 自動分類")

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
    current_category = None

    def detect_type(cat_name):
        """根據分類標題，自動判斷是必修 / 選修 / 通識"""
        if "必修" in cat_name:
            return "必修"
        elif "選修" in cat_name or "學群" in cat_name or "專業" in cat_name:
            return "選修"
        elif "通識" in cat_name:
            return "通識"
        else:
            return "未分類"

    for line in lines:
        line = line.strip()
        if re.match(r"^[\u4e00-\u9fa5A-Za-z（）\[\]\s]+$", line) and not re.search(r"\d", line):
            current_category = line
            continue

        match = re.match(r"(.+?)\s+(\d+)\s+(\d+)\s+(\d+)$", line)
        if match:
            course_name = match.group(1).strip()
            credit = int(match.group(2))
            category = current_category or "未分類"
            course_type = detect_type(category)
            data.append({
                "類別": course_type,
                "分類": category,
                "課程": course_name,
                "學分": credit
            })

    if data:
        df = pd.DataFrame(data)
        st.subheader("📊 課程分類表")
        st.dataframe(df)

        st.markdown("### ✅ 各類別學分統計")
        total_by_type = df.groupby("類別")["學分"].sum().to_dict()
        total_required = {"必修": 30, "選修": 40, "通識": 20}

        for t in ["必修", "選修", "通識"]:
            earned = total_by_type.get(t, 0)
            required = total_required[t]
            diff = required - earned
            if diff <= 0:
                st.success(f"✔️ {t} 已達標：{earned} / {required} 學分")
            else:
                st.warning(f"⚠️ {t} 尚缺：{diff} 學分（已修 {earned} / 需要 {required}）")

        total_earned = df["學分"].sum()
        total_required_sum = sum(total_required.values())
        total_diff = total_required_sum - total_earned

        st.markdown("### 🎯 總學分")
        if total_diff <= 0:
            st.success(f"🎉 已修總學分 {total_earned}，已達畢業門檻 {total_required_sum}！")
        else:
            st.info(f"目前總學分：{total_earned} / {total_required_sum}，還差 {total_diff} 學分")

    else:
        st.error("⚠️ 無法解析課程資料，請確認格式正確")
