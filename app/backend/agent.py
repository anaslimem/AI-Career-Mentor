from langchain_ollama import OllamaLLM as Ollama
from langchain.prompts import PromptTemplate
from comparator import compare_skills
from job_parser import fetch_and_clean, search_jobs
from vectorstore import build_vector_store, top_k
from chunker import chunk_text
import os
import time
from dotenv import load_dotenv

load_dotenv()

Tavily_API_KEY = os.getenv("TAVILY_API_KEY")
if not Tavily_API_KEY:
    raise ValueError("TAVILY_API_KEY environment variable is not set.")

GAP_PROMPT = PromptTemplate.from_template("""
You are an **expert career mentor, hiring manager, and skills analyst**.  
Your goal is to help the candidate close the gap between their current skills and the target role.  

Analyze the following information carefully:

**TARGET ROLE:** {role}  
**CANDIDATE SKILLS FROM CV:** {cv_skills}  
**RELEVANT JOB DESCRIPTION EXCERPTS:**  
{jd_evidence}

---

### 🔎 Your Task
Provide a **detailed, structured analysis** in the following format:

## ✅ Skills You Already Have
- Clearly list and explain the CV skills that match the target role requirements.
- Add a short note on how these skills are typically applied in the role.

## ❌ High-Priority Missing Skills
- Identify the most important missing skills (order them by importance for the role).
- For each missing skill, explain *why it matters* in this role.

## ⚖️ Skill Gap Analysis
- Summarize the overall gap between current CV and role expectations.
- Highlight strengths the candidate can leverage, and risks if gaps remain unaddressed.

## 📈 30/60/90-Day Action Plan

### 30 Days (Foundation)
- Quick wins and immediate steps to start closing skill gaps  
- Learning resources (online courses, documentation, tutorials)

### 60 Days (Development)
- Intermediate projects and hands-on practice to reinforce skills  
- Networking or portfolio-building opportunities

### 90 Days (Mastery)
- Advanced, role-specific applications (e.g., real-world projects, open-source contributions)  
- Stretch goals to stand out to employers

## 📋 Evidence from Job Descriptions
- Quote specific skills, tools, or responsibilities mentioned in the job postings.  
- Map them directly to the candidate’s current and missing skills.

---

### ✅ Output Guidelines
- Be **specific, actionable, and motivating** (no generic advice).  
- Prioritize skills/tools that recur across multiple job descriptions.  
- Keep the tone professional but encouraging — as if guiding a motivated job seeker.  
- Where possible, suggest **concrete resources** (platforms, project ideas, or certifications).
""")

def test_vector_store_connection():
    """Test if vector store service is available"""
    try:
        # Try to build a minimal vector store to test connection
        test_chunks = ["test content for vector store connection"]
        vs = build_vector_store(test_chunks)
        print("✅ Vector store connection successful")
        return True
    except Exception as e:
        print(f"❌ Vector store connection failed: {e}")
        return False

def test_ollama_connection():
    """Test if Ollama service is available"""
    try:
        ollama_base_url = os.getenv("OLLAMA_BASE_URL")
        model_name = os.getenv("OLLAMA_MODEL")
        
        llm = Ollama(
            model=model_name,
            base_url=ollama_base_url,
            temperature=0.1
        )
        
        # Test with a simple prompt
        response = llm.invoke("Hello, this is a connection test.")
        print("✅ Ollama connection successful")
        return True
    except Exception as e:
        print(f"❌ Ollama connection failed: {e}")
        return False

def run_agent(cv_text: str, role: str, use_fallback_on_failure: bool = True):
    """
    Enhanced version with better error handling and fallback mechanisms
    """
    print(f"🚀 Starting analysis for role: {role}")
    
    # Test connections first
    vector_store_available = test_vector_store_connection()
    ollama_available = test_ollama_connection()
    
    if not ollama_available:
        return "⚠️ Ollama service is not available. Please ensure Ollama is running and the specified model is installed."
    
    jd_texts = []
    
    # 1) Try to fetch job descriptions
    print("🔍 Searching for job descriptions...")
    try:
        raw_jds = search_jobs(role)
        print(f"Found {len(raw_jds)} job search results")
        
        if isinstance(raw_jds, dict):
            values = list(raw_jds.values())
            if values and all(isinstance(v, dict) for v in values):
                norm_jds = values
            else:
                keys = list(raw_jds.keys())
                if keys and all(isinstance(k, str) and (k.startswith("http") or k.startswith("www")) for k in keys):
                    norm_jds = keys
                else:
                    norm_jds = [str(v) for v in values]
        elif isinstance(raw_jds, list):
            norm_jds = raw_jds
        else:
            norm_jds = [raw_jds] if raw_jds else []
        
    except Exception as e:
        print(f"❌ Error searching for jobs: {e}")
        norm_jds = []
    
    # 2) Fetch and clean job descriptions
    print("📄 Processing job descriptions...")
    successful_fetches = 0
    for i, jd in enumerate(norm_jds):
        url = None
        try:
            if isinstance(jd, dict):
                url = jd.get("url") or jd.get("link") or jd.get("job_url") or jd.get("href") or jd.get("apply_link")
                # Check if content is already available
                existing_text = jd.get("html") or jd.get("description") or jd.get("text") or jd.get("body") or jd.get("content")
                if existing_text and isinstance(existing_text, str) and len(existing_text.strip()) > 100:
                    jd_texts.append(existing_text.strip())
                    successful_fetches += 1
                    print(f"✅ Used existing content for JD[{i}]")
                    continue
            elif isinstance(jd, str):
                url = jd.strip()
            
            if not url:
                print(f"⚠️ Skipping JD[{i}] - no URL found")
                continue
            
            print(f"🌐 Fetching JD[{i}] from {url[:50]}...")
            text = fetch_and_clean(url)
            if text and len(text.strip()) > 100:
                jd_texts.append(text)
                successful_fetches += 1
                print(f"✅ Successfully fetched JD[{i}]")
            else:
                print(f"⚠️ JD[{i}] returned insufficient content")
                
            # Add delay between requests
            if i < len(norm_jds) - 1:  # Don't delay after the last request
                time.sleep(1)
                
        except Exception as e:
            print(f"❌ Failed to fetch JD[{i}] from {url}: {e}")
            continue
    
    print(f"📊 Successfully processed {successful_fetches} out of {len(norm_jds)} job descriptions")
    
    # 3) Use fallback content if needed
    if not jd_texts:
        print("⚠️ Could not fetch any job descriptions. Please try a different role")
    
    # 4) Process with vector store (if available) or use simple text matching
    cv_skills = []
    jd_evidence = []
    
    if vector_store_available:
        try:
            print("🧠 Building vector store...")
            chunks = []
            for jd in jd_texts:
                try:
                    chunks.extend(chunk_text(jd))
                except Exception as e:
                    print(f"⚠️ Failed to chunk a job description: {e}")
                    # Add as single chunk if chunking fails
                    chunks.append(jd)
            
            vs = build_vector_store(chunks)
            print("✅ Vector store built successfully")
            
            # Compare skills using vector store
            cv_skills, jd_evidence = compare_skills(cv_text, vs, role)
            print(f"🎯 Found {len(cv_skills)} matching skills and {len(jd_evidence)} evidence pieces")
            
        except Exception as e:
            print(f"❌ Vector store processing failed: {e}")
            vector_store_available = False
    
    if not vector_store_available:
        print("🔄 Using simple text analysis (vector store unavailable)")
        # Simple fallback: extract key terms from CV and JDs
        cv_skills = extract_simple_skills(cv_text)
        jd_evidence = [jd[:500] + "..." if len(jd) > 500 else jd for jd in jd_texts[:3]]
    
    # 5) Generate analysis with Ollama
    print("🤖 Generating skills gap analysis...")
    try:
        ollama_base_url = os.getenv("OLLAMA_BASE_URL")
        model_name = os.getenv("OLLAMA_MODEL")
        
        llm = Ollama(
            model=model_name,
            base_url=ollama_base_url,
            temperature=0.1
        )
        
        prompt = GAP_PROMPT.format(
            role=role,
            cv_skills=", ".join(cv_skills) if cv_skills else "Skills analysis pending - please review CV content",
            jd_evidence="\n\n".join(jd_evidence[:3]) if jd_evidence else f"Job market analysis for {role} position"
        )
        
        response = llm.invoke(prompt)
        print("✅ Analysis complete!")
        return response
        
    except Exception as e:
        error_msg = f"⚠️ Error generating analysis: {str(e)}"
        print(error_msg)
        return error_msg

def extract_simple_skills(cv_text: str) -> list:
    """
    Simple skill extraction fallback when vector store is unavailable
    """
    import re
    
    # Common technical skills patterns
    skill_patterns = [
        r'\b(python|java|javascript|c\+\+|sql|r|scala|golang?|rust)\b',
        r'\b(react|angular|vue|node\.?js|express|django|flask|spring)\b',
        r'\b(aws|azure|gcp|docker|kubernetes|git|jenkins)\b',
        r'\b(pandas|numpy|scikit-learn|tensorflow|pytorch|matplotlib)\b',
        r'\b(mysql|postgresql|mongodb|redis|elasticsearch)\b',
        r'\b(html|css|bootstrap|tailwind|sass)\b',
        r'\b(agile|scrum|devops|ci/cd|microservices)\b'
    ]
    
    skills = []
    cv_lower = cv_text.lower()
    
    for pattern in skill_patterns:
        matches = re.findall(pattern, cv_lower, re.IGNORECASE)
        skills.extend(matches)
    
    # Remove duplicates and return
    return list(set(skills))

if __name__ == "__main__":
    # Test the connections
    print("🔧 Testing system connections...")
    test_vector_store_connection()
    test_ollama_connection()