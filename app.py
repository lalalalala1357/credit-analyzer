import streamlit as st
import pdfplumber
import pandas as pd
import re

st.title("📚 課程學分分類分析工具（含子類別 + 自選課程勾選）")

uploaded_file = st.file_uploader("請上傳學分 PDF", type="pdf")

def detect_type_and_subtype(title):
    if "必修" in title:
        if "核心" in title:
            return "必修", "核心必修"
        elif "專業" in title:
            return "必修", "專業必修"
        else:
            return "必修", "一般必修"
    elif "選修" in title or "學群" in title or "專業" in title:
        if "核心" in title:
            return "選修", "核心選修"
        elif "專業" in title:
            return "選修", "專業選修"
        elif "一般" in title:
            return "選修", "一般選修"
        else:
            return "選修", "其他選修"
    elif "通識" in title:
        return "通識", ""
    else:
        return "未分類", ""

if uploaded_file:
    with pdfplumber.open(uploaded_file) as pdf:
        text = ""
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"

    st.subheader("📄 PDF 文字內容預覽")
    st.text_area("PDF內容", text, height=300)

    lines = text.split("\n")
    data = []
    current_block = ""

    for line in lines:
        line = line.strip()

        # 判斷大標題（分類）
        if re.search(r"(必修|選修|通識|學群|專業|核心)", line) and not re.search(r"\d", line):
            current_block = line
            continue

        match = re.match(r"^[●△\s]*([\u4e00-\u9fa5A-Za-z0-9（）【】\[\]\-、&\s]+?)\s+(\d+)\s+(\d+)\s+(\d+)$", line)
        if match:
            course_name = match.group(1).strip()
            credit = int(match.group(2))
            category, subtype = detect_type_and_subtype(current_block)
            data.append({
                "分類標題": current_block,
                "類別": category,
                "子類別": subtype,
                "課程名稱": course_name,
                "學分": credit
            })

    if data:
        df = pd.DataFrame(data)

        st.subheader("✅ 請勾選您已修過的課程")
        selected = []
        for idx, row in df.iterrows():
            label = f"{row['課程名稱']} ({row['類別']} - {row['子類別']}，{row['學分']} 學分)"
            checked = st.checkbox(label, key=f"course_{idx}")
            if checked:
                selected.append(row)

        if selected:
            df_selected = pd.DataFrame(selected)
            st.subheader("📊 您選擇的課程")
            st.dataframe(df_selected)

            # 計算選擇課程的學分統計
            total_by_type_subtype = df_selected.groupby(["類別", "子類別"])["學分"].sum().reset_index()

            st.subheader("🎯 您的學分統計")
            for _, row in total_by_type_subtype.iterrows():
                c = row["類別"]
                s = row["子類別"]
                earned = row["學分"]
                st.write(f"{c} - {s}: {earned} 學分")
        else:
            st.info("請勾選您已修過的課程以計算學分。")

    else:
        st.error("⚠️ 找不到可辨識的課程資訊，請確認PDF格式正確。")
