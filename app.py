import streamlit as st
import pdfplumber
import pandas as pd
import re
from fpdf import FPDF
import io

st.title("📚 學分分析工具")

# 🎓 畢業條件輸入
st.sidebar.header("🎓 畢業學分要求設定")
required_total = st.sidebar.number_input("畢業總學分", min_value=1, value=128)
required_required = st.sidebar.number_input("必修學分", min_value=0, value=80)
required_elective = st.sidebar.number_input("選修學分", min_value=0, value=48)

uploaded_file = st.file_uploader("請上傳學分計畫 PDF", type="pdf")

grade_pattern = re.compile(r"第(一|二|三|四)學年")

section_type = "其他"

def detect_type(line, course_name):
    if "博雅" in line or "博雅" in course_name:
        return "博雅通識"
    elif "必修" in section_type:
        return "必修"
    elif "選修" in section_type:
        return "選修"
    elif "通識" in section_type:
        return "通識"
    else:
        return "其他"

def generate_pdf(dataframe):
    pdf = FPDF()
    pdf.add_page()
    pdf.add_font("NotoSansTC", "", "fonts/NotoSansTC-Regular.ttf", uni=True)
    pdf.set_font("NotoSansTC", size=12)

    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, txt="已修課程報告", ln=True, align="C")
    pdf.ln(10)

    pdf.set_font("Arial", size=12)
    col_widths = [30, 30, 80, 20]
    headers = ["年級", "類別", "課程名稱", "學分"]
    for i, header in enumerate(headers):
        pdf.cell(col_widths[i], 10, header, border=1, align="C")
    pdf.ln()

    for _, row in dataframe.iterrows():
        pdf.cell(col_widths[0], 10, str(row["年級"]), border=1, align="C")
        pdf.cell(col_widths[1], 10, str(row["類別"]), border=1, align="C")
        course_name = str(row["課程名稱"])
        course_display = course_name[:35] + "…" if len(course_name) > 35 else course_name
        pdf.cell(col_widths[2], 10, course_display, border=1, align="L")
        pdf.cell(col_widths[3], 10, str(row["學分"]), border=1, align="C")
        pdf.ln()

    pdf_output = io.BytesIO()
    pdf.output(pdf_output)
    pdf_output.seek(0)
    return pdf_output

if uploaded_file:
    with pdfplumber.open(uploaded_file) as pdf:
        text = ""
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"

    lines = text.split("\n")
    current_grade = "未標示"
    data = []

    for line in lines:
        line = line.strip()

        grade_match = grade_pattern.search(line)
        if grade_match:
            year_num = grade_match.group(1)
            current_grade = f"第{year_num}學年"
            continue

        if any(keyword in line for keyword in ["必修", "選修", "通識", "博雅"]):
            section_type = line

        m = re.match(r"^(.+?)\s+(\d+)\s+(\d+)\s+(\d+)", line)
        if m:
            course_name = m.group(1).strip("●△ ")
            credit = int(m.group(2))
            category = detect_type(line, course_name)

            data.append({
                "年級": current_grade,
                "類別": category,
                "課程名稱": course_name,
                "學分": credit,
            })

    if data:
        df = pd.DataFrame(data)
        grade_order = {"第一學年": 1, "第二學年": 2, "第三學年": 3, "第四學年": 4, "未標示": 5}
        df["年級排序"] = df["年級"].map(grade_order)
        df = df.sort_values("年級排序")

        st.subheader("✅ 請勾選已修課程")

        selected_per_grade = {grade: [] for grade in df["年級"].unique()}

        for grade in sorted(df["年級"].unique(), key=lambda x: grade_order.get(x, 99)):
            group_df = df[df["年級"] == grade]
            with st.expander(f"▶️ {grade}"):
                select_all_key = f"select_all_{grade}"
                select_all = st.checkbox(f"全選 {grade} 課程", key=select_all_key)

                checked_courses = {}
                for idx, row in group_df.iterrows():
                    label = f"{row['課程名稱']} ({row['類別']}，{row['學分']} 學分)"
                    checked = st.checkbox(
                        label,
                        key=f"course_{grade}_{idx}",
                        value=select_all
                    )
                    checked_courses[idx] = checked

                selected_per_grade[grade] = [group_df.loc[idx] for idx, checked in checked_courses.items() if checked]

        st.subheader("📊 已修課程與學分統計")

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
            col2.metric("必修學分", f"{required_credits} / {required_required}",
                        "✅" if required_credits >= required_required else "❌")
            col3.metric("選修學分", f"{elective_credits} / {required_elective}",
                        "✅" if elective_credits >= required_elective else "❌")

            # 匯出功能
            st.subheader("📥 匯出學分報告")

            # CSV
            csv = df_all.to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                label="📄 下載已修課程 CSV",
                data=csv,
                file_name="已修課程報告.csv",
                mime="text/csv"
            )

            # PDF
            pdf_file = generate_pdf(df_all)
            st.download_button(
                label="📝 下載已修課程 PDF",
                data=pdf_file,
                file_name="已修課程報告.pdf",
                mime="application/pdf"
            )
        else:
            st.info("請勾選您已修課程以計算學分。")
    else:
        st.error("找不到可辨識的課程資訊，請確認 PDF 格式。")
