import streamlit as st
import pdfplumber
import re

st.title("📚 學分分析小幫手 V4 - 自動偵測 + 手動設定畢業門檻")

uploaded_file = st.file_uploader("請上傳學分計畫表 PDF", type="pdf")

REQUIRED_CREDITS_DEFAULT = {
    "必修": 30,
    "選修": 40,
    "通識": 20,
}

if uploaded_file:
    with pdfplumber.open(uploaded_file) as pdf:
        text = ""
        for page in pdf.pages:
            text += page.extract_text() + "\n"
    st.subheader("PDF 內容預覽")
    st.text(text[:1500])

    # 自動偵測門檻
    detected_credits = {}

    for line in text.split("\n"):
        # 例：必修需修學分：30、必修畢業門檻 30、選修 40 等等
        match = re.search(r"(必修|選修|通識).*?(?:需修學分|畢業門檻|門檻)?[:：]?\s*(\d+)", line)
        if match:
            category, credit = match.groups()
            detected_credits[category] = int(credit)

    st.markdown("### 📊 自動偵測到的畢業門檻（可修改）")

    # 用偵測到的值填入輸入框，沒偵測到用預設值
    required_mandatory = st.number_input(
        "必修學分門檻", value=detected_credits.get("必修", REQUIRED_CREDITS_DEFAULT["必修"])
    )
    required_elective = st.number_input(
        "選修學分門檻", value=detected_credits.get("選修", REQUIRED_CREDITS_DEFAULT["選修"])
    )
    required_general = st.number_input(
        "通識學分門檻", value=detected_credits.get("通識", REQUIRED_CREDITS_DEFAULT["通識"])
    )

    REQUIRED_CREDITS = {
        "必修": required_mandatory,
        "選修": required_elective,
        "通識": required_general,
    }

    # 以下是學分統計（和前面版本類似）
    import pandas as pd
    lines = text.strip().split("\n")
    data = []
    for line in lines:
        match = re.match(r"(必修|選修|通識)\s+(\S+)\s+(\d+)", line)
        if match:
            category, course, credit = match.groups()
            data.append({"類別": category, "課程": course, "學分": int(credit)})

    if data:
        st.subheader("📊 課程分類與學分統計")
        df = pd.DataFrame(data)
        st.dataframe(df)

        total_by_type = df.groupby("類別")["學分"].sum().to_dict()

        st.markdown("### ✅ 各類別學分統計")
        for category, required in REQUIRED_CREDITS.items():
            earned = total_by_type.get(category, 0)
            diff = required - earned
            if diff <= 0:
                st.success(f"✔️ {category} 已達標：{earned} / {required} 學分")
            else:
                st.warning(f"⚠️ {category} 尚缺：{diff} 學分（已修 {earned} / 需要 {required}）")

        st.markdown("### 🎯 總結")
        total_required = sum(REQUIRED_CREDITS.values())
        total_earned = sum(df["學分"])
        total_diff = total_required - total_earned

        if total_diff <= 0:
            st.success(f"🎉 已修總學分 {total_earned}，已達畢業門檻 {total_required}！")
        else:
            st.info(f"目前總學分：{total_earned} / {total_required}，還差 {total_diff} 學分")
    else:
        st.error("⚠️ 找不到可辨識的課程資訊，請確認 PDF 格式正確（如：'必修 國文 2'）")
