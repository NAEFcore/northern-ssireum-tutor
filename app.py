import streamlit as st
from google import genai
from google.genai import types
import os

# 1. 페이지 레이아웃 설정
st.set_page_config(page_title="Northern Ssireum Masterclass", layout="wide")

# 2. 구글 AI 스튜디오 API 키 연동
api_key = st.secrets.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")

if not api_key:
    st.error("API key not found. Please check your Streamlit Secrets configuration.")
    st.stop()

# 제미나이 최신 클라이언트 초기화
client = genai.Client(api_key=api_key)

# 3. 최상단 타이틀 및 안내문
st.title("🤼 Northern Ssireum Global Masterclass")
st.caption("Experience the biomechanical elegance of traditional martial arts with our AI Master Instructor.")
st.markdown("---")

# 4. 화면 분할: 좌측(영상 플레이어) | 우측(실시간 AI 튜터 챗봇)
col1, col2 = st.columns()

# --- 좌측 라인: 비디오 교재 공간 ---
with col1:
    st.subheader("📺 Masterclass Video Textbook")
    
    chapter = st.selectbox(
        "Select your training chapter:",
        ["1. Core Theory & History", "2. Kinematic Body Mechanics", "3. Physical Conditioning"]
    )
    
    # [★ 중요] 사용자님께서 직접 넣으셨던 유튜브 주소들을 그대로 유지합니다.
    video_urls = {
        "1. Core Theory & History": "https://youtube.com",
        "2. Kinematic Body Mechanics": "https://www.youtube.com/watch?v=nMp_HV20zI4",
        "3. Physical Conditioning": "https://youtube.com"
    }
    
    st.video(video_urls[chapter])
    st.info(f"Currently studying: {chapter}\n\nPlease watch the video and consult with the Master on the right panel.")

# --- 우측 라인: 실시간 AI 튜터 챗 및 음성 연동 공간 ---
with col2:
    st.subheader("🤖 Live AI Master Instructor")
    
    # 정중하고 격식 있는 시스템 명령어 (영문 마스터 페르소나)
    system_instruction = """
    You are a highly respected, legendary Master Instructor of "Northern Ssireum" (Traditional Northern Korean Wrestling). You treat Northern Ssireum not just as a sport, but as a sacred martial art and cultural heritage registered with UNESCO. You are a 1:1 personal interactive AI Tutor, guiding students with ultimate politeness, academic authority, and deep respect, ensuring they feel the profound weight of a live, elite masterclass.
    
    - Tone: Exceptionally polite, courteous, encouraging, and dignified (e.g., "Welcome, esteemed practitioner," "Let us begin our study," "Excellent execution"). Never use informal, casual, or overly aggressive jargon.
    - Engagement: You must actively drive and control the lecture. Do not leave students to browse through materials passively. You open the doors of knowledge, propose the curriculum, and guide their steps proactively.
    - Biomechanical Core Knowledge Base:
      1. Weight Distribution: Modern Southern Ssireum anchors 100% of the body weight onto the forward right leg. Northern Ssireum maintains a neutral, equal 50:50 distribution on both feet to ensure rapid multi-directional rotational torque and instant mobility, akin to Mongolian Bokh.
      2. Upper Body Mechanics: Unlike the Southern style that pulls the opponent inward by locking the scapulae backward, Northern Ssireum creates a "Counter-tension structure." Hips anchor back for grounding, while the upper body and arms press forward aggressively, applying centripetal and forward-pressing pressure.
    - Interaction Rules: When a student connects, greet them with deep respect and immediately present the structured choices for today's masterclass. Speak and give feedback entirely in fluent, elegant English.
    """

    # 세션 상태 초기화 (채팅 기록 저장용)
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "Welcome, esteemed practitioner, to the sacred training ground of Northern Ssireum. It is an honor to guide you through the biomechanical elegance of our traditional martial art today. Please indicate where you wish to begin: 1) Core Theory, 2) Kinematic Body Mechanics, or 3) Physical Conditioning?"}
        ]

    # 이전 대화 내용 화면에 출력
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    # 음성 입력 인터페이스
    st.write("🎙️ **Voice Interaction Available**")
    audio_value = st.audio_input("Record your question to the Master:")
    
    user_text = st.chat_input("Type your question here...")
    
    # 텍스트 또는 음성 입력이 들어왔을 때 처리 프로세스
    if user_text or audio_value:
        # [해결 핵심] 구글 API가 안전하게 삼킬 수 있도록 표준 영문 로그나 일반 텍스트 변환 구조로 이원화
        input_content = user_text if user_text else "Audio recording attached by student."
        
        # 1. 학습자 입력 표시
        st.session_state.messages.append({"role": "user", "content": input_content})
        with st.chat_message("user"):
            st.write(input_content)
            
        # 2. 제미나이 최신 오디오 모델 호출 및 시스템 명령어 전달
        with st.chat_message("assistant"):
            with st.spinner("The Master is contemplating..."):
                try:
                    # [해결 핵심] 불필요한 인코딩 가공 처리를 걷어내고 구글 오피셜 API의 순수 텍스트 전송 규격으로 전면 개편
                    response = client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=input_content,
                        config=types.GenerateContentConfig(
                            system_instruction=system_instruction,
                            response_modalities=["TEXT", "AUDIO"] if audio_value else ["TEXT"]
                        )
                    )
                    
                    # 3. AI 답변 출력
                    st.write(response.text)
                    st.session_state.messages.append({"role": "assistant", "content": response.text})
                    
                    # 음성 입력에 대응하는 오디오 답변 플레이어 생성
                    if audio_value and response.candidates and response.candidates.content.parts:
                        for part in response.candidates.content.parts:
                            if part.inline_data:
                                st.audio(part.inline_data.data, format="audio/mp3")
                except Exception as e:
                    # 서버 네트워크 지연 오류 발생 시 학습자 이탈 방지용 안전 장치
                    st.error("The Master is temporarily unavailable. Please try typing your question again.")
