import streamlit as st
import pdfplumber
import pandas as pd
import re

st.title("📚 學分分析工具（用學年分類）")

uploaded_file = st.file_uploader("請上傳學分計畫 PDF", type="pdf")

grade_pattern = re.compile(r"第(一|二|三|四)學年")

def detect_type(line):
    if "必修" in line:
        return "必修"
    elif "選修" in line:
        return "選修"
    elif "通識" in line:
        return "通識"
    else:
        return "其他"

if uploaded_file:
    with pdfplumber.open(uploaded_file) as pdf:
        text = ""
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"

    lines = text.split("\n")

    current_grade = "未標示"
    current_category = "未分類"
    data = []

    for line in lines:
        line = line.strip()
        grade_match = grade_pattern.search(line)
        if grade_match:
            year_num = grade_match.group(1)
            current_grade = f"第{year_num}學年"
            continue

        if any(k in line for k in ["必修", "選修", "通識"]):
            current_category = detect_type(line)
            continue

        m = re.match(r"^(.+?)\s+(\d+)\s+.*$", line)
        if m:
            course_name = m.group(1).strip("●△ ")
            credit = int(m.group(2))
            data.append({
                "年級": current_grade,
                "類別": current_category,
                "課程名稱": course_name,
                "學分": credit,
            })

    if data:
        df = pd.DataFrame(data)

        st.subheader("✅ 請勾選已修課程（依學年分類）")

        selected_rows = []
        # 依年級分組，逐組輸出區塊
        for grade, group_df in df.groupby("年級"):
            with st.expander(f"▶️ {grade}"):
                for idx, row in group_df.iterrows():
                    label = f"{row['課程名稱']} ({row['類別']}，{row['學分']} 學分)"
                    checked = st.checkbox(label, key=f"course_{grade}_{idx}")
                    if checked:
                        selected_rows.append(row)

        if selected_rows:
            df_selected = pd.DataFrame(selected_rows)
            st.subheader("📊 已選課程")
            st.dataframe(df_selected)

            st.subheader("🎯 學分統計（依年級與類別）")
            summary = df_selected.groupby(["年級", "類別"])["學分"].sum().reset_index()
            for _, r in summary.iterrows():
                st.write(f"{r['年級']} - {r['類別']}: {r['學分']} 學分")
        else:
            st.info("請勾選您已修課程以計算學分。")

    else:
        st.error("找不到可辨識的課程資訊，請確認 PDF 格式。")
