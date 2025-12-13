import streamlit as st
import httpx
import json

# --- CONFIGURATION ---
BACKEND_URL = "http://127.0.0.1:8000"  # Ensure your FastAPI is running here
st.set_page_config(page_title="PRISM AI", page_icon="🌈", layout="wide")

# --- STATE MANAGEMENT ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "user_id" not in st.session_state:
    st.session_state.user_id = "test_user_1"  # You can make this dynamic later
if "image_url" not in st.session_state:
    st.session_state.image_url = ""

# --- CUSTOM CSS (For "WhatsApp" Style Bubbles) ---
st.markdown("""
<style>
.stChatMessage { font-family: 'Inter', sans-serif; }
.user-msg { background-color: #2b313e; padding: 10px; border-radius: 10px; margin-bottom: 5px;}
.ai-msg { background-color: #0e1117; padding: 10px; border-radius: 10px; border: 1px solid #303030; margin-bottom: 5px;}
</style>
""", unsafe_allow_html=True)

# --- SIDEBAR (Debug & Tools) ---
with st.sidebar:
    st.title("🌈 PRISM Controls")
    st.write(f"**User ID:** {st.session_state.user_id}")
    st.text_input("Optional Image URL (for vision)", key="image_url", placeholder="https://...")
    
    if st.button("🗑️ Wipe Memory"):
        try:
            r = httpx.delete(f"{BACKEND_URL}/me/memory", params={"user_id": st.session_state.user_id}, timeout=10.0)
            if r.status_code == 200:
                st.success("Short-term memory cleared!")
            else:
                st.warning(f"Wipe failed: {r.status_code}")
        except Exception as e:
            st.error(f"Backend offline: {e}")

    st.markdown("---")
    st.subheader("📊 Live Mood")
    # Placeholder for mood graph (we can fetch from backend later)
    st.progress(70, text="Current Mood: Energetic ⚡")

# --- MAIN CHAT LOGIC ---

st.title("🌈 PRISM: Personal AI")
st.caption("Powered by Llama 3, Neo4j, & Real-Time Web")

# 1. Display Chat History
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        # If the message had a video, show it again
        if "video_data" in msg and msg["video_data"]:
             st.video(msg["video_data"]["link"])

# 2. Chat Input
if prompt := st.chat_input("Ask PRISM..."):
    # Show User Message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Get AI Response
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        message_placeholder.markdown("⚡ *Thinking...*")
        
        try:
            # Call Backend
            payload = {"message": prompt, "user_id": st.session_state.user_id}
            if st.session_state.image_url:
                payload["image_url"] = st.session_state.image_url
            response = httpx.post(
                f"{BACKEND_URL}/chat/",
                json=payload,
                timeout=60.0 # Deep research takes time
            )
            
            if response.status_code == 200:
                data = response.json()
                reply_text = data["reply"]
                intent = data["intent"]
                action_data = data.get("action_data") # Video/Music data
                
                # --- SPECIAL HANDLING FOR YOUTUBE ---
                video_url = None
                if intent == "youtube_play" and action_data:
                     # Parse the JSON string from action_data if it comes as string
                    if isinstance(action_data, str):
                        try:
                            vid_info = json.loads(action_data)
                        except Exception:
                            vid_info = None
                    else:
                        vid_info = action_data
                    if vid_info and 'link' in vid_info:
                        video_url = vid_info['link']
                        title = vid_info.get('title', 'Video')
                        reply_text = f"**Now Playing:** {title}\n\n" + reply_text

                # Display Text
                message_placeholder.markdown(reply_text)
                
                # Display Video if exists
                if video_url:
                    st.video(video_url)

                # Save to History
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": reply_text,
                    "video_data": {"link": video_url} if video_url else None
                })
                
            else:
                message_placeholder.error(f"Backend Error: {response.status_code}")
                
        except Exception as e:
            message_placeholder.error(f"Connection Error: {e}")