import streamlit as st
import requests
import os
from dotenv import load_dotenv

load_dotenv()
API_URL = os.getenv("API_URL")  # Updated default port


st.title("🎯 AI Career Mentor – CV vs Job Role Analyzer")
st.markdown("Upload your CV and specify a target role to get personalized career gap analysis!")

# Input section
col1, col2 = st.columns([2, 1])

with col1:
    role = st.text_input("🎯 Target Role (e.g., Machine Learning Engineer, Data Scientist)")

with col2:
    st.markdown("### Examples:")
    st.markdown("• Machine Learning Engineer")
    st.markdown("• Data Scientist") 
    st.markdown("• Software Engineer")
    st.markdown("• DevOps Engineer")

cv = st.file_uploader("📄 Upload your CV (PDF)", type=["pdf"])

if st.button("🔍 Analyze My Career Gap", type="primary") and role and cv:
    with st.spinner("🤖 Analyzing your CV against job market requirements..."):
        try:
            files = {"cv": (cv.name or "resume.pdf", cv.getvalue(), "application/pdf")}
            data = {"role": role}
            
            response = requests.post(f"{API_URL}/analyze", data=data, files=files, timeout=180)
            
            if response.ok:
                result = response.json()
                st.success("✅ Analysis complete!")
                st.markdown("---")
                st.markdown(result["report"])
            else:
                st.error(f"❌ Error: {response.text}")
                
        except requests.exceptions.ConnectionError:
            st.error(f"❌ Cannot connect to backend server at {API_URL}")
            st.info("💡 Make sure the FastAPI backend is running with: `python app.py`")
        except requests.exceptions.Timeout:
            st.error("⏰ Request timed out. The analysis is taking too long.")
        except Exception as e:
            st.error(f"❌ Request failed: {e}")

# Footer
st.markdown("---")
st.markdown("💡 **Tip**: Make sure your CV includes technical skills, projects, and experience relevant to your target role!")

# Debug info in sidebar
with st.sidebar:
    # Test API connection
    try:
        test_response = requests.get(f"{API_URL}/", timeout=5)
        if test_response.ok:
            st.success("✅ Backend connected")
        else:
            st.error("❌ Backend error")
    except:
        st.error("❌ Backend offline")
        st.markdown("Run: `python app.py`")