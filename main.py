import streamlit as st
import os
from dotenv import load_dotenv
import google.generativeai as genai
import fitz  # pymupdf for PDF handling
import docx  # python-docx for DOCX handling
import json
from datetime import datetime
import pandas as pd
import sqlite3
import hashlib
import re

# Streamlit UI Setup - Must be first Streamlit command
st.set_page_config(
    page_title="Personalized AI Study Buddy",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load environment variables
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Custom CSS for better styling
st.markdown("""
    <style>
    .main {
        background-color: #f5f5f5;
    }
    .stButton>button {
        width: 100%;
        border-radius: 20px;
        height: 3em;
        background-color: #4CAF50;
        color: white;
        font-weight: bold;
    }
    .stButton>button:hover {
        background-color: #45a049;
    }
    .css-1d391kg {
        padding: 2rem 1rem;
    }
    .stTextInput>div>div>input {
        border-radius: 10px;
    }
    .stSelectbox>div>div>select {
        border-radius: 10px;
    }
    .css-1v0mbdj {
        margin-top: 2rem;
    }
    .css-1wrcr25 {
        background-color: white;
        padding: 2rem;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .css-1d391kg {
        background-color: white;
        padding: 2rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
    .stMarkdown {
        color: #2c3e50;
    }
    .css-1v0mbdj.ebxwdo61 {
        background-color: #4CAF50;
        color: white;
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
    .css-1v0mbdj.ew7r33j0 {
        background-color: #f8d7da;
        color: #721c24;
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
    .css-1v0mbdj.e1f1d6gn0 {
        background-color: #d4edda;
        color: #155724;
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
    </style>
""", unsafe_allow_html=True)

# Database initialization
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (username TEXT PRIMARY KEY, 
                  password TEXT,
                  email TEXT UNIQUE,
                  learning_style TEXT,
                  difficulty_level TEXT,
                  topics_of_interest TEXT,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

# Password hashing
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Email validation
def is_valid_email(email):
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(pattern, email) is not None

# User authentication functions
def signup_user(username, password, email):
    if not is_valid_email(email):
        return False, "Invalid email format"
    
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, password, email) VALUES (?, ?, ?)",
                 (username, hash_password(password), email))
        conn.commit()
        return True, "Signup successful!"
    except sqlite3.IntegrityError:
        return False, "Username or email already exists"
    finally:
        conn.close()

def login_user(username, password):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username = ? AND password = ?",
             (username, hash_password(password)))
    user = c.fetchone()
    conn.close()
    return user is not None

def get_user_data(username):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = c.fetchone()
    conn.close()
    return user

# Initialize database
init_db()

# Initialize session state
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'username' not in st.session_state:
    st.session_state.username = None
if 'user_profile' not in st.session_state:
    st.session_state.user_profile = {
        'learning_style': None,
        'difficulty_level': 'medium',
        'topics_of_interest': [],
        'study_history': [],
        'progress': {}
    }

# Configure Gemini AI
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel("gemini-1.5-pro")

# Authentication UI
if not st.session_state.logged_in:
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.markdown("<h1 style='text-align: center; color: #2c3e50;'>📚 Personalized AI Study Buddy</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #7f8c8d;'>Your personal AI-powered learning companion</p>", unsafe_allow_html=True)
        
        tab1, tab2 = st.tabs(["Login", "Sign Up"])
        
        with tab1:
            st.markdown("<h2 style='text-align: center; color: #2c3e50;'>Welcome Back!</h2>", unsafe_allow_html=True)
            login_username = st.text_input("Username", key="login_username")
            login_password = st.text_input("Password", type="password", key="login_password")
            
            if st.button("Login", key="login_button"):
                if login_user(login_username, login_password):
                    st.session_state.logged_in = True
                    st.session_state.username = login_username
                    user_data = get_user_data(login_username)
                    if user_data[3]:
                        st.session_state.user_profile['learning_style'] = user_data[3]
                    if user_data[4]:
                        st.session_state.user_profile['difficulty_level'] = user_data[4]
                    if user_data[5]:
                        st.session_state.user_profile['topics_of_interest'] = json.loads(user_data[5])
                    st.success("Login successful!")
                    st.rerun()
                else:
                    st.error("Invalid username or password")
        
        with tab2:
            st.markdown("<h2 style='text-align: center; color: #2c3e50;'>Create Account</h2>", unsafe_allow_html=True)
            signup_username = st.text_input("Username", key="signup_username")
            signup_password = st.text_input("Password", type="password", key="signup_password")
            signup_email = st.text_input("Email", key="signup_email")
            
            if st.button("Sign Up", key="signup_button"):
                if len(signup_username) < 3:
                    st.error("Username must be at least 3 characters long")
                elif len(signup_password) < 6:
                    st.error("Password must be at least 6 characters long")
                else:
                    success, message = signup_user(signup_username, signup_password, signup_email)
                    if success:
                        st.success(message)
                    else:
                        st.error(message)

else:
    # Main app content (only shown when logged in)
    st.markdown("<h1 style='text-align: center; color: #2c3e50;'>📚 Personalized AI Study Buddy</h1>", unsafe_allow_html=True)
    
    # Add logout button in sidebar with custom styling
    st.sidebar.markdown("""
        <style>
        .sidebar .sidebar-content {
            background-color: #2c3e50;
        }
        </style>
    """, unsafe_allow_html=True)
    
    if st.sidebar.button("Logout", key="logout_button"):
        st.session_state.logged_in = False
        st.session_state.username = None
        st.session_state.user_profile = {
            'learning_style': None,
            'difficulty_level': 'medium',
            'topics_of_interest': [],
            'study_history': [],
            'progress': {}
        }
        st.rerun()

    # Sidebar Navigation with icons
    st.sidebar.markdown("<h2 style='color: #2c3e50;'>Navigation</h2>", unsafe_allow_html=True)
    page = st.sidebar.radio("", ["🏠 Home", "👤 Profile", "📚 Study Materials", "✍️ Practice Tests", "📈 Progress", "💬 Chat"])

    # Profile Setup with enhanced UI
    def setup_user_profile():
        st.markdown("<h2 style='color: #2c3e50;'>🎯 Personalize Your Learning Experience</h2>", unsafe_allow_html=True)
        
        # Learning Style Assessment
        if not st.session_state.user_profile['learning_style']:
            st.markdown("<h3 style='color: #34495e;'>Let's determine your learning style!</h3>", unsafe_allow_html=True)
            learning_style_q = st.radio(
                "How do you prefer to learn?",
                ["Visual (through images and diagrams)", 
                 "Auditory (through listening and discussion)",
                 "Reading/Writing (through text and notes)",
                 "Kinesthetic (through hands-on practice)"]
            )
            if st.button("Save Learning Style"):
                st.session_state.user_profile['learning_style'] = learning_style_q
                conn = sqlite3.connect('users.db')
                c = conn.cursor()
                c.execute("UPDATE users SET learning_style = ? WHERE username = ?",
                         (learning_style_q, st.session_state.username))
                conn.commit()
                conn.close()
                st.success("Learning style saved!")

        # Difficulty Level with custom styling
        st.markdown("<h3 style='color: #34495e;'>Set Your Difficulty Level</h3>", unsafe_allow_html=True)
        new_difficulty = st.select_slider(
            "Select your preferred difficulty level:",
            options=['beginner', 'medium', 'advanced'],
            value=st.session_state.user_profile['difficulty_level']
        )
        if new_difficulty != st.session_state.user_profile['difficulty_level']:
            st.session_state.user_profile['difficulty_level'] = new_difficulty
            conn = sqlite3.connect('users.db')
            c = conn.cursor()
            c.execute("UPDATE users SET difficulty_level = ? WHERE username = ?",
                     (new_difficulty, st.session_state.username))
            conn.commit()
            conn.close()

        # Topics of Interest with enhanced UI
        st.markdown("<h3 style='color: #34495e;'>Choose Your Topics</h3>", unsafe_allow_html=True)
        topics = st.multiselect(
            "Select your topics of interest:",
            ["Mathematics", "Science", "History", "Literature", "Computer Science", 
             "Languages", "Arts", "Social Studies", "Other"],
            default=st.session_state.user_profile['topics_of_interest']
        )
        if topics != st.session_state.user_profile['topics_of_interest']:
            st.session_state.user_profile['topics_of_interest'] = topics
            conn = sqlite3.connect('users.db')
            c = conn.cursor()
            c.execute("UPDATE users SET topics_of_interest = ? WHERE username = ?",
                     (json.dumps(topics), st.session_state.username))
            conn.commit()
            conn.close()

    # Home Page with enhanced UI
    if page == "🏠 Home":
        st.markdown("""
            <div style='background-color: white; padding: 2rem; border-radius: 10px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);'>
                <h2 style='color: #2c3e50; text-align: center;'>Welcome to Your Personalized AI Study Buddy! 🎓</h2>
                <p style='color: #7f8c8d; text-align: center;'>This AI-powered study assistant adapts to your learning style and helps you achieve your academic goals.</p>
            </div>
        """, unsafe_allow_html=True)
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown("""
                <div style='background-color: #4CAF50; color: white; padding: 1rem; border-radius: 10px; text-align: center;'>
                    <h3>📊 Personalized Materials</h3>
                </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown("""
                <div style='background-color: #2196F3; color: white; padding: 1rem; border-radius: 10px; text-align: center;'>
                    <h3>📝 Practice Tests</h3>
                </div>
            """, unsafe_allow_html=True)
        with col3:
            st.markdown("""
                <div style='background-color: #9C27B0; color: white; padding: 1rem; border-radius: 10px; text-align: center;'>
                    <h3>📈 Progress Tracking</h3>
                </div>
            """, unsafe_allow_html=True)
        with col4:
            st.markdown("""
                <div style='background-color: #FF9800; color: white; padding: 1rem; border-radius: 10px; text-align: center;'>
                    <h3>💬 AI Tutoring</h3>
                </div>
            """, unsafe_allow_html=True)
        
        if not st.session_state.user_profile['learning_style']:
            st.info("👆 Please complete your profile setup in the Profile section to get started!")

    # Profile Page
    elif page == "👤 Profile":
        setup_user_profile()

    # Study Materials
    elif page == "📚 Study Materials":
        st.subheader("📚 Personalized Study Materials")
        
        if not st.session_state.user_profile['learning_style']:
            st.warning("Please complete your profile setup first!")
        else:
            topic = st.text_input("Enter a topic for study materials:")
            if st.button("Generate Materials") and topic:
                try:
                    learning_style = st.session_state.user_profile['learning_style']
                    difficulty = st.session_state.user_profile['difficulty_level']
                    
                    prompt = f"""
                    Create personalized study materials for {topic} considering:
                    - Learning style: {learning_style}
                    - Difficulty level: {difficulty}
                    Include:
                    1. Key concepts
                    2. Examples
                    3. Practice questions
                    4. Study tips
                    """
                    
                    response = model.generate_content(prompt)
                    materials = response.candidates[0].content.parts[0].text
                    st.write(materials)
                    
                    # Save to study history
                    st.session_state.user_profile['study_history'].append({
                        'topic': topic,
                        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        'materials': materials
                    })
                    
                except Exception as e:
                    st.error(f"Error generating materials: {e}")

    # Practice Tests
    elif page == "✍️ Practice Tests":
        st.subheader("📝 Personalized Practice Tests")
        
        if not st.session_state.user_profile['learning_style']:
            st.warning("Please complete your profile setup first!")
        else:
            topic = st.text_input("Enter a topic for practice test:")
            if st.button("Generate Test") and topic:
                try:
                    learning_style = st.session_state.user_profile['learning_style']
                    difficulty = st.session_state.user_profile['difficulty_level']
                    
                    prompt = f"""
                    Create a personalized practice test for {topic} considering:
                    - Learning style: {learning_style}
                    - Difficulty level: {difficulty}
                    Include:
                    1. 5 multiple-choice questions
                    2. 3 short-answer questions
                    3. 1 essay question
                    Format the output clearly with question numbers and options.
                    """
                    
                    response = model.generate_content(prompt)
                    test = response.candidates[0].content.parts[0].text
                    st.write(test)
                    
                except Exception as e:
                    st.error(f"Error generating test: {e}")

    # Progress Tracking
    elif page == "📈 Progress":
        st.subheader("📈 Your Learning Progress")
        
        if st.session_state.user_profile['study_history']:
            st.write("Recent Study Sessions:")
            for session in reversed(st.session_state.user_profile['study_history'][-5:]):
                st.write(f"📅 {session['timestamp']} - Topic: {session['topic']}")
        else:
            st.info("Start studying to track your progress!")

    # AI Chatbot
    elif page == "💬 Chat":
        st.subheader("💬 Personalized AI Tutor")
        user_input = st.text_input("Ask your AI tutor:")
        
        if st.button("Ask") and user_input.strip():
            try:
                learning_style = st.session_state.user_profile['learning_style']
                prompt = f"""
                As an AI tutor, provide a personalized response to: {user_input}
                Consider the user's learning style: {learning_style}
                Provide a detailed, educational response with examples and explanations.
                """
                
                response = model.generate_content(prompt)
                answer = response.candidates[0].content.parts[0].text
                st.write(answer)
                
            except Exception as e:
                st.error(f"Error in AI response: {e}")
        elif not user_input.strip():
            st.warning("Please enter a question before asking AI.")

    # Display user profile summary in sidebar with enhanced styling
    st.sidebar.markdown("---")
    st.sidebar.markdown(f"<h3 style='color: #2c3e50;'>Welcome, {st.session_state.username}!</h3>", unsafe_allow_html=True)
    if st.session_state.user_profile['learning_style']:
        st.sidebar.markdown(f"<p style='color: #34495e;'><strong>Learning Style:</strong> {st.session_state.user_profile['learning_style']}</p>", unsafe_allow_html=True)
        st.sidebar.markdown(f"<p style='color: #34495e;'><strong>Difficulty Level:</strong> {st.session_state.user_profile['difficulty_level']}</p>", unsafe_allow_html=True)
        if st.session_state.user_profile['topics_of_interest']:
            st.sidebar.markdown("<p style='color: #34495e;'><strong>Topics of Interest:</strong></p>", unsafe_allow_html=True)
            for topic in st.session_state.user_profile['topics_of_interest']:
                st.sidebar.markdown(f"<p style='color: #7f8c8d;'>• {topic}</p>", unsafe_allow_html=True)

    st.sidebar.markdown("""
        <div style='background-color: #34495e; color: white; padding: 1rem; border-radius: 10px; margin-top: 2rem;'>
            <p style='text-align: center;'>Developed with Streamlit and Gemini API</p>
        </div>
    """, unsafe_allow_html=True)
