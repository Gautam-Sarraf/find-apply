"""
Targeted Job Matcher for Developers in Nepal & India.
Specializes in matching candidate resumes with remote LinkedIn postings
that specifically accept developers located in Nepal, India, or Worldwide.
"""

import asyncio
import logging
import re
from typing import Dict, List, Optional, Any, Tuple
import httpx
from linkedin_scraper import scraper, DEFAULT_HEADERS

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("TargetJobMatcher")

# Regional keywords and cities for India and Nepal
INDIAN_LOCATIONS = {
    "india", "bengaluru", "bangalore", "pune", "delhi", "new delhi", "hyderabad",
    "mumbai", "noida", "gurgaon", "gurugram", "chennai", "kolkata", "ahmedabad",
    "kerala", "kochi", "indore", "jaipur"
}

NEPALI_LOCATIONS = {
    "nepal", "kathmandu", "lalitpur", "bhaktapur", "pokhara", "biratnagar", "chitwan", "butwal", "dharan"
}

US_LOCATIONS = {
    "united states", "us", "usa", "san francisco", "new york", "austin", "seattle", "boston",
    "los angeles", "california", "chicago", "denver", "colorado", "texas", "sunnyvale",
    "san jose", "palo alto", "cambridge", "portland", "atlanta", "remote in us"
}

UK_LOCATIONS = {
    "united kingdom", "uk", "london", "england", "manchester", "cambridge", "edinburgh",
    "bristol", "oxford", "birmingham", "leeds", "scotland"
}

STARTUP_PATTERNS = [
    r"\b(?:startup|seed|series\s+[a-d]|backed\s+by|y\s+combinator|yc|early[- ]stage|founding|stealth|scaleup|fast[- ]growing|venture|fintech|healthtech|ai\s+startup)\b"
]

OFFSHORE_GLOBAL_PATTERNS = [
    r"\b(?:hire|hiring|open\s+to|accepting|contractor|developers?|engineers?)\s+(?:in|from)\s+(?:india|nepal|asia|apac)\b",
    r"\b(?:india|nepal)\s+(?:remote|contractor|offshore|residents?)\b",
    r"\b(?:work|working)\s+(?:from\s+anywhere|worldwide|globally)\b",
    r"\b(?:deel|remote\.com|oyster|eor|international\s+contractor|b2b\s+contractor)\b",
    r"\bglobal\s+(?:remote|talent|team|workforce|engineering)\b",
    r"\bany\s+timezone\b",
    r"\bopen\s+to\s+(?:international|global|worldwide|apac|india|nepal)\b",
    r"\bdistributed\s+(?:team|engineering|workforce)\b",
    r"\boffshore\s+(?:team|engineers?|developers?)\b"
]

# Negative patterns indicating strict geographical restrictions
EXCLUSION_PATTERNS = [
    r"\b(?:us|united states|uk|canada|eu)\s+candidates?\s+only\b",
    r"\b(?:must|need to)\s+be\s+(?:located|based|resident)\s+in\s+the\s+(?:us|usa|united states|uk|canada|europe|eu)\b",
    r"\b(?:us|united states)\s+(?:citizens?|green card|permanent resident)\s+only\b",
    r"\b(?:only|strictly)\s+(?:us|uk|eu|canada)\s+(?:candidates|applicants|residents)\b",
    r"\b(?:authorized|eligible)\s+to\s+work\s+in\s+the\s+(?:us|united states)\s+without\s+sponsorship\b",
    r"\b(?:us|eu|uk)\s+work\s+authorization\s+required\b",
    r"\bno\s+(?:visa\s+sponsorship|international\s+applicants)\b",
    r"\blatam\s+only\b",
    r"\bcanada\s+only\b",
    r"\beu\s+only\b"
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
    Intelligent matcher for finding remote LinkedIn jobs accepting developers from Nepal and India,
    including US & UK startups hiring remotely from Nepal and India.
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

        return list(dict.fromkeys(queries))[:3]

    @classmethod
    def evaluate_geo_eligibility(
        cls,
        location_str: str,
        description: str = "",
        title_str: str = ""
    ) -> Dict[str, Any]:
        """
        Verifies if a remote position accepts candidates residing in India or Nepal,
        or is a US/UK startup hiring remotely from Nepal/India.
        """
        loc_lower = (location_str or "").lower()
        desc_lower = (description or "").lower()
        title_lower = (title_str or "").lower()
        combined_text = f"{title_lower} {loc_lower} {desc_lower}"

        # 1. Check for explicit positive Nepal/India/Offshore hiring signals first
        has_offshore_signal = any(re.search(pat, combined_text) for pat in OFFSHORE_GLOBAL_PATTERNS)

        # 2. Check for strict exclusion clauses (unless explicitly overridden by offshore/India/Nepal mentions)
        if not has_offshore_signal:
            for pat in EXCLUSION_PATTERNS:
                if re.search(pat, title_lower) or re.search(pat, desc_lower):
                    return {
                        "is_eligible": False,
                        "status": "RESTRICTED",
                        "badge": "Restricted (US/EU Only)",
                        "badge_color": "#ef4444",
                        "reason": "Requires US/EU work authorization or strict local residency."
                    }

        # 3. Check if explicitly in Nepal
        is_nepal = any(nl in loc_lower for nl in NEPALI_LOCATIONS) or ("nepal" in desc_lower and "remote" in desc_lower)
        if is_nepal:
            return {
                "is_eligible": True,
                "status": "ACCEPTED_NEPAL",
                "badge": "Nepal Remote",
                "badge_color": "#10b981",
                "reason": "Remote position based in Nepal - Directly hires Nepali developers."
            }

        # 4. Check if explicitly in India
        is_india = any(il in loc_lower for il in INDIAN_LOCATIONS) or ("india" in desc_lower and "remote" in desc_lower)
        if is_india:
            return {
                "is_eligible": True,
                "status": "ACCEPTED_INDIA",
                "badge": "India Remote",
                "badge_color": "#06b6d4",
                "reason": "Remote position based in India - Directly hires Indian/Nepali developers."
            }

        # 5. Check if US Startup hiring remotely (specifically open to Nepal/India/Contractors)
        is_us = any(u in loc_lower for u in US_LOCATIONS) or "united states" in loc_lower
        is_startup = any(re.search(pat, desc_lower) for pat in STARTUP_PATTERNS) or "startup" in combined_text

        if is_us:
            if has_offshore_signal or ("india" in desc_lower or "nepal" in desc_lower):
                return {
                    "is_eligible": True,
                    "status": "ACCEPTED_US_STARTUP",
                    "badge": "US Startup • Remote IN/NP",
                    "badge_color": "#2563eb",
                    "reason": "US startup actively hiring remote engineers in Nepal & India."
                }
            if is_startup or any(re.search(pat, desc_lower) for pat in POSITIVE_GLOBAL_PATTERNS):
                return {
                    "is_eligible": True,
                    "status": "ACCEPTED_US_STARTUP",
                    "badge": "US Startup • Global Remote",
                    "badge_color": "#3b82f6",
                    "reason": "US-based startup offering remote role (open to global/contractor applicants in Nepal & India)."
                }
            # General US remote with no hard exclusion
            return {
                "is_eligible": True,
                "status": "ACCEPTED_US_STARTUP",
                "badge": "US Remote",
                "badge_color": "#3b82f6",
                "reason": "US remote position (open to global contractors/applicants)."
            }

        # 6. Check if UK Startup hiring remotely
        is_uk = any(u in loc_lower for u in UK_LOCATIONS) or "united kingdom" in loc_lower
        if is_uk:
            if has_offshore_signal or ("india" in desc_lower or "nepal" in desc_lower):
                return {
                    "is_eligible": True,
                    "status": "ACCEPTED_UK_STARTUP",
                    "badge": "UK Startup • Remote IN/NP",
                    "badge_color": "#4f46e5",
                    "reason": "UK startup actively hiring remote engineers in Nepal & India."
                }
            return {
                "is_eligible": True,
                "status": "ACCEPTED_UK_STARTUP",
                "badge": "UK Startup • Global Remote",
                "badge_color": "#6366f1",
                "reason": "UK startup offering remote role (open to global/contractor applicants in Nepal & India)."
            }

        # 7. Check for Worldwide / Global Remote signals
        is_worldwide = "worldwide" in loc_lower or "anywhere" in loc_lower or "remote" in loc_lower
        has_positive_global = any(re.search(pat, desc_lower) for pat in POSITIVE_GLOBAL_PATTERNS)

        if is_worldwide or has_positive_global:
            return {
                "is_eligible": True,
                "status": "ACCEPTED_WORLDWIDE",
                "badge": "Worldwide Remote",
                "badge_color": "#8b5cf6",
                "reason": "Global remote position open to developers anywhere in the world."
            }

        # 8. Ambiguous/General Remote
        return {
            "is_eligible": True,
            "status": "ACCEPTED_GLOBAL",
            "badge": "Global Remote",
            "badge_color": "#0ea5e9",
            "reason": f"Remote position in {location_str} (open to international applicants)."
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
        status = geo_result.get("status")
        if status in ["ACCEPTED_NEPAL", "ACCEPTED_INDIA", "ACCEPTED_US_STARTUP", "ACCEPTED_UK_STARTUP"]:
            geo_score = 15
        elif status == "ACCEPTED_WORLDWIDE":
            geo_score = 12
        elif status == "ACCEPTED_GLOBAL":
            geo_score = 8
        elif not geo_result.get("is_eligible"):
            return 0, [], ["Excluded: Position requires US/local work authorization."]

        # 4. Seniority fit (up to 5 points)
        seniority_score = 5
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
        include_worldwide: bool = True,
        include_us_startups: bool = True,
        include_uk_startups: bool = True,
        time_filter: str = "month",
        max_results: int = 35,
        min_score: int = 20
    ) -> Dict[str, Any]:
        """
        End-to-end pipeline:
        1. Generates targeted queries from candidate profile
        2. Scrapes LinkedIn across:
           - Nepal Remote
           - India Remote
           - US Startups hiring remotely from Nepal/India
           - UK Startups hiring remotely from Nepal/India
           - Worldwide Remote
        3. Screens for geographical eligibility and startup remote fit
        4. Scores and ranks postings by relevance
        """
        if locations is None:
            locations = ["Nepal", "India"]

        queries = cls.generate_targeted_queries(profile)
        primary_q = queries[0] if queries else "Python Developer"
        secondary_q = queries[1] if len(queries) > 1 else primary_q
        logger.info(f"Target matching for {profile.get('candidate_name')} with queries: {queries}")

        # Construct specific search channel tasks
        search_tasks = []
        channel_labels = []

        # 1. Nepal Remote Channel
        if any("nepal" in loc.lower() for loc in locations):
            search_tasks.append(
                scraper.scrape_jobs_async(
                    keywords="Python remote",
                    location="Nepal",
                    remote_only=True,
                    time_filter=time_filter,
                    limit=8,
                    fetch_details=False
                )
            )
            channel_labels.append("Nepal")

        # 2. India Remote Channel
        if any("india" in loc.lower() for loc in locations):
            search_tasks.append(
                scraper.scrape_jobs_async(
                    keywords=primary_q,
                    location="India",
                    remote_only=True,
                    time_filter=time_filter,
                    limit=10,
                    fetch_details=False
                )
            )
            channel_labels.append("India")

        # 3. US Startups Channel (Hiring Remote IN/NP)
        if include_us_startups or any("united states" in loc.lower() or "us" in loc.lower() for loc in locations):
            # Query A: Startup remote in US
            search_tasks.append(
                scraper.scrape_jobs_async(
                    keywords=f"{primary_q} startup remote",
                    location="United States",
                    remote_only=True,
                    time_filter=time_filter,
                    limit=8,
                    fetch_details=False
                )
            )
            channel_labels.append("US Startup Remote")
            # Query B: US remote explicitly hiring India/Nepal
            search_tasks.append(
                scraper.scrape_jobs_async(
                    keywords=f"{primary_q} remote India",
                    location="United States",
                    remote_only=True,
                    time_filter=time_filter,
                    limit=8,
                    fetch_details=False
                )
            )
            channel_labels.append("US Hiring India/Nepal")

        # 4. UK Startups Channel (Hiring Remote IN/NP)
        if include_uk_startups or any("united kingdom" in loc.lower() or "uk" in loc.lower() for loc in locations):
            search_tasks.append(
                scraper.scrape_jobs_async(
                    keywords=f"{primary_q} startup remote",
                    location="United Kingdom",
                    remote_only=True,
                    time_filter=time_filter,
                    limit=8,
                    fetch_details=False
                )
            )
            channel_labels.append("UK Startup Remote")

        # 5. Worldwide Remote Channel
        if include_worldwide or any("worldwide" in loc.lower() for loc in locations):
            search_tasks.append(
                scraper.scrape_jobs_async(
                    keywords=f"{secondary_q} remote",
                    location="Worldwide",
                    remote_only=True,
                    time_filter=time_filter,
                    limit=8,
                    fetch_details=False
                )
            )
            channel_labels.append("Worldwide Remote")

        logger.info(f"Dispatching concurrent LinkedIn searches across {len(search_tasks)} channels: {channel_labels}")
        results = await asyncio.gather(*search_tasks, return_exceptions=True)

        scraped_jobs: List[Dict[str, Any]] = []
        seen_ids = set()

        for label, batch in zip(channel_labels, results):
            if isinstance(batch, list):
                logger.info(f"Channel '{label}' returned {len(batch)} jobs.")
                for j in batch:
                    jid = j.get("id") or j.get("job_id")
                    if jid and jid not in seen_ids:
                        seen_ids.add(jid)
                        scraped_jobs.append(j)
            else:
                logger.warning(f"Channel '{label}' encountered error: {batch}")

        logger.info(f"Scraped {len(scraped_jobs)} distinct postings across all channels. Enriching details...")

        # Concurrently fetch detailed job descriptions and criteria for evaluation
        if scraped_jobs:
            candidate_skills = [s.lower() for s in profile.get("skills", [])]
            def prelim_rank(j):
                t = j.get("title", "").lower()
                return sum(1 for s in candidate_skills if s in t) + (2 if "python" in t else 0)

            scraped_jobs.sort(key=prelim_rank, reverse=True)
            jobs_to_enrich = scraped_jobs[:24]

            sem = asyncio.Semaphore(2)
            async with httpx.AsyncClient(headers=DEFAULT_HEADERS, follow_redirects=True, timeout=12.0) as client:
                detail_tasks = [
                    scraper.fetch_job_detail_async(client, j["job_id"], semaphore=sem)
                    for j in jobs_to_enrich
                ]
                detail_results = await asyncio.gather(*detail_tasks, return_exceptions=True)
                for job, det in zip(jobs_to_enrich, detail_results):
                    if isinstance(det, dict) and det.get("description"):
                        job["description"] = det["description"]
                        if det.get("excerpt"):
                            job["excerpt"] = det["excerpt"]
                        if det.get("tags"):
                            for t in det["tags"]:
                                if t not in job["tags"]:
                                    job["tags"].append(t)
                        if not job.get("has_salary") and det.get("salary"):
                            job["salary"] = det["salary"]
                            job["has_salary"] = True

        # Evaluate eligibility and score each job
        ranked_jobs = []
        for j in scraped_jobs:
            geo_eval = cls.evaluate_geo_eligibility(
                location_str=j.get("location", ""),
                description=j.get("description", ""),
                title_str=j.get("title", "")
            )

            # Skip restricted jobs (US/EU only without global remote/contractor options)
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

        logger.info(f"Successfully matched and ranked {len(final_jobs)} jobs for {profile.get('candidate_name')} (including US/UK startups).")

        return {
            "status": "success",
            "candidate_name": profile.get("candidate_name", "Developer"),
            "primary_role": profile.get("primary_role"),
            "skills": profile.get("skills", []),
            "generated_queries": queries,
            "target_channels": channel_labels,
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
    print(f"Targeted Remote LinkedIn Matcher for Nepal & India")
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

    print(f"Found {result['total_matches']} matching postings for {profile.get('candidate_name')}:\n")
    for i, j in enumerate(result["jobs"], 1):
        sal = f" | {j['salary']}" if j.get("has_salary") else ""
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
        print(f"Results exported to: {args.output}\n")


if __name__ == "__main__":
    main()
