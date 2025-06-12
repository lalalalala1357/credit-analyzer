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
    elif "博雅通識" in line:
        return "博雅通識"
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

        # 用 dict 紀錄每學年勾選課程
        selected_per_grade = {grade: [] for grade in df["年級"].unique()}

        for grade, group_df in df.groupby("年級"):
            with st.expander(f"▶️ {grade}"):
                for idx, row in group_df.iterrows():
                    label = f"{row['課程名稱']} ({row['類別']}，{row['學分']} 學分)"
                    checked = st.checkbox(label, key=f"course_{grade}_{idx}")
                    if checked:
                        selected_per_grade[grade].append(row)

        st.subheader("📊 已選課程與學分統計（依學年分開）")

        any_selected = False
        for grade, rows in selected_per_grade.items():
            if rows:
                any_selected = True
                st.markdown(f"### {grade}")
                df_selected = pd.DataFrame(rows)
                st.dataframe(df_selected)

                summary = df_selected.groupby("類別")["學分"].sum().reset_index()
                for _, r in summary.iterrows():
                    st.write(f"{r['類別']}: {r['學分']} 學分")
            else:
                st.markdown(f"### {grade}")
                st.info("尚無勾選課程")

        if not any_selected:
            st.info("請勾選您已修課程以計算學分。")

    else:
        st.error("找不到可辨識的課程資訊，請確認 PDF 格式。")
