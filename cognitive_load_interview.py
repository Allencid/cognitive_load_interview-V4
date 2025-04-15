import streamlit as st
import re
import io
from docx import Document
from textwrap import wrap

st.set_page_config(page_title="時序陳述分析系統", layout="wide")
st.title("🧭 時序陳述分段與補問工具")

# 初始化階段狀態與參數
if "stage" not in st.session_state:
    st.session_state.stage = "input"
if "max_segs" not in st.session_state:
    st.session_state.max_segs = 4
if "segment_mode" not in st.session_state:
    st.session_state.segment_mode = "語意自動分段"

# 時序詞分段
def split_text_by_time(text):
    time_cues = r"(?<!\d)(\d{1,2}點(?:\d{1,2}分)?|早上|中午|下午|傍晚|晚上|清晨|凌晨|當時|後來|接著|那時候|之後|突然|隔天|前一天|一天|某天|同時)(?!\d)"
    split_points = [m.start() for m in re.finditer(time_cues, text)]
    segments = []

    if not split_points:
        return [text]

    split_points.append(len(text))
    for i in range(len(split_points) - 1):
        segment = text[split_points[i]:split_points[i+1]].strip()
        if segment:
            segments.append(segment)

    return segments

# 語意自動分段：根據語意斷點切分
def semantic_split(text, max_segs=4):
    cues = ["後來", "接著", "結果", "然後", "那時候", "過沒多久", "當時", "突然", "接下來", "最後"]
    pattern = r"(?<=。|，|,|\.|\n)(" + "|".join(cues) + r")"
    segments = re.split(pattern, text)

    # 合併 cue 到句子中，重新整理段落
    final = []
    temp = ""
    for seg in segments:
        if seg.strip() in cues:
            temp += seg
        else:
            if temp:
                final.append(temp + seg.strip())
                temp = ""
            else:
                final.append(seg.strip())

    # 合併為指定段數
    if len(final) > max_segs:
        size = len(final) // max_segs
        grouped = ["".join(final[i:i+size]) for i in range(0, len(final), size)]
        return grouped
    return final

# 主流程
if st.session_state.stage == "input":
    st.header("✏️ 請輸入完整陳述內容")
    st.markdown("""
    請你把整件事情從頭到尾仔細地跟我說一遍，不管重要或不重要的細節都跟我說，
    你可以自己決定從什麼時候開始說，也可以自己決定說到什麼時候結束。
    """)

    statement = st.text_area("你的陳述內容：", height=300)

    st.markdown("---")
    st.session_state.segment_mode = st.radio("分段模式選擇：", ["語意自動分段", "時間詞分段"])
    st.session_state.max_segs = st.slider("你希望最多分成幾段？", min_value=2, max_value=10, value=4)

    if st.button("📌 自動分段與產生補問") and statement:
        st.session_state.statement = statement
        st.session_state.stage = "segmentation"
        st.rerun()


elif st.session_state.stage == "segmentation":
    statement = st.session_state.statement
    responses = []

    # 分段模式
    if st.session_state.segment_mode == "時間詞分段":
        base_segments = split_text_by_time(statement)
    else:
        base_segments = semantic_split(statement, st.session_state.max_segs)

    # 萬一太少則強制均分
    if len(base_segments) < 2:
        segment_len = len(statement) // st.session_state.max_segs
        base_segments = [statement[i:i+segment_len] for i in range(0, len(statement), segment_len)]

    edited_segments = []
    st.subheader("📗 分段與可編輯補問區")

    for i, seg in enumerate(base_segments, 1):
        st.markdown(f"### 📍 段落 {i}")
        keep = st.checkbox("✅ 保留此段落", value=True, key=f"keep_{i}")
        if not keep:
            continue

        edited = st.text_area(f"📝 你可以修改這段內容", value=seg, key=f"edit_seg_{i}")
        edited_segments.append(edited)

        with st.expander(f"🗨️ 補問：關於段落 {i}，你可以講得更仔細一點嗎？"):
            answer = st.text_area(f"你想補充的內容（段落{i}）", key=f"answer_{i}")
            responses.append((f"段落{i}", edited, answer))

            if st.checkbox(f"➕ 我要新增其他問題（段落{i}）", key=f"add_q_{i}"):
                user_q = st.text_input(f"請輸入你的自訂問題：", key=f"user_q_{i}")
                user_a = st.text_area(f"你的回答：", key=f"user_a_{i}")
                responses.append((f"自訂問題 - 段落{i}", user_q, user_a))

    # 補問們
    st.subheader("🔍 延伸補問區")
    with st.expander("補問 1️⃣：在這些事情發生以前的任何事，你可以跟我說的更仔細一點嗎？"):
        q1 = "在這些事情發生以前的任何事，你可以跟我說的更仔細一點嗎..."
        a1 = st.text_area("回答：", key="before_event")
        responses.append(("補問1 - 該事件前的事", q1, a1))

    with st.expander("補問 2️⃣：在這些事情之後到現在發生的任何事情，你可以跟我說的更仔細一點嗎？"):
        q2 = "在這些事情之後到現在發生的任何事情，你可以跟我說的更仔細一點嗎..."
        a2 = st.text_area("回答：", key="after_event")
        responses.append(("補問2 - 該事件後的事", q2, a2))

    with st.expander("補問 3️⃣：為了讓所有調查這個案件的人可以更加相信你說的是實話，你還可以想到什麼事情可以跟我說的嗎？任何事情都可以？"):
        q3 = "為了讓所有調查這個案件的人可以更加相信你說的是實話，你還可以想到什麼事情可以跟我說的嗎？任何事情都可以？"
        a3 = st.text_area("回答：", key="credibility")
        responses.append(("補問3 - 鼓勵誠實補充", q3, a3))

    if st.button("📄 顯示所有回應彙整"):
        st.session_state.responses = responses
        st.session_state.stage = "summary"
        st.rerun()

elif st.session_state.stage == "summary":
    st.subheader("📘 使用者所有補充回應")
    responses = st.session_state.responses
    statement = st.session_state.statement

    txt_output = "【完整陳述內容】\n" + statement.strip() + "\n\n"
    doc = Document()
    doc.add_heading("使用者補充回應彙整", level=1)

    # 新增完整陳述內容區塊
    doc.add_heading("完整陳述內容", level=2)
    doc.add_paragraph(statement.strip())

    for title, context, ans in responses:
        display_text = f"【{title}】\n> {context.strip()}\n✏ 回答：{ans.strip() if ans else '（無）'}\n\n"
        st.text(display_text)
        txt_output += display_text

        doc.add_heading(title, level=2)
        doc.add_paragraph(context.strip())
        doc.add_paragraph(f"回答：{ans.strip() if ans else '（無）'}")

    # 匯出為 TXT 和 DOCX
    txt_bytes = txt_output.encode("utf-8")
    doc_buffer = io.BytesIO()
    doc.save(doc_buffer)
    doc_buffer.seek(0)

    st.download_button("📄 下載為 TXT", data=txt_bytes, file_name="陳述補問彙整.txt", mime="text/plain")
    st.download_button("📘 下載為 DOCX", data=doc_buffer, file_name="陳述補問彙整.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")

