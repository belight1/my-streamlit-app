
import os, base64, json, requests
import streamlit as st
from openai import OpenAI

# OpenAI 클라이언트 생성
client = OpenAI()

# 페이지 설정
st.set_page_config(page_title="음성 AI 서비스", page_icon="❤️🔊", layout="wide")
st.title("음성 인식 AI 서비스")
st.write("음성으로 질문하시면 답변해 드립니다.")

# 역할 지정
sys_role = """
당신은 다양한 업무를 처리하는 AI 서비스입니다.
개인 비서처럼 친절하게 응대합니다.
"""

# 상태 초기화
if "messages" not in st.session_state:
    st.session_state.messages = []

# 지시 영역
with st.form("task_form"):
    uploaded_file = st.file_uploader("텍스트 파일 업로드", type=["txt"])
    audio_value = st.audio_input("무엇을 도와드릴까요?")

# 체크한 경우에만 메일 발송
    email_send = st.checkbox("답변 핵심 내용을 내 Gmail로 보내기")
    submit = st.form_submit_button("실행")

# 버튼을 눌렀을 때만 실행
if submit:
    # 업로드 된 파일이 있으면 디코딩
    text = ""
    if uploaded_file is not None:
        text = uploaded_file.read().decode("utf-8")

    # 녹음이 없으면 녹음 요청
    if audio_value is None:
        st.warning("음성을 녹음해주세요.")
        st.stop()

    # 시스템 메세지
    system_content = sys_role
    if text:
        system_content += f"\n\n다음 내용을 참고하세요:\n{text}"
    input_messages = [{"role": "system", "content": system_content}]

    # STT: 음성 → 텍스트
    transcript = client.audio.transcriptions.create(
        model="whisper-1",
        file=("audio.wav", audio_value, "audio/wav"))

    # 이전 대화를 먼저 추가
    input_messages.extend(st.session_state.messages)

    # 이번 질문을 추가
    input_messages.append({"role": "user", "content": transcript.text})

    # LLM 호출 및 응답 듣기
    with st.spinner("답변을 준비하고 있습니다..."):
        # LLM 호출
        response = client.responses.create(
            model="gpt-4o-mini",
            input=input_messages
        )
        answer = response.output_text

        # 응답 출력
        st.subheader("AI 답변")
        st.write(answer)

        # 이번 질문 저장
        st.session_state.messages.append(
            {"role": "user", "content": transcript.text}
        )

        # 이번 답변 저장
        st.session_state.messages.append(
            {"role": "assistant", "content": answer}
        )

        # 최근 질문·답변 10쌍만 유지
        st.session_state.messages = st.session_state.messages[-20:]

       # 음성으로 읽어줄 최종 답변
        final_answer = answer

        # 체크박스를 선택한 경우에만 요약 및 메일 발송
        if email_send:
            try:
                with st.spinner("핵심 내용을 요약하고 메일을 보내고 있습니다..."):

                    # 이번 질문과 답변을 바탕으로 메일 내용 생성
                    summary_response = client.responses.create(
                        model="gpt-4o-mini",
                        input=[
                            {
                                "role": "system",
                                "content": (
                                    "질문과 답변의 핵심 내용을 한국어로 "
                                    "3~5개의 짧은 항목으로 요약하세요. "
                                    "원문에 없는 내용은 추가하지 마세요."
                                )
                            },
                            {
                                "role": "user",
                                "content": (
                                    f"질문: {transcript.text}\n\n"
                                    f"답변: {answer}"
                                )
                            }
                        ]
                    )

                    summary = summary_response.output_text

                    # 본인 Gmail로 요약 발송
                    result = send_email(
                        to=st.secrets["GMAIL_ADDRESS"],
                        subject="음성 AI 서비스 핵심 요약",
                        body=summary
                    )

                # 실제 발송 결과에 따라 안내
                if result["status"] == "success":
                    st.success("핵심 요약 메일 발송 요청이 완료됐습니다.")
                    final_answer += "\n핵심 요약 메일 발송 요청도 완료했습니다."
                else:
                    st.error("메일 발송에 실패했습니다.")
                    final_answer += "\n메일 발송은 실패했습니다."

            except Exception:
                st.error("메일 요약 또는 발송 처리 중 오류가 발생했습니다.")
                final_answer += "\n메일 처리 중 오류가 발생했습니다."

        # 메일 처리 후 최종 답변을 음성으로 변환
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

        # 저장된 대화 내역 표시
with st.expander("이전 대화 보기"):
    for message in st.session_state.messages:
        if message["role"] == "user":
            st.write("🙋 나:", message["content"])
        else:
            st.write("🤖 AI:", message["content"])


# 라이브러리를 불러오기
import smtplib
from email.mime.text import MIMEText

# 함수 만들기
def send_email(to, subject, body):
    sender = os.getenv("GMAIL_ADDRESS")
    password = os.getenv("GMAIL_APP_PASSWORD")

    # 메일 구성 (본문, 제목, 발신자, 수신자)
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = to

    # 메일 보내기 (with 구문: 오류가 나도 연결이 닫힘)
    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as s:
            s.starttls()
            s.login(sender, password)
            s.sendmail(sender, to, msg.as_string())
        return {"status": "success"}
    except Exception as e:
        return {"status": "failed", "error": str(e)}

if st.button("테스트 메일 보내기"):
    with st.spinner("메일을 보내고 있습니다..."):
        result = send_email(
            to=st.secrets["GMAIL_ADDRESS"],
            subject="음성 AI 서비스 발송 테스트",
            body="테스트 메일입니다. Gmail 연결을 확인합니다."
        )

    if result["status"] == "success":
        st.success("메일 서버가 발송 요청을 정상적으로 받았습니다.")
    else:
        st.error("메일 발송에 실패했습니다.")
        st.write(result["error"])

      
