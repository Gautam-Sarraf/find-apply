"""
LinkedIn Job Scraper Module & CLI
Supports both authenticated session login (using LINKEDIN_EMAIL & LINKEDIN_PASSWORD / li_at cookie)
and resilient live public Jobs API scraping with full details, company logos, and salary parsing.
"""

import os
import sys
import asyncio
import re
import html
import json
import time
import argparse
import logging
from typing import List, Dict, Optional, Any
from urllib.parse import urlencode, quote_plus
from dotenv import load_dotenv
import httpx
from bs4 import BeautifulSoup

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("LinkedInScraper")

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Sec-Ch-Ua": '"Chromium";v="123", "Not:A-Brand";v="8"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"macOS"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1"
}


def clean_html(raw_html: Optional[str]) -> str:
    """Removes scripts/tags and collapses whitespace for clean text excerpts."""
    if not raw_html:
        return ""
    clean = re.sub(r"<(script|style).*?>.*?</\1>", "", raw_html, flags=re.DOTALL | re.IGNORECASE)
    clean = re.sub(r"<[^>]+>", " ", clean)
    clean = html.unescape(clean)
    return re.sub(r"\s+", " ", clean).strip()


def extract_salary_from_text(text: str) -> Optional[str]:
    """Detects salary patterns like $120,000 - $160,000 or $50/hr or $100k+ in text."""
    if not text:
        return None
    patterns = [
        r"(\$\s*\d{2,3}(?:,\d{3})*(?:\.\d+)?\s*(?:-|to)\s*\$\s*\d{2,3}(?:,\d{3})*(?:\.\d+)?\s*(?:/(?:yr|year|hr|hour|mo|month)|a year|per year)?)",
        r"(\$\s*\d{2,3}k\s*(?:-|to)\s*\$\s*\d{2,3}k)",
        r"(\$\s*\d{2,3}(?:,\d{3})*(?:\.\d+)?\s*(?:/(?:yr|year|hr|hour)|per hour|a year))",
        r"((?:€|£)\s*\d{2,3}(?:,\d{3})*(?:\.\d+)?\s*(?:-|to)\s*(?:€|£)?\s*\d{2,3}(?:,\d{3})*)"
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return None


class LinkedInScraper:
    """
    Scraper for LinkedIn Job Postings with credentials management and resilient multi-mode scraping.
    """
    BASE_SEARCH_URL = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
    JOB_DETAIL_URL = "https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}"

    def __init__(
        self,
        email: Optional[str] = None,
        password: Optional[str] = None,
        li_at_cookie: Optional[str] = None
    ):
        self.email = email or os.getenv("LINKEDIN_EMAIL")
        self.password = password or os.getenv("LINKEDIN_PASSWORD")
        self.li_at_cookie = li_at_cookie or os.getenv("LINKEDIN_LI_AT")
        self.api_client = None
        self._auth_status = "unauthenticated"
        self._init_auth()

    def _init_auth(self):
        """Attempts authenticated session login if credentials exist."""
        if not (self.email and self.password) and not self.li_at_cookie:
            logger.info("No LinkedIn credentials found. Running in resilient public guest mode.")
            return

        try:
            from linkedin_api import Linkedin
            logger.info(f"Attempting authenticated LinkedIn session for {self.email}...")
            
            # If user provided li_at cookie, use that directly
            if self.li_at_cookie:
                self.api_client = Linkedin("", "", cookies={"li_at": self.li_at_cookie})
                self._auth_status = "authenticated_cookie"
                logger.info("Successfully initialized LinkedIn session via session cookie (li_at).")
                return

            # Attempt email + password authentication
            try:
                self.api_client = Linkedin(self.email, self.password, refresh_cookies=True)
                self._auth_status = "authenticated_creds"
                logger.info("Successfully authenticated LinkedIn API session.")
            except Exception as e:
                err_msg = str(e)
                if "CHALLENGE" in err_msg or "ChallengeException" in str(type(e)):
                    logger.warning(
                        "LinkedIn triggered an interactive security challenge (checkpoint/CAPTCHA/OTP). "
                        "Switching smoothly to resilient guest jobs scraper."
                    )
                else:
                    logger.warning(f"LinkedIn login failed: {e}. Switching to resilient guest jobs scraper.")
                self.api_client = None
                self._auth_status = "fallback_guest"
        except ImportError:
            logger.warning("linkedin-api package not installed. Using direct HTTP scraper.")
            self._auth_status = "fallback_guest"

    async def fetch_job_detail_async(
        self,
        client: httpx.AsyncClient,
        job_id: str,
        semaphore: Optional[asyncio.Semaphore] = None
    ) -> Dict[str, Any]:
        """Fetches full job description, criteria tags, and details for a specific posting."""
        url = self.JOB_DETAIL_URL.format(job_id=job_id)
        if semaphore:
            async with semaphore:
                return await self._fetch_job_detail_request(client, url, job_id)
        return await self._fetch_job_detail_request(client, url, job_id)

    async def _fetch_job_detail_request(self, client: httpx.AsyncClient, url: str, job_id: str) -> Dict[str, Any]:
        try:
            await asyncio.sleep(0.15)  # Politeness jitter
            resp = await client.get(url, timeout=9.0)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                
                # Extract Description
                desc_elem = soup.find("div", class_="show-more-less-html__markup") or \
                            soup.find("div", class_="description__text")
                raw_desc = str(desc_elem) if desc_elem else ""
                clean_desc = clean_html(raw_desc)
                
                # Extract criteria badges (Seniority, Employment type, Industry)
                criteria_items = soup.find_all("li", class_="description__job-criteria-item")
                tags = []
                for item in criteria_items:
                    val_elem = item.find("span")
                    if val_elem:
                        val = val_elem.get_text(strip=True)
                        if val and val != "Not Applicable" and val not in tags:
                            tags.append(val)

                # Detect salary in description
                salary = extract_salary_from_text(clean_desc)

                return {
                    "description": raw_desc,
                    "excerpt": clean_desc[:260] + "..." if clean_desc else "",
                    "tags": tags,
                    "salary": salary
                }
            elif resp.status_code == 429:
                logger.debug(f"LinkedIn detail rate limit (429) on job {job_id}; keeping card snippet.")
        except Exception as e:
            logger.debug(f"Failed to fetch detail for job {job_id}: {e}")
        return {"description": "", "excerpt": "", "tags": [], "salary": None}

    async def scrape_jobs_async(
        self,
        keywords: Optional[str] = "software engineer",
        location: Optional[str] = "Remote",
        remote_only: bool = True,
        time_filter: str = "24h",  # '24h', 'week', 'month', 'any'
        limit: int = 25,
        fetch_details: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Scrapes live LinkedIn job postings matching keywords and filters.
        """
        jobs: List[Dict[str, Any]] = []
        batch_size = 25
        max_start = max(batch_size, limit)

        # Build time filter parameter: f_TPR
        tpr_map = {
            "24h": "r86400",
            "today": "r86400",
            "week": "r604800",
            "month": "r2592000"
        }
        tpr_val = tpr_map.get(time_filter.lower()) if time_filter else None

        async with httpx.AsyncClient(headers=DEFAULT_HEADERS, follow_redirects=True, timeout=14.0) as client:
            for start in range(0, max_start, batch_size):
                if len(jobs) >= limit:
                    break

                params = {
                    "keywords": keywords or "",
                    "location": location or "",
                    "start": start
                }
                if remote_only:
                    params["f_WT"] = "2"  # 2 = Remote on LinkedIn
                if tpr_val:
                    params["f_TPR"] = tpr_val

                url = f"{self.BASE_SEARCH_URL}?{urlencode(params)}"
                logger.info(f"Querying LinkedIn job search (start={start}, query='{keywords}')...")

                try:
                    resp = await client.get(url)
                    if resp.status_code != 200:
                        logger.warning(f"LinkedIn search returned status code {resp.status_code}")
                        break

                    soup = BeautifulSoup(resp.text, "html.parser")
                    cards = soup.find_all("li")
                    if not cards:
                        # Try finding by card container
                        cards = soup.find_all("div", class_="base-card")

                    if not cards:
                        logger.info("No more job cards returned from LinkedIn.")
                        break

                    for card in cards:
                        if len(jobs) >= limit:
                            break

                        # Title & Link
                        title_elem = card.find("h3", class_=lambda x: x and "title" in x) or \
                                     card.find("a", class_=lambda x: x and "title" in x)
                        link_elem = card.find("a", class_=lambda x: x and ("link" in x or "title" in x))
                        
                        raw_link = link_elem.get("href", "") if link_elem else ""
                        clean_link = raw_link.split("?")[0] if raw_link else ""
                        
                        # Extract Job ID
                        job_id_match = re.search(r"view/.*?(\d{7,})", raw_link) or re.search(r"(\d{8,})", raw_link)
                        job_id = job_id_match.group(1) if job_id_match else str(abs(hash(clean_link)))

                        title = title_elem.get_text(strip=True) if title_elem else "Open Role"

                        # Company
                        company_elem = card.find(["h4", "a"], class_=lambda x: x and "subtitle" in x)
                        company = company_elem.get_text(strip=True) if company_elem else "Confidential"

                        # Location
                        loc_elem = card.find("span", class_=lambda x: x and "location" in x)
                        loc_str = loc_elem.get_text(strip=True) if loc_elem else ("Remote" if remote_only else "Worldwide")

                        # Logo
                        img_elem = card.find("img")
                        logo_url = ""
                        if img_elem:
                            logo_url = img_elem.get("data-delayed-url") or img_elem.get("src") or ""

                        # Date
                        time_elem = card.find("time")
                        date_str = ""
                        if time_elem:
                            date_str = time_elem.get("datetime") or time_elem.get_text(strip=True)

                        # Salary from card badge if present
                        salary_elem = card.find("span", class_=lambda x: x and "salary" in x)
                        card_salary = salary_elem.get_text(strip=True) if salary_elem else None

                        job_item = {
                            "source": "LinkedIn",
                            "source_color": "#0a66c2",
                            "id": f"linkedin-{job_id}",
                            "job_id": job_id,
                            "title": title,
                            "company": company,
                            "company_logo": logo_url,
                            "location": loc_str,
                            "is_remote": remote_only or "remote" in loc_str.lower(),
                            "salary": card_salary or "Not specified",
                            "has_salary": bool(card_salary),
                            "apply_url": clean_link or f"https://www.linkedin.com/jobs/view/{job_id}",
                            "tags": ["LinkedIn", "Remote" if remote_only else "On-site"],
                            "date": date_str,
                            "description": "",
                            "excerpt": f"{title} at {company} ({loc_str})"
                        }
                        jobs.append(job_item)

                except Exception as e:
                    logger.error(f"Error requesting LinkedIn jobs batch: {e}")
                    break

            # Concurrently fetch detailed description and tags if requested
            if fetch_details and jobs:
                logger.info(f"Fetching detailed job descriptions and criteria for {len(jobs)} postings...")
                sem = asyncio.Semaphore(2)
                detail_tasks = [
                    self.fetch_job_detail_async(client, j["job_id"], semaphore=sem)
                    for j in jobs
                ]
                detail_results = await asyncio.gather(*detail_tasks, return_exceptions=True)

                for job, det in zip(jobs, detail_results):
                    if isinstance(det, dict) and det.get("description"):
                        job["description"] = det["description"]
                        if det.get("excerpt"):
                            job["excerpt"] = det["excerpt"]
                        if det.get("tags"):
                            # Append extra criteria tags
                            for t in det["tags"]:
                                if t not in job["tags"]:
                                    job["tags"].append(t)
                        if not job["has_salary"] and det.get("salary"):
                            job["salary"] = det["salary"]
                            job["has_salary"] = True

        logger.info(f"Scraped {len(jobs)} total LinkedIn job postings.")
        return jobs

    def scrape_jobs(
        self,
        keywords: Optional[str] = "software engineer",
        location: Optional[str] = "Remote",
        remote_only: bool = True,
        time_filter: str = "24h",
        limit: int = 25,
        fetch_details: bool = True
    ) -> List[Dict[str, Any]]:
        """Synchronous wrapper for scrape_jobs_async."""
        import asyncio
        return asyncio.run(
            self.scrape_jobs_async(
                keywords=keywords,
                location=location,
                remote_only=remote_only,
                time_filter=time_filter,
                limit=limit,
                fetch_details=fetch_details
            )
        )


# Singleton instance using environment variables
scraper = LinkedInScraper()


def main():
    parser = argparse.ArgumentParser(description="LinkedIn Latest Job Postings Scraper")
    parser.add_argument("-k", "--keywords", type=str, default="software engineer", help="Job search keywords")
    parser.add_argument("-l", "--location", type=str, default="Remote", help="Location (e.g. Remote, United States, Europe)")
    parser.add_argument("-n", "--limit", type=int, default=20, help="Maximum number of jobs to fetch")
    parser.add_argument("--no-remote", action="store_true", help="Include non-remote/on-site positions")
    parser.add_argument("-t", "--time-filter", type=str, default="24h", choices=["24h", "week", "month", "any"], help="Filter by posting date")
    parser.add_argument("-o", "--output", type=str, help="Output file path (JSON or CSV)")
    parser.add_argument("--no-details", action="store_true", help="Skip fetching full descriptions for faster speed")

    args = parser.parse_args()

    print(f"\n💼 LinkedIn Job Scraper")
    print(f"==================================================")
    print(f"Keywords:    {args.keywords}")
    print(f"Location:    {args.location}")
    print(f"Remote Only: {not args.no_remote}")
    print(f"Time Filter: {args.time_filter}")
    print(f"Target Count: {args.limit}")
    print(f"Credentials: {scraper.email or 'None'} (Status: {scraper._auth_status})")
    print(f"==================================================\n")

    t0 = time.time()
    jobs = scraper.scrape_jobs(
        keywords=args.keywords,
        location=args.location,
        remote_only=not args.no_remote,
        time_filter=args.time_filter,
        limit=args.limit,
        fetch_details=not args.no_details
    )
    elapsed = time.time() - t0

    print(f"\n✅ Retrieved {len(jobs)} jobs in {elapsed:.2f}s\n")
    for i, j in enumerate(jobs, 1):
        sal = f" | 💰 {j['salary']}" if j["has_salary"] else ""
        date_badge = f" ({j['date']})" if j.get("date") else ""
        print(f"[{i:02d}] {j['title']} @ {j['company']}")
        print(f"     📍 {j['location']}{sal}{date_badge}")
        print(f"     🔗 {j['apply_url']}")
        if j.get("tags"):
            print(f"     🏷️  {', '.join(j['tags'][:5])}")
        print()

    if args.output:
        out_path = os.path.abspath(args.output)
        if args.output.lower().endswith(".csv"):
            import csv
            with open(out_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=["id", "title", "company", "location", "is_remote", "salary", "date", "apply_url", "excerpt"],
                    extrasaction="ignore"
                )
                writer.writeheader()
                writer.writerows(jobs)
        else:
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(jobs, f, indent=2, ensure_ascii=False)
        print(f"📁 Results exported to: {out_path}")


if __name__ == "__main__":
    import asyncio
    main()
