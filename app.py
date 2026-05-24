import streamlit as st
import pdfplumber
import pandas as pd
import re

st.title("📚 學分分析工具 (勤益科大資工專用版)")

# 🎓 畢業條件設定
st.sidebar.header("🎓 畢業學分要求設定")
required_total = st.sidebar.number_input("畢業總學分", min_value=1, value=130)
required_required = st.sidebar.number_input("必修學分", min_value=0, value=86)
required_elective = st.sidebar.number_input("選修學分", min_value=0, value=44)

uploaded_file = st.file_uploader("請上傳學分計畫 PDF", type="pdf")

def parse_curriculum_text(text):
    text = text.replace("|", " ")
    # 將多個連續空白壓縮成單一空白
    text = re.sub(r'[ \t]+', ' ', text)
    lines = text.split('\n')
    
    data = []
    current_grade = "未標示"
    current_category = "其他"
    
    grade_pattern = re.compile(r"(第一學年|第二學年|第三學年|第四學年)")
    category_pattern = re.compile(r"(共同必修科目|專業必修科目|共同選修科目|專業選修科目|核心專業選修科目|智慧多媒體科技學群選修|學程共同選修|智慧型嵌入式技術學群選修|計畫型選修)")
    
    # 🌟 重大修正：只要結尾有 2 到 3 個數字 (學分 正課 實習)，前面的文字通通當作課名！
    course_pattern = re.compile(r"^(.*?)\s+(\d{1,2})\s+(\d{1,2})(?:\s+(\d{1,2}))?\s*$")

    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        cat_match = category_pattern.search(line)
        if cat_match:
            current_category = cat_match.group(1).replace("科目", "")
            continue
            
        grade_match = grade_pattern.search(line)
        if grade_match:
            current_grade = grade_match.group(1)
            continue
            
        m = course_pattern.search(line)
        if m:
            raw_name = m.group(1).strip()
            # 過濾掉表格標題 (例如 Total, Credits 等)
            if "Total" in raw_name or "Credits" in raw_name or "Courses" in raw_name or len(raw_name) < 2:
                continue
                
            tags = []
            if "●" in raw_name: tags.append("職能")
            if "△" in raw_name: tags.append("程式")
            if "[AI]" in raw_name: tags.append("AI")
            
            # 清除標籤符號，但完整保留中英文字與 3D/C# 等符號
            clean_name = re.sub(r"[●△]|\[AI\]", "", raw_name).strip()
            if not clean_name:
                continue

            # 第二個區塊現在是學分
            credit = int(m.group(2))
            
            data.append({
                "年級": current_grade,
                "類別": current_category,
                "課程名稱": clean_name,
                "標籤": ", ".join(tags) if tags else "-",
                "學分": credit
            })
            
    return pd.DataFrame(data)

if uploaded_file:
    try:
        with pdfplumber.open(uploaded_file) as pdf:
            text = ""
            for page in pdf.pages:
                # 🌟 重大修正：加入 layout=True，維持 PDF 原始排版，防止雙欄位文字錯亂
                page_text = page.extract_text(layout=True)
                if page_text:
                    text += page_text + "\n"

        df = parse_curriculum_text(text)

        if not df.empty:
            st.success(f"✅ 成功抓取 {len(df)} 筆課程資料！")
            
            # --- 排序邏輯 ---
            grade_order = {"第一學年": 1, "第二學年": 2, "第三學年": 3, "第四學年": 4, "未標示": 99}
            df["年級排序"] = df["年級"].map(grade_order).fillna(99)
            df["類別排序"] = df["類別"].apply(lambda x: 0 if "必修" in x else (1 if "選修" in x else 2))
            df = df.sort_values(["年級排序", "類別排序"]).reset_index(drop=True)

            st.subheader("✅ 請勾選已修課程")
            selected_per_grade = {grade: [] for grade in df["年級"].unique()}

            for grade in df["年級"].unique():
                group_df = df[df["年級"] == grade]
                
                with st.expander(f"▶️ {grade}", expanded=False):
                    select_all = st.checkbox(f"全選 {grade} 課程", key=f"select_all_{grade}")

                    checked_courses = {}
                    for idx, row in group_df.iterrows():
                        label = f"{row['課程名稱']} ({row['類別']}，{row['學分']} 學分)"
                        if row['標籤'] != "-":
                            label += f" [{row['標籤']}]"
                            
                        checked = st.checkbox(label, key=f"course_{idx}", value=select_all)
                        checked_courses[idx] = checked

                    selected_per_grade[grade] = [
                        group_df.loc[idx] for idx, checked in checked_courses.items() if checked
                    ]

            # --- 統計計算 UI ---
            st.subheader("📊 已修課程與學分統計")
            all_selected_rows = [row for rows in selected_per_grade.values() for row in rows]
            
            if all_selected_rows:
                df_all_selected = pd.DataFrame(all_selected_rows)
                
                for grade, rows in selected_per_grade.items():
                    if rows:
                        st.markdown(f"**{grade} 已修清單**")
                        st.dataframe(pd.DataFrame(rows)[["類別", "課程名稱", "標籤", "學分"]], hide_index=True)

                st.divider()

                total_credits = df_all_selected["學分"].sum()
                required_credits = df_all_selected[df_all_selected["類別"].str.contains("必修")]["學分"].sum()
                elective_credits = df_all_selected[df_all_selected["類別"].str.contains("選修")]["學分"].sum()

                core_electives = df_all_selected[df_all_selected["類別"] == "核心專業選修"]
                core_credits = core_electives["學分"].sum()
                core_count = len(core_electives)

                st.subheader("🎯 畢業條件達成檢查")
                
                col1, col2, col3 = st.columns(3)
                col1.metric("總學分", f"{total_credits} / {required_total}",
                            "✅ 達標" if total_credits >= required_total else f"❌ 缺 {required_total - total_credits}")
                col2.metric("必修學分", f"{required_credits} / {required_required}",
                            "✅ 達標" if required_credits >= required_required else f"❌ 缺 {required_required - required_credits}")
                col3.metric("選修學分", f"{elective_credits} / {required_elective}",
                            "✅ 達標" if elective_credits >= required_elective else f"❌ 缺 {required_elective - elective_credits}")

                st.write("---")
                st.markdown("### 💎 核心專業選修檢核")
                st.markdown("規定：**至少修畢 4 門** 且 **累積達 12 學分**。")
                
                progress_col1, progress_col2 = st.columns(2)
                with progress_col1:
                    st.write(f"📌 **門數進度： {core_count} / 4 門**")
                    st.progress(min(core_count / 4.0, 1.0))
                with progress_col2:
                    st.write(f"📌 **學分進度： {core_credits} / 12 學分**")
                    st.progress(min(core_credits / 12.0, 1.0))

                if core_count >= 4 and core_credits >= 12:
                    st.success("🎉 太棒了！您的「核心專業選修」條件已達標！")
                else:
                    st.warning(f"⚠️ 核心專業選修尚未達標：還缺 {max(0, 4 - core_count)} 門課，或 {max(0, 12 - core_credits)} 學分。")

            else:
                st.info("👆 請從上方列表勾選您已修畢的課程以計算學分。")

        else:
            st.warning("⚠️ 找不到可辨識的課程資訊，請確認 PDF 格式是否符合預期。")

    except Exception as e:
        st.error(f"解析 PDF 時發生錯誤: {e}")
