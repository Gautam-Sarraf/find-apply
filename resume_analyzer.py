import io
import re
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
import pypdf
import docx

# Comprehensive domain skill catalog
SKILL_TAXONOMY = {
    # Languages
    "python": "Python",
    "javascript": "JavaScript",
    "typescript": "TypeScript",
    "golang": "Go",
    "go": "Go",
    "java": "Java",
    "c++": "C++",
    "cpp": "C++",
    "c#": "C#",
    "csharp": "C#",
    "rust": "Rust",
    "ruby": "Ruby",
    "php": "PHP",
    "swift": "Swift",
    "kotlin": "Kotlin",
    "scala": "Scala",
    "r": "R",
    "sql": "SQL",
    "html": "HTML",
    "html5": "HTML5",
    "css": "CSS",
    "css3": "CSS3",
    "sass": "Sass",
    "bash": "Bash",
    "shell": "Shell",

    # Frontend Frameworks & Libraries
    "react": "React",
    "reactjs": "React",
    "react.js": "React",
    "next.js": "Next.js",
    "nextjs": "Next.js",
    "vue": "Vue.js",
    "vuejs": "Vue.js",
    "angular": "Angular",
    "svelte": "Svelte",
    "redux": "Redux",
    "tailwind": "Tailwind CSS",
    "tailwindcss": "Tailwind CSS",
    "bootstrap": "Bootstrap",

    # Backend Frameworks
    "fastapi": "FastAPI",
    "django": "Django",
    "flask": "Flask",
    "node": "Node.js",
    "nodejs": "Node.js",
    "node.js": "Node.js",
    "express": "Express",
    "expressjs": "Express",
    "nest": "NestJS",
    "nestjs": "NestJS",
    "spring": "Spring Boot",
    "spring boot": "Spring Boot",
    "ruby on rails": "Ruby on Rails",
    "rails": "Rails",
    "asp.net": "ASP.NET",
    "laravel": "Laravel",

    # Databases & Caching
    "postgresql": "PostgreSQL",
    "postgres": "PostgreSQL",
    "mysql": "MySQL",
    "mongodb": "MongoDB",
    "redis": "Redis",
    "sqlite": "SQLite",
    "elasticsearch": "Elasticsearch",
    "cassandra": "Cassandra",
    "dynamodb": "DynamoDB",
    "firestore": "Firestore",
    "supabase": "Supabase",
    "snowflake": "Snowflake",

    # Cloud & Infrastructure
    "aws": "AWS",
    "amazon web services": "AWS",
    "gcp": "Google Cloud",
    "google cloud": "Google Cloud",
    "azure": "Azure",
    "docker": "Docker",
    "kubernetes": "Kubernetes",
    "k8s": "Kubernetes",
    "terraform": "Terraform",
    "ansible": "Ansible",
    "ci/cd": "CI/CD",
    "jenkins": "Jenkins",
    "github actions": "GitHub Actions",
    "gitlab": "GitLab",
    "linux": "Linux",
    "nginx": "Nginx",
    "kafka": "Kafka",
    "rabbitmq": "RabbitMQ",

    # AI & Data
    "machine learning": "Machine Learning",
    "deep learning": "Deep Learning",
    "pytorch": "PyTorch",
    "tensorflow": "TensorFlow",
    "pandas": "Pandas",
    "numpy": "NumPy",
    "scikit-learn": "Scikit-Learn",
    "llm": "LLMs",
    "llms": "LLMs",
    "genai": "Generative AI",
    "generative ai": "Generative AI",
    "rag": "RAG",
    "ai agents": "AI Agents",
    "ai agent": "AI Agents",
    "nlp": "NLP",
    "computer vision": "Computer Vision",
    "data engineering": "Data Engineering",
    "data pipelines": "Data Pipelines",
    "data pipeline": "Data Pipelines",
    "web scraping": "Web Scraping",
    "scraping": "Web Scraping",
    "semantic search": "Semantic Search",
    "spark": "Apache Spark",
    "websockets": "WebSockets",
    "websocket": "WebSockets",
    "cron": "Cron Jobs",

    # Methodologies & Tools
    "git": "Git",
    "rest": "REST APIs",
    "rest api": "REST APIs",
    "rest apis": "REST APIs",
    "graphql": "GraphQL",
    "microservices": "Microservices",
    "agile": "Agile",
    "scrum": "Scrum",
    "tdd": "TDD",
    "testing": "Testing"
}

ROLE_DOMAINS = {
    "Full Stack Engineer": ["react", "node", "typescript", "javascript", "python", "full stack", "fullstack"],
    "Backend Engineer": ["python", "golang", "java", "fastapi", "django", "postgresql", "redis", "docker", "backend", "api"],
    "Frontend Engineer": ["react", "vue", "angular", "next.js", "typescript", "javascript", "css", "html", "tailwind", "frontend"],
    "DevOps / SRE": ["docker", "kubernetes", "k8s", "terraform", "aws", "gcp", "azure", "ci/cd", "linux", "devops", "sre"],
    "Data Scientist / ML Engineer": ["python", "machine learning", "pytorch", "tensorflow", "pandas", "data science", "llm", "ai"],
    "Data Engineer": ["python", "sql", "spark", "kafka", "snowflake", "etl", "data engineering"],
    "Mobile Developer": ["swift", "kotlin", "react native", "flutter", "ios", "android"],
    "Product Manager": ["product management", "roadmap", "agile", "scrum", "analytics", "product manager"]
}


class ResumeParser:
    @staticmethod
    def extract_text_from_pdf(file_bytes: bytes) -> str:
        text = ""
        try:
            reader = pypdf.PdfReader(io.BytesIO(file_bytes))
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
        except Exception as e:
            raise ValueError(f"Error reading PDF file: {e}")
        return text.strip()

    @staticmethod
    def extract_text_from_docx(file_bytes: bytes) -> str:
        text = ""
        try:
            doc = docx.Document(io.BytesIO(file_bytes))
            for p in doc.paragraphs:
                if p.text:
                    text += p.text + "\n"
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        if cell.text:
                            text += cell.text + " "
                    text += "\n"
        except Exception as e:
            raise ValueError(f"Error reading DOCX file: {e}")
        return text.strip()

    @staticmethod
    def extract_text(file_bytes: bytes, filename: str) -> str:
        ext = filename.lower().split(".")[-1]
        if ext == "pdf":
            return ResumeParser.extract_text_from_pdf(file_bytes)
        elif ext in ["docx", "doc"]:
            return ResumeParser.extract_text_from_docx(file_bytes)
        else:
            try:
                return file_bytes.decode("utf-8")
            except UnicodeDecodeError:
                return file_bytes.decode("latin-1", errors="ignore")


class ResumeAnalyzer:
    """
    Parses resume text into a structured candidate profile and scores job fit.
    """
    @classmethod
    def analyze_resume(cls, text: str) -> Dict[str, Any]:
        if not text or len(text.strip()) < 30:
            raise ValueError("Resume content is too short or could not be extracted.")

        lower_text = text.lower()

        # 1. Extract email & candidate name heuristic
        email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", text)
        email = email_match.group(0) if email_match else ""

        lines = [line.strip() for line in text.split("\n") if line.strip()]
        candidate_name = ""
        for line in lines[:5]:
            # If line is short and doesn't look like contact info
            if len(line) < 40 and not any(c in line for c in ["@", "http", "www", "+", "/"]) and re.search(r"[a-zA-Z]", line):
                candidate_name = line
                break
        if not candidate_name:
            candidate_name = "Candidate"

        # 2. Extract Skills
        detected_skills = set()
        for key, display_name in SKILL_TAXONOMY.items():
            pattern = r"\b" + re.escape(key) + r"\b"
            if re.search(pattern, lower_text):
                detected_skills.add(display_name)

        # 3. Detect Years of Experience
        years_exp = cls._detect_experience_years(text, lower_text)

        # 4. Determine Seniority Level
        seniority = cls._detect_seniority(years_exp, lower_text)

        # 5. Detect Primary Domains / Target Roles
        detected_roles = cls._detect_target_roles(detected_skills, lower_text)
        primary_title = detected_roles[0] if detected_roles else f"{seniority} Software Engineer"

        # 6. Education
        education = cls._detect_education(lower_text)

        return {
            "candidate_name": candidate_name,
            "email": email,
            "years_of_experience": years_exp,
            "seniority": seniority,
            "primary_role": primary_title,
            "target_roles": detected_roles,
            "skills": sorted(list(detected_skills)),
            "skills_count": len(detected_skills),
            "education": education,
            "summary": f"{seniority} professional with ~{years_exp} years of experience specializing in {', '.join(list(detected_skills)[:5]) if detected_skills else 'software development'}."
        }

    @classmethod
    def _detect_experience_years(cls, raw_text: str, lower_text: str) -> int:
        # Pattern 1: explicit mentions like "5+ years of experience", "3 years exp"
        exp_patterns = [
            r"(\d{1,2})\+?\s*(?:years|yrs|year)\s*(?:of)?\s*(?:experience|exp)",
            r"(?:experience|exp)\s*:\s*(\d{1,2})\+?\s*(?:years|yrs|year)",
            r"(?:over|more than)\s*(\d{1,2})\s*(?:years|yrs)"
        ]
        explicit_years = []
        for pat in exp_patterns:
            matches = re.findall(pat, lower_text)
            for m in matches:
                try:
                    val = int(m)
                    if 1 <= val <= 35:
                        explicit_years.append(val)
                except ValueError:
                    pass

        if explicit_years:
            return max(explicit_years)

        # Pattern 2: Year ranges like 2018 - 2024 or 2019 - Present
        current_year = datetime.now().year
        year_ranges = re.findall(r"\b(20[0-2][0-9]|199[0-9])\s*[-–—to]+\s*(present|current|now|20[0-2][0-9])\b", lower_text)
        total_span = 0
        earliest_start = current_year

        for start_str, end_str in year_ranges:
            try:
                start_yr = int(start_str)
                if end_str in ["present", "current", "now"]:
                    end_yr = current_year
                else:
                    end_yr = int(end_str)
                if start_yr <= end_yr and start_yr < earliest_start:
                    earliest_start = start_yr
            except ValueError:
                pass

        if earliest_start < current_year:
            calculated_span = current_year - earliest_start
            return min(max(calculated_span, 1), 30)

        return 3  # default standard mid-level estimate if indeterminate

    @classmethod
    def _detect_seniority(cls, years: int, text: str) -> str:
        if "lead" in text or "principal" in text or "staff" in text or years >= 8:
            if "principal" in text:
                return "Principal"
            if "lead" in text or years >= 10:
                return "Lead / Staff"
            return "Senior"
        elif "senior" in text or years >= 5:
            return "Senior"
        elif years <= 2 or "junior" in text or "entry level" in text or "intern" in text:
            return "Junior / Entry-Level"
        else:
            return "Mid-Level"

    @classmethod
    def _detect_target_roles(cls, detected_skills: set, lower_text: str) -> List[str]:
        skill_lower = {s.lower() for s in detected_skills}
        role_scores = []
        for role, keywords in ROLE_DOMAINS.items():
            matches = sum(1 for kw in keywords if kw in skill_lower or kw in lower_text)
            if matches > 0:
                role_scores.append((role, matches))

        role_scores.sort(key=lambda x: x[1], reverse=True)
        return [r[0] for r in role_scores[:3]]

    @classmethod
    def _detect_education(cls, text: str) -> str:
        if "phd" in text or "doctorate" in text:
            return "Ph.D. / Doctorate"
        elif "master" in text or "m.s." in text or "mba" in text:
            return "Master's Degree"
        elif "bachelor" in text or "b.s." in text or "b.tech" in text or "b.e." in text:
            return "Bachelor's Degree"
        return "Not specified"


class JobMatchingEngine:
    """
    Ranks and scores aggregated jobs against the parsed candidate profile.
    """
    @classmethod
    def match_jobs(
        cls,
        candidate_profile: Dict[str, Any],
        jobs: List[Dict[str, Any]],
        min_score: int = 15
    ) -> List[Dict[str, Any]]:
        candidate_skills = set(candidate_profile.get("skills", []))
        candidate_skills_lower = {s.lower() for s in candidate_skills}
        cand_years = candidate_profile.get("years_of_experience", 3)
        cand_seniority = candidate_profile.get("seniority", "Mid-Level")
        target_roles = [r.lower() for r in candidate_profile.get("target_roles", [])]

        matched_results = []

        for job in jobs:
            title = job.get("title", "")
            title_lower = title.lower()
            desc = job.get("description", "")
            desc_lower = desc.lower()
            tags = [str(t).lower() for t in job.get("tags", [])]

            # 1. Extract job skills
            job_skills = set()
            for key, display_name in SKILL_TAXONOMY.items():
                pattern = r"\b" + re.escape(key) + r"\b"
                if re.search(pattern, title_lower) or any(key in t for t in tags) or re.search(pattern, desc_lower):
                    job_skills.add(display_name)

            # Match overlap
            matched_skills = [s for s in job_skills if s in candidate_skills]
            missing_skills = [s for s in job_skills if s not in candidate_skills]

            # Skill Score (0 to 50 pts)
            if job_skills:
                skill_ratio = len(matched_skills) / len(job_skills)
                skill_score = min(50, int(skill_ratio * 40) + min(len(matched_skills) * 3, 15))
            else:
                # If job doesn't list explicit tags, check candidate skills in job description
                found_in_desc = [s for s in candidate_skills if s.lower() in desc_lower]
                matched_skills = found_in_desc[:6]
                skill_score = min(35, len(found_in_desc) * 7)

            # 2. Title & Role Alignment (0 to 35 pts)
            role_score = 0
            for r in target_roles:
                words = [w for w in r.split() if len(w) > 3]
                if any(w in title_lower for w in words):
                    role_score = 30
                    break
            if not role_score:
                if any(s.lower() in title_lower for s in candidate_skills):
                    role_score = 20
                elif "engineer" in title_lower or "developer" in title_lower:
                    role_score = 15

            # 3. Seniority & Experience Alignment (0 to 15 pts)
            exp_score = 10
            is_senior_job = any(w in title_lower for w in ["senior", "sr", "lead", "principal", "staff", "head"])
            is_junior_job = any(w in title_lower for w in ["junior", "jr", "entry", "associate", "intern"])

            if is_senior_job:
                if cand_years >= 5 or "Senior" in cand_seniority or "Lead" in cand_seniority:
                    exp_score = 15
                else:
                    exp_score = 5
            elif is_junior_job:
                if cand_years <= 3:
                    exp_score = 15
                else:
                    exp_score = 8
            else:
                exp_score = 12

            # Total Composite Match Score (0 - 100%)
            total_score = min(99, skill_score + role_score + exp_score)

            if total_score < min_score:
                continue

            # Generate human-readable fit reasons
            fit_reasons = []
            if matched_skills:
                fit_reasons.append(f"Matching core skills: {', '.join(matched_skills[:4])}")
            if is_senior_job and cand_years >= 5:
                fit_reasons.append(f"Senior role aligns with your {cand_years}+ years of experience")
            elif role_score >= 25:
                fit_reasons.append(f"Title strongly aligns with your target role ({candidate_profile.get('primary_role')})")
            if job.get("has_salary"):
                fit_reasons.append(f"Disclosed compensation: {job.get('salary')}")

            matched_results.append({
                **job,
                "match_score": total_score,
                "match_grade": "Excellent Match" if total_score >= 80 else ("Strong Match" if total_score >= 60 else "Good Match"),
                "matched_skills": matched_skills,
                "missing_skills": missing_skills[:5],
                "fit_reasons": fit_reasons
            })

        # Sort by highest match score
        matched_results.sort(key=lambda x: x["match_score"], reverse=True)
        return matched_results
