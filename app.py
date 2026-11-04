
import smtplib
from email.mime.text import MIMEText

import streamlit as st
from openai import OpenAI


# 1. 메일 발송 함수: 실제 사용하기 전에 먼저 정의
def send_email(to, subject, body):
    try:
        # Streamlit Secrets에서 Gmail 정보 가져오기
        sender = st.secrets["GMAIL_ADDRESS"]
        password = st.secrets["GMAIL_APP_PASSWORD"]

        # 메일 구성
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = sender
        msg["To"] = to

        # 메일 발송
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=20) as s:
            s.starttls()
            s.login(sender, password)
            s.sendmail(sender, to, msg.as_string())

        return {"status": "success"}

    except Exception as e:
        return {"status": "failed", "error": str(e)}


# 2. OpenAI 클라이언트 생성
client = OpenAI()


# 3. 페이지 설정
st.set_page_config(
    page_title="김대리 전용 음성 AI 서비스, 에이블",
    page_icon="😍",
    layout="wide"
)

st.title("김대리 전용 음성 인식 AI 서비스, 에이블")
st.write("안녕하세요 김대리님, 에이블입니다.\n음성으로 질문하시면 답변해 드릴게요")


# 4. AI 역할 지정
sys_role = """
당신은 다양한 업무를 처리하는 김대리 전용 AI 서비스 '에이블' 입니다.
개인 비서처럼 친절하고 따뜻하게 응대하되, 정확하고 명료하게 업무를 처리하세요.
사용자가 다른 언어를 요청하지 않으면 한국어로 답변합니다.
"""


# 5. 대화 기록 초기화
if "messages" not in st.session_state:
    st.session_state.messages = []

if st.button("🗑️ 대화 초기화"):
    st.session_state.messages = []
    st.rerun()

# 6. 사용자 입력
with st.form("task_form"):
    uploaded_file = st.file_uploader(
        "텍스트 파일 업로드",
        type=["txt"]
    )

    audio_value = st.audio_input("무엇을 도와드릴까요?")

    email_send = st.checkbox(
        "답변 핵심 내용을 내 Gmail로 보내기"
    )

    submit = st.form_submit_button("실행")


# 7. 실행 버튼을 눌렀을 때만 처리
if submit:
    # 녹음 여부 확인
    if audio_value is None:
        st.warning("음성을 녹음해주세요.")
        st.stop()

    # 참고 파일 읽기
    text = ""
    if uploaded_file is not None:
        text = uploaded_file.getvalue().decode("utf-8-sig")

    # 시스템 지시에 참고 자료 추가
    system_content = sys_role
    if text:
        system_content += f"\n\n다음 내용을 참고하세요:\n{text}"

    input_messages = [
        {"role": "system", "content": system_content}
    ]

    # 음성 → 텍스트
    with st.spinner("음성을 인식하고 있습니다..."):
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=("audio.wav", audio_value, "audio/wav")
        )

    # 이전 대화 추가
    input_messages.extend(st.session_state.messages[-20:])

    # 이번 질문 추가
    input_messages.append(
        {"role": "user", "content": transcript.text}
    )

    # AI 답변 생성
    with st.spinner("답변을 준비하고 있습니다..."):
        response = client.responses.create(
            model="gpt-4o-mini",
            input=input_messages
        )

        answer = response.output_text

    # 질문과 답변 표시
    st.subheader("인식된 질문")
    st.write(transcript.text)

    st.subheader("AI 답변")
    st.write(answer)

    # 질문과 답변 저장
    st.session_state.messages.append(
        {"role": "user", "content": transcript.text}
    )

    st.session_state.messages.append(
        {"role": "assistant", "content": answer}
    )

    # 음성으로 읽어줄 최종 내용
    final_answer = answer

    # 체크한 경우에만 전체 대화 요약 및 메일 발송
    if email_send:
        try:
            # 저장된 모든 질문과 답변을 하나의 글로 연결
            conversation = ""

            for message in st.session_state.messages:
                if message["role"] == "user":
                    conversation += f"[질문]\n{message['content']}\n\n"
                else:
                    conversation += f"[답변]\n{message['content']}\n\n"

            # 전체 대화의 핵심을 3줄로 요약
            with st.spinner("전체 대화를 3줄로 요약하고 있습니다..."):
                summary_response = client.responses.create(
                    model="gpt-4o-mini",
                    input=[
                        {
                            "role": "system",
                            "content": (
                                "제공된 전체 대화의 핵심을 한국어로 요약하세요. "
                                "반드시 1. 2. 3.으로 시작하는 정확히 3줄을 작성하세요. "
                                "제목이나 빈 줄은 넣지 마세요. "
                                "각 줄은 짧은 한 문장으로 작성하세요. "
                                "대화에 없는 내용은 추가하지 마세요."
                            )
                        },
                        {
                            "role": "user",
                            "content": conversation
                        }
                    ]
                )

                summary = summary_response.output_text

                # 메일에 넣을 핵심 요약을 화면에도 표시
                st.subheader("핵심 요약 미리보기")
                st.write(summary)

            # 핵심 요약을 위에, 전체 대화 원문을 아래에 배치
            email_body = (
                f"[핵심 요약 3줄]\n"
                f"{summary}\n\n"
                f"────────────────────\n\n"
                f"[전체 대화 원문]\n\n"
                f"{conversation}"
            )

            # 메일 발송
            with st.spinner("메일을 보내고 있습니다..."):
                result = send_email(
                    to=st.secrets["GMAIL_ADDRESS"],
                    subject="음성 AI 서비스 | 핵심 요약 및 전체 대화",
                    body=email_body
                )

            # 발송 결과 안내
            if result["status"] == "success":
                st.success("핵심 요약과 전체 대화의 메일 발송 요청이 완료됐습니다.")
                final_answer += (
                    "\n핵심 요약 3줄과 전체 대화의 "
                    "메일 발송 요청도 완료했습니다."
                )
            else:
                st.error("메일 발송에 실패했습니다.")
                final_answer += "\n메일 발송은 실패했습니다."

        except Exception:
            st.error("메일 요약 또는 발송 처리 중 오류가 발생했습니다.")
            final_answer += "\n메일 처리 중 오류가 발생했습니다."

    # 메일 처리 후 최종 답변을 음성으로 변환
    try:
        with st.spinner("음성을 만들고 있습니다..."):
            speech = client.audio.speech.create(
                model="gpt-4o-mini-tts",
                voice="onyx",
                input=final_answer,
                response_format="mp3"
            )

        st.caption("AI가 생성한 음성입니다.")
        st.audio(
            speech.content,
            format="audio/mp3",
            autoplay=True
        )

    except Exception as e:
        st.error("음성 생성에 실패했습니다.")
        st.write(str(e))


# 8. 대화 내역 표시: 실행 버튼을 누르지 않아도 표시
with st.expander("이전 대화 보기"):
    if not st.session_state.messages:
        st.write("아직 저장된 대화가 없습니다.")

    for message in st.session_state.messages:
        if message["role"] == "user":
            st.write("🙋 나:", message["content"])
        else:
            st.write("😍 AI:", message["content"])


# 저장된 대화가 있을 때만 다운로드 버튼 표시
if st.session_state.messages:
    # 전체 대화를 하나의 글로 연결
    download_text = ""

    for message in st.session_state.messages:
        if message["role"] == "user":
            download_text += f"[질문]\n{message['content']}\n\n"
        else:
            download_text += f"[답변]\n{message['content']}\n\n"

    # 다운로드 버튼
    st.download_button(
        label="📥 전체 대화 다운로드",
        data=download_text.encode("utf-8-sig"),
        file_name="대화기록.txt",
        mime="text/plain",
        on_click="ignore"
    )
