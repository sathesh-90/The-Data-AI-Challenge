"""
job_profile.py
==============

Structured encoding of the released Job Description
("Senior AI Engineer - Founding Team", Redrob AI).

The JD is qualitative prose, so the signal that matters is not a keyword list
but the *intent* behind it. This module turns that intent into the lexicons,
weights and thresholds the scorer uses. Every entry here is traceable to a
specific line in data/raw/job_description.md.

Key intent captured (see the "Final note for participants" section of the JD):
  * Reward people who *built* retrieval / ranking / recommendation / search at
    product companies, even if their profile uses plain language.
  * Punish keyword-stuffers: an AI-skill-laden profile whose title is
    "Marketing Manager" is NOT a fit, no matter how perfect the skill list.
  * Down-weight candidates who are not actually hire-able (dead engagement).
"""

from __future__ import annotations

# Reference "today" for the synthetic dataset. The first candidate's current
# role starts 2024-03-08 with duration_months=27 -> ~2026-06, which matches the
# challenge's stated `currentDate`. Used for recency / tenure math.
REFERENCE_DATE = (2026, 6, 28)


# ---------------------------------------------------------------------------
# 1. Core competencies the JD says you "absolutely need"
#    (embeddings retrieval, vector search, ranking, NLP/IR, eval frameworks)
# ---------------------------------------------------------------------------
CORE_COMPETENCIES = {
    # embeddings / retrieval
    "embedding", "embeddings", "sentence-transformers", "sentence transformers",
    "sbert", "bge", "e5", "semantic search", "dense retrieval", "retrieval",
    "rag", "retrieval augmented", "retrieval-augmented",
    # vector / hybrid search infra
    "faiss", "pinecone", "weaviate", "qdrant", "milvus", "opensearch",
    "elasticsearch", "vector search", "vector database", "vector db",
    "hybrid search", "bm25", "lucene", "solr",
    # ranking / recsys / IR
    "ranking", "learning to rank", "ltr", "recommendation", "recommender",
    "recsys", "recommendation system", "personalization", "relevance",
    "information retrieval", "search relevance", "matching",
    # NLP / LLM core
    "nlp", "natural language processing", "transformer", "transformers",
    "bert", "llm", "large language model", "fine-tuning", "fine tuning",
    "lora", "qlora", "peft",
    # evaluation frameworks (explicitly required)
    "ndcg", "mrr", "map", "mean average precision", "a/b test", "a/b testing",
    "ab testing", "offline evaluation", "online evaluation",
}

# Strong "evidence of shipping" phrases that appear in career-history
# descriptions. These are what separate a real builder from a keyword stuffer.
EVIDENCE_PHRASES = {
    "recommendation system", "recommender", "ranking system", "ranking model",
    "search system", "search engine", "retrieval", "semantic search",
    "vector search", "embedding", "embeddings", "personalization",
    "relevance", "information retrieval", "learning to rank",
    "matching system", "candidate matching", "a/b test", "ab test",
    "production", "at scale", "real users", "latency", "deployed",
    "served", "throughput", "ndcg", "click-through",
}

# ---------------------------------------------------------------------------
# 2. Adjacent / supporting skills - good, but not the decisive signal
# ---------------------------------------------------------------------------
ADJACENT_COMPETENCIES = {
    "machine learning", "deep learning", "data science", "pytorch",
    "tensorflow", "scikit-learn", "sklearn", "xgboost", "lightgbm",
    "python", "spark", "pyspark", "airflow", "kafka", "sql", "mlops",
    "model serving", "inference", "feature engineering", "data engineering",
    "data pipeline", "etl", "docker", "kubernetes", "aws", "gcp", "azure",
}

# ---------------------------------------------------------------------------
# 3. Off-domain skills the JD explicitly does NOT want as a *primary* expertise
#    ("primary expertise is computer vision, speech, or robotics without
#     significant NLP/IR exposure ... you'd be re-learning fundamentals here")
# ---------------------------------------------------------------------------
OFF_DOMAIN_SKILLS = {
    "image classification", "object detection", "computer vision", "opencv",
    "image segmentation", "ocr", "speech recognition", "asr", "tts",
    "text to speech", "speech synthesis", "robotics", "slam", "ros",
    "motion planning", "autonomous", "lidar",
}

# Non-engineering primary titles. These are the keyword-stuffer traps in the
# dataset: profiles loaded with AI skills but a current title that has nothing
# to do with building ML systems. The JD calls this out directly.
NON_ENGINEERING_TITLES = {
    "marketing manager", "hr manager", "human resources", "recruiter",
    "accountant", "sales executive", "sales manager", "graphic designer",
    "content writer", "copywriter", "operations manager", "customer support",
    "customer success", "office manager", "administrative", "receptionist",
    "civil engineer", "mechanical engineer", "electrical engineer",
    "financial analyst", "teacher", "nurse", "chef", "logistics",
}

# Engineering / ML titles that fit the role directly.
CORE_ENGINEER_TITLES = {
    "ai engineer", "ml engineer", "machine learning engineer",
    "senior machine learning", "applied scientist", "research engineer",
    "nlp engineer", "search engineer", "relevance engineer",
    "recommendation engineer", "mlops engineer", "ai/ml engineer",
}

# Adjacent engineering titles - good if backed by ML evidence in history.
ADJACENT_ENGINEER_TITLES = {
    "data scientist", "backend engineer", "software engineer",
    "data engineer", "platform engineer", "full stack", "fullstack",
    "staff engineer", "principal engineer", "lead engineer", "sde",
    "analytics engineer",
}

# ---------------------------------------------------------------------------
# 4. Company-type signal. The JD down-weights "only worked at consulting firms
#    (TCS, Infosys, Wipro, Accenture, Cognizant, Capgemini, etc.) entire career"
#    and rewards product-company experience.
# ---------------------------------------------------------------------------
CONSULTING_COMPANIES = {
    "tcs", "tata consultancy", "infosys", "wipro", "accenture", "cognizant",
    "capgemini", "hcl", "tech mahindra", "mindtree", "mphasis", "ltimindtree",
    "lti", "l&t infotech", "igate", "hexaware", "birlasoft", "deloitte",
    "pwc", "kpmg", "ernst & young", "ey ", "ibm global", "dxc", "ntt data",
    "persistent", "zensar", "coforge", "cybage",
}

# ---------------------------------------------------------------------------
# 5. Location. JD: Pune/Noida preferred; Hyderabad, Mumbai, Delhi NCR, Bangalore
#    welcome; outside India case-by-case, no visa sponsorship.
# ---------------------------------------------------------------------------
PREFERRED_CITIES = {"pune", "noida"}
WELCOME_CITIES = {
    "hyderabad", "mumbai", "delhi", "new delhi", "gurgaon", "gurugram",
    "ncr", "bangalore", "bengaluru", "ghaziabad", "faridabad",
}

# ---------------------------------------------------------------------------
# 6. Experience band. JD: 5-9 years, ideal 6-8, of which 4-5 in applied ML at
#    product companies. Strong penalty below 3, mild above 12.
# ---------------------------------------------------------------------------
EXPERIENCE_BAND = {
    "ideal_min": 6.0,
    "ideal_max": 8.0,
    "soft_min": 5.0,
    "soft_max": 9.0,
    "hard_floor": 2.5,   # below this, almost certainly junior for a "Senior" role
    "hard_ceiling": 14.0,
}

# Job-hopping / title-chasing: JD explicitly rejects "switching companies every
# 1.5 years" optimizing for titles. Average tenure below this -> penalty.
SHORT_TENURE_MONTHS = 20

# Behavioural availability: JD says a perfect-on-paper candidate inactive for
# 6 months with a 5% response rate is "not actually available".
INACTIVE_DAYS_HARD = 180     # ~6 months
LOW_RESPONSE_RATE = 0.15
