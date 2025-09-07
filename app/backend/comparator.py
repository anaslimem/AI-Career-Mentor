from vectorstore import top_k
import re

HARD_SKILLS = ["python","pytorch","tensorflow","scikit-learn","mlflow","docker","kubernetes","airflow","spark","sql","pandas","numpy","langchain","faiss","chroma","aws","gcp","azure","transformers","llm","prompt engineering"]

def extract_skills(cv_text: str) -> list:
    """Extract skills from CV text using a predefined list of hard skills."""
    cv_text_lower = cv_text.lower()
    found_skills = [skill for skill in HARD_SKILLS if skill in cv_text_lower]
    return found_skills
    
def compare_skills(cv_text: str, vector_store, role: str, k: int = 5):

    # 1️⃣ Extract skills from CV
    skill_patterns = [
        r'\b(python|java|javascript|sql|react|aws|docker)\b',
    ]
    cv_lower = cv_text.lower()
    cv_skills = []
    for pattern in skill_patterns:
        cv_skills.extend(re.findall(pattern, cv_lower, re.IGNORECASE))
    cv_skills = list(set(cv_skills))

    # 2️⃣ Use vector store to find relevant JD evidence
    results = vector_store.similarity_search(cv_text, k=k)
    jd_evidence = [r.page_content for r in results]

    return cv_skills, jd_evidence