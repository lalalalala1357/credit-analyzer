import streamlit as st
import pdfplumber
import pandas as pd
import re

st.title("📚 學分分析工具（用學年分類）")

# 🎓 畢業條件輸入
st.sidebar.header("🎓 畢業學分要求設定")
required_total = st.sidebar.number_input("畢業總學分", min_value=1, value=128)
required_required = st.sidebar.number_input("必修學分（含博雅）", min_value=0, value=80)
required_elective = st.sidebar.number_input("選修學分", min_value=0, value=48)

uploaded_file = st.file_uploader("請上傳學分計畫 PDF", type="pdf")

# 判斷學年區段
grade_pattern = re.compile(r"第(一|二|三|四)學年")

# 根據區段標題決定課程初步類別
def detect_section_category(section_title):
    section_title = section_title.lower()
    if "博雅" in section_title:
        return "博雅通識"
    elif "通識" in section_title:
        return "通識"
    elif "選修" in section_title:
        return "選修"
    elif "必修" in section_title:
        return "必修"
    else:
        return "其他"

# 根據課名進行覆寫分類（避免體育歸錯類）
def detect_course_override(course_name, current_section):
    if "體育" in course_name:
        return "體育"
    if "軍事訓練" in course_name or "國防" in course_name:
        return "其他"
    return current_section

if uploaded_file:
    with pdfplumber.open(uploaded_file) as pdf:
        text = ""
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"

    lines = text.split("\n")

    current_grade = "未標示"
    current_section = None
    data = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # 判斷學年
        grade_match = grade_pattern.search(line)
        if grade_match:
            year_num = grade_match.group(1)
            current_grade = f"第{year_num}學年"
            continue

        # 判斷區段標題
        if any(keyword in line for keyword in ["必修", "選修", "通識", "博雅"]):
            current_section = detect_section_category(line)
            continue

        # 課程行
        m = re.match(r"^(.+?)\s+(\d+)\s+(\d+)\s+(\d+)", line)
        if m and current_section:
            course_name = m.group(1).strip("●△ ")
            credit = int(m.group(2))
            category = detect_course_override(course_name, current_section)

            data.append({
                "年級": current_grade,
                "類別": category,
                "課程名稱": course_name,
                "學分": credit,
            })

    if data:
        df = pd.DataFrame(data)

        # 排序學年
        grade_order = {
            "第一學年": 1,
            "第二學年": 2,
            "第三學年": 3,
            "第四學年": 4,
            "未標示": 5
        }

        df["年級排序"] = df["年級"].map(grade_order)
        df = df.sort_values("年級排序")

        st.subheader("✅ 請勾選已修課程（依學年分類）")
        selected_per_grade = {grade: [] for grade in df["年級"].unique()}

        for grade in sorted(df["年級"].unique(), key=lambda x: grade_order.get(x, 99)):
            group_df = df[df["年級"] == grade]
            with st.expander(f"▶️ {grade}"):
                for idx, row in group_df.iterrows():
                    label = f"{row['課程名稱']} ({row['類別']}，{row['學分']} 學分)"
                    checked = st.checkbox(label, key=f"course_{grade}_{idx}")
                    if checked:
                        selected_per_grade[grade].append(row)

        st.subheader("📊 已選課程與學分統計（依學年分開）")
        any_selected = False

        for grade, rows in selected_per_grade.items():
            st.markdown(f"### {grade}")
            if rows:
                any_selected = True
                df_selected = pd.DataFrame(rows)
                st.dataframe(df_selected)

                summary = df_selected.groupby("類別")["學分"].sum().reset_index()
                for _, r in summary.iterrows():
                    st.write(f"{r['類別']}: {r['學分']} 學分")
            else:
                st.info("尚無勾選課程")

        # 🎯 畢業條件總覽
        all_selected_rows = [row for rows in selected_per_grade.values() for row in rows]
        if all_selected_rows:
            df_all = pd.DataFrame(all_selected_rows)

            total_credits = df_all["學分"].sum()
            required_credits = df_all[df_all["類別"].isin(["必修", "博雅通識"])]["學分"].sum()
            elective_credits = df_all[df_all["類別"] == "選修"]["學分"].sum()

            st.subheader("🎯 畢業條件達成檢查")
            col1, col2, col3 = st.columns(3)
            col1.metric("總學分", f"{total_credits} / {required_total}",
                        "✅" if total_credits >= required_total else "❌")
            col2.metric("必修學分（含博雅）", f"{required_credits} / {required_required}",
                        "✅" if required_credits >= required_required else "❌")
            col3.metric("選修學分", f"{elective_credits} / {required_elective}",
                        "✅" if elective_credits >= required_elective else "❌")
        else:
            st.info("請勾選您已修課程以計算學分。")

    else:
        st.error("找不到可辨識的課程資訊，請確認 PDF 格式。")
