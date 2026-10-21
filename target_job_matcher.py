"""
Targeted Job Matcher for Developers in Nepal & India.
Specializes in matching candidate resumes with remote LinkedIn postings
that specifically accept developers located in Nepal, India, or Worldwide.
"""

import asyncio
import logging
import re
from typing import Dict, List, Optional, Any, Tuple
from linkedin_scraper import scraper

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("TargetJobMatcher")

# Regional keywords and cities for India and Nepal
INDIAN_LOCATIONS = {
    "india", "bengaluru", "bangalore", "pune", "delhi", "new delhi", "hyderabad",
    "mumbai", "noida", "gurgaon", "gurugram", "chennai", "kolkata", "ahmedabad",
    "kerala", "kochi", "indore", "jaipur"
}

NEPALI_LOCATIONS = {
    "nepal", "kathmandu", "lalitpur", "bhaktapur", "pokhara", "biratnagar", "chitwan"
}

# Negative patterns indicating strict geographical restrictions
EXCLUSION_PATTERNS = [
    r"\b(?:must|need to)\s+be\s+(?:located|based|resident)\s+in\s+the\s+(?:us|usa|united states|uk|canada|europe|eu)\b",
    r"\b(?:us|united states)\s+(?:citizens?|green card|permanent resident)\s+only\b",
    r"\b(?:only|strictly)\s+(?:us|uk|eu|canada)\s+(?:candidates|applicants|residents)\b",
    r"\b(?:authorized|eligible)\s+to\s+work\s+in\s+the\s+(?:us|united states)\s+without\s+sponsorship\b",
    r"\b(?:us|eu|uk)\s+work\s+authorization\s+required\b",
    r"\bno\s+(?:visa\s+sponsorship|international\s+applicants)\b",
    r"\blatam\s+only\b",
    r"\bcanada\s+only\b"
]

POSITIVE_GLOBAL_PATTERNS = [
    r"\bwork\s+from\s+anywhere\b",
    r"\bworldwide\b",
    r"\bglobal\s+remote\b",
    r"\banywhere\s+in\s+the\s+world\b",
    r"\bany\s+timezone\b",
    r"\bopen\s+to\s+(?:international|global|worldwide|apac|india|nepal)\b",
    r"\b(?:contractor|b2b)\s+worldwide\b",
    r"\bindia\s+or\s+nepal\b",
    r"\bapac\s+timezone\b"
]


class TargetJobMatcher:
    """
    Intelligent matcher for finding remote LinkedIn jobs accepting developers from Nepal and India.
    """

    @classmethod
    def generate_targeted_queries(cls, profile: Dict[str, Any]) -> List[str]:
        """
        Derives high-signal search queries from candidate's skills and experience.
        """
        skills = [s.lower() for s in profile.get("skills", [])]
        queries = []

        # 1. Primary combination: Python + FastAPI / AI
        if "python" in skills and "fastapi" in skills:
            queries.append("Python FastAPI")
        elif "python" in skills:
            queries.append("Python Developer")

        # 2. AI / LLM / RAG specialized query
        if any(s in skills for s in ["llms", "rag", "ai agents", "generative ai"]):
            queries.append("Python AI LLM")

        # 3. Web Scraping / Automation
        if "web scraping" in skills or "data pipelines" in skills:
            queries.append("Python Web Scraping")

        # 4. Backend Engineer general query
        if "backend engineer" in [r.lower() for r in profile.get("target_roles", [])]:
            queries.append("Backend Engineer Python")
        elif profile.get("primary_role"):
            queries.append(f"{profile['primary_role']} Python")

        # Fallbacks
        if not queries:
            queries = ["Python Developer", "Backend Engineer"]

        # Limit to top 3-4 distinct queries to balance rate limits and diversity
        return list(dict.fromkeys(queries))[:3]

    @classmethod
    def evaluate_geo_eligibility(
        cls,
        location_str: str,
        description: str = "",
        target_countries: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Verifies if a remote position accepts candidates residing in India or Nepal.
        """
        loc_lower = (location_str or "").lower()
        desc_lower = (description or "").lower()

        # Check for strict exclusion clauses
        for pat in EXCLUSION_PATTERNS:
            if re.search(pat, desc_lower):
                return {
                    "is_eligible": False,
                    "status": "RESTRICTED",
                    "badge": "🚫 Restricted (US/EU Only)",
                    "badge_color": "#ef4444",
                    "reason": "Requires US/EU work authorization or strict local residency."
                }

        # Check if explicitly in Nepal
        is_nepal = any(nl in loc_lower for nl in NEPALI_LOCATIONS)
        if is_nepal:
            return {
                "is_eligible": True,
                "status": "ACCEPTED_NEPAL",
                "badge": "🇳🇵 Nepal Remote",
                "badge_color": "#10b981",
                "reason": "Remote position based in Nepal - Directly hires Nepali developers."
            }

        # Check if explicitly in India
        is_india = any(il in loc_lower for il in INDIAN_LOCATIONS)
        if is_india:
            return {
                "is_eligible": True,
                "status": "ACCEPTED_INDIA",
                "badge": "🇮🇳 India Remote",
                "badge_color": "#06b6d4",
                "reason": "Remote position based in India - Directly hires Indian/Nepali developers."
            }

        # Check for Worldwide / Global Remote signals
        is_worldwide = "worldwide" in loc_lower or "anywhere" in loc_lower or "remote" in loc_lower
        has_positive_global = any(re.search(pat, desc_lower) for pat in POSITIVE_GLOBAL_PATTERNS)

        if is_worldwide or has_positive_global:
            return {
                "is_eligible": True,
                "status": "ACCEPTED_WORLDWIDE",
                "badge": "🌍 Worldwide Remote (Accepts IN/NP)",
                "badge_color": "#8b5cf6",
                "reason": "Global remote position open to developers anywhere in the world."
            }

        # Ambiguous location
        return {
            "is_eligible": True,
            "status": "CHECK_REQUIRED",
            "badge": "🌐 Remote (Location Check)",
            "badge_color": "#64748b",
            "reason": f"Remote position in {location_str}."
        }

    @classmethod
    def calculate_match_score(
        cls,
        profile: Dict[str, Any],
        job: Dict[str, Any],
        geo_result: Dict[str, Any]
    ) -> Tuple[int, List[str], List[str]]:
        """
        Calculates match score (0-100%) and reasons for fit.
        """
        candidate_skills = profile.get("skills", [])
        job_title = job.get("title", "").lower()
        job_desc = (job.get("description", "") + " " + job.get("excerpt", "")).lower()
        job_tags = [t.lower() for t in job.get("tags", [])]

        matched_skills = []
        for skill in candidate_skills:
            pattern = r"\b" + re.escape(skill.lower()) + r"\b"
            if re.search(pattern, job_desc) or re.search(pattern, job_title) or any(re.search(pattern, t) for t in job_tags):
                matched_skills.append(skill)

        # 1. Skill Score (up to 55 points)
        if candidate_skills:
            skill_ratio = len(matched_skills) / min(len(candidate_skills), 8)
            skill_score = min(int(skill_ratio * 55), 55)
        else:
            skill_score = 30

        # Essential core skills boost (Python & FastAPI)
        if "Python" in matched_skills:
            skill_score += 5
        if "FastAPI" in matched_skills:
            skill_score += 5

        # 2. Title & Role Score (up to 25 points)
        title_score = 0
        primary_role = profile.get("primary_role", "").lower()
        target_roles = [r.lower() for r in profile.get("target_roles", [])]

        if any(role_word in job_title for role in target_roles for role_word in role.split()):
            title_score += 15
        if "python" in job_title:
            title_score += 10
        elif "backend" in job_title or "software" in job_title:
            title_score += 5

        # 3. Geo-Eligibility Boost (up to 15 points)
        geo_score = 0
        if geo_result.get("status") in ["ACCEPTED_NEPAL", "ACCEPTED_INDIA"]:
            geo_score = 15
        elif geo_result.get("status") == "ACCEPTED_WORLDWIDE":
            geo_score = 10
        elif not geo_result.get("is_eligible"):
            return 0, [], ["Excluded: Position requires US/local work authorization."]

        # 4. Seniority fit (up to 5 points)
        seniority_score = 5
        # If job is Senior/Lead and candidate is Junior, small adjustment
        if ("senior" in job_title or "lead" in job_title) and profile.get("seniority") == "Junior / Entry-Level":
            seniority_score = 2

        total_score = min(skill_score + title_score + geo_score + seniority_score, 100)

        # Build Fit Reasons
        reasons = []
        if matched_skills:
            reasons.append(f"Matches {len(matched_skills)} key skills: {', '.join(matched_skills[:4])}")
        reasons.append(geo_result.get("reason", "Remote position."))
        if "fastapi" in [s.lower() for s in matched_skills]:
            reasons.append("Specifically requires FastAPI expertise.")

        return total_score, matched_skills, reasons

    @classmethod
    async def match_resume_to_target_jobs(
        cls,
        profile: Dict[str, Any],
        locations: Optional[List[str]] = None,
        time_filter: str = "month",
        max_results: int = 30,
        min_score: int = 25
    ) -> Dict[str, Any]:
        """
        End-to-end pipeline:
        1. Generates targeted queries from candidate profile
        2. Scrapes LinkedIn for Nepal, India, and Worldwide remote roles
        3. Filters for geographical eligibility (Nepal & India developers)
        4. Scores and ranks postings by relevance
        """
        if not locations:
            locations = ["Nepal", "India"]

        queries = cls.generate_targeted_queries(profile)
        logger.info(f"Generated queries for candidate {profile.get('candidate_name')}: {queries}")

        scraped_jobs: List[Dict[str, Any]] = []
        seen_ids = set()

        # Scrape concurrently across locations & queries with politeness delays
        for loc in locations:
            for q in queries:
                if len(scraped_jobs) >= max_results * 2:
                    break

                try:
                    logger.info(f"Target scraping LinkedIn: query='{q}', location='{loc}', remote=True...")
                    batch = await scraper.scrape_jobs_async(
                        keywords=q,
                        location=loc,
                        remote_only=True,
                        time_filter=time_filter,
                        limit=8,
                        fetch_details=True
                    )
                    for j in batch:
                        jid = j.get("id") or j.get("job_id")
                        if jid and jid not in seen_ids:
                            seen_ids.add(jid)
                            scraped_jobs.append(j)

                    # Short politeness sleep between queries
                    await asyncio.sleep(0.4)

                except Exception as e:
                    logger.warning(f"Error fetching batch '{q}' in '{loc}': {e}")

        logger.info(f"Scraped {len(scraped_jobs)} raw candidate jobs. Evaluating and ranking...")

        # Evaluate eligibility and score each job
        ranked_jobs = []
        for j in scraped_jobs:
            geo_eval = cls.evaluate_geo_eligibility(
                j.get("location", ""),
                j.get("description", "")
            )

            # Skip restricted jobs
            if not geo_eval.get("is_eligible"):
                continue

            score, matched_skills, reasons = cls.calculate_match_score(profile, j, geo_eval)
            if score >= min_score:
                job_card = dict(j)
                job_card["match_score"] = score
                job_card["matched_skills"] = matched_skills
                job_card["matched_skills_count"] = len(matched_skills)
                job_card["fit_reasons"] = reasons
                job_card["geo_badge"] = geo_eval["badge"]
                job_card["geo_badge_color"] = geo_eval["badge_color"]
                job_card["geo_status"] = geo_eval["status"]
                ranked_jobs.append(job_card)

        # Sort by match score descending
        ranked_jobs.sort(key=lambda x: x["match_score"], reverse=True)
        final_jobs = ranked_jobs[:max_results]

        logger.info(f"Successfully matched and ranked {len(final_jobs)} jobs for {profile.get('candidate_name')}.")

        return {
            "status": "success",
            "candidate_name": profile.get("candidate_name", "Developer"),
            "primary_role": profile.get("primary_role"),
            "skills": profile.get("skills", []),
            "generated_queries": queries,
            "target_locations": locations,
            "total_matches": len(final_jobs),
            "jobs": final_jobs
        }


def main():
    import argparse
    import json
    from resume_analyzer import ResumeParser, ResumeAnalyzer

    parser = argparse.ArgumentParser(description="Targeted Remote LinkedIn Job Matcher (Nepal & India)")
    parser.add_argument("-r", "--resume", type=str, required=True, help="Path to resume file (PDF, DOCX, TXT)")
    parser.add_argument("-l", "--locations", type=str, default="Nepal,India", help="Comma-separated target locations (default: Nepal,India)")
    parser.add_argument("-w", "--worldwide", action="store_true", help="Include worldwide / global remote jobs")
    parser.add_argument("-t", "--time-filter", type=str, default="month", choices=["24h", "week", "month", "any"], help="Posting timeframe")
    parser.add_argument("-n", "--limit", type=int, default=15, help="Maximum number of matches to display")
    parser.add_argument("-o", "--output", type=str, help="Save matches to JSON file")

    args = parser.parse_args()

    # Read and parse resume
    with open(args.resume, "rb") as f:
        file_bytes = f.read()

    text = ResumeParser.extract_text(file_bytes, args.resume)
    profile = ResumeAnalyzer.analyze_resume(text)

    locs = [loc.strip() for loc in args.locations.split(",") if loc.strip()]
    if args.worldwide and "Worldwide" not in locs:
        locs.append("Worldwide")

    print(f"\n========================================================")
    print(f"🎯 Targeted Remote LinkedIn Matcher for Nepal & India")
    print(f"========================================================")
    print(f"Candidate:  {profile.get('candidate_name')} ({profile.get('seniority')})")
    print(f"Role:       {profile.get('primary_role')}")
    print(f"Top Skills: {', '.join(profile.get('skills', [])[:8])}")
    print(f"Locations:  {', '.join(locs)}")
    print(f"========================================================\n")

    result = asyncio.run(
        TargetJobMatcher.match_resume_to_target_jobs(
            profile=profile,
            locations=locs,
            time_filter=args.time_filter,
            max_results=args.limit
        )
    )

    print(f"✅ Found {result['total_matches']} matching postings for {profile.get('candidate_name')}:\n")
    for i, j in enumerate(result["jobs"], 1):
        sal = f" | 💰 {j['salary']}" if j.get("has_salary") else ""
        print(f"[{i:02d}] {j['match_score']}% FIT | {j['geo_badge']}")
        print(f"     Title:   {j['title']} @ {j['company']}")
        print(f"     Location: {j['location']}{sal}")
        print(f"     Apply:   {j['apply_url']}")
        if j.get("matched_skills"):
            print(f"     Matched: {', '.join(j['matched_skills'][:6])}")
        if j.get("fit_reasons"):
            print(f"     Why Fit: {j['fit_reasons'][0]}")
        print()

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"📁 Results exported to: {args.output}\n")


if __name__ == "__main__":
    main()
