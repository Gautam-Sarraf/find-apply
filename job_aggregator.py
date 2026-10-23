import asyncio
import html
import json
import logging
import re
import time
from typing import List, Dict, Optional, Any
import httpx
from linkedin_scraper import parse_date_to_timestamp

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("JobAggregator")

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
}


def clean_html(raw_html: Optional[str]) -> str:
    """Removes script/style tags and basic HTML formatting for text search and clean excerpts."""
    if not raw_html:
        return ""
    # Strip script/style
    clean = re.sub(r"<(script|style).*?>.*?</\1>", "", raw_html, flags=re.DOTALL | re.IGNORECASE)
    # Strip HTML tags
    clean = re.sub(r"<[^>]+>", " ", clean)
    # Unescape entities
    clean = html.unescape(clean)
    # Collapse multiple whitespaces
    return re.sub(r"\s+", " ", clean).strip()


class JobProvider:
    NAME: str
    COLOR: str
    HOMEPAGE: str

    async def fetch_async(self, client: httpx.AsyncClient, limit: int = 50) -> List[Dict[str, Any]]:
        raise NotImplementedError


class RemoteOKProvider(JobProvider):
    NAME = "RemoteOK"
    COLOR = "#10b981"  # Emerald
    HOMEPAGE = "https://remoteok.com"
    URL = "https://remoteok.com/api"

    async def fetch_async(self, client: httpx.AsyncClient, limit: int = 50) -> List[Dict[str, Any]]:
        try:
            resp = await client.get(self.URL, timeout=12.0)
            if resp.status_code != 200:
                logger.warning(f"RemoteOK returned status {resp.status_code}")
                return []
            raw = resp.json()
            if not isinstance(raw, list):
                return []
            jobs_raw = [j for j in raw if isinstance(j, dict) and j.get("id")]
            results = []
            for j in jobs_raw[:limit]:
                sal_min = j.get("salary_min")
                sal_max = j.get("salary_max")
                salary_str = ""
                if sal_min and sal_max:
                    salary_str = f"${sal_min:,} - ${sal_max:,}"
                elif sal_min:
                    salary_str = f"From ${sal_min:,}"

                tags = [str(t).strip() for t in j.get("tags") or [] if t]

                results.append({
                    "source": self.NAME,
                    "source_color": self.COLOR,
                    "id": f"remoteok-{j.get('id')}",
                    "title": (j.get("position") or "").strip(),
                    "company": (j.get("company") or "").strip(),
                    "company_logo": j.get("company_logo") or j.get("logo") or "",
                    "location": j.get("location") or "Worldwide / Remote",
                    "is_remote": True,
                    "salary": salary_str or "Not specified",
                    "has_salary": bool(salary_str),
                    "apply_url": j.get("apply_url") or j.get("url") or "",
                    "tags": tags,
                    "date": j.get("date"),
                    "description": j.get("description", ""),
                    "excerpt": clean_html(j.get("description", ""))[:260] + "..."
                })
            return results
        except Exception as e:
            logger.error(f"RemoteOK fetch failed: {e}")
            return []


class HimalayasProvider(JobProvider):
    NAME = "Himalayas"
    COLOR = "#6366f1"  # Indigo
    HOMEPAGE = "https://himalayas.app"
    URL = "https://himalayas.app/jobs/api"

    async def fetch_async(self, client: httpx.AsyncClient, limit: int = 50) -> List[Dict[str, Any]]:
        try:
            resp = await client.get(self.URL, timeout=12.0)
            if resp.status_code != 200:
                logger.warning(f"Himalayas returned status {resp.status_code}")
                return []
            raw = resp.json()
            jobs_raw = raw.get("jobs", []) if isinstance(raw, dict) else []
            results = []
            for j in jobs_raw[:limit]:
                currency = j.get("currency") or "USD"
                min_sal = j.get("minSalary")
                max_sal = j.get("maxSalary")
                salary_str = ""
                if min_sal and max_sal:
                    salary_str = f"{currency} {min_sal:,} - {max_sal:,}"
                elif min_sal:
                    salary_str = f"{currency} {min_sal:,}+"

                tags = [str(t).strip() for t in j.get("categories") or [] if t]

                location_restrictions = j.get("locationRestrictions") or []
                location_str = ", ".join(location_restrictions) if location_restrictions else "Worldwide / Remote"

                desc = j.get("description") or j.get("excerpt") or ""

                results.append({
                    "source": self.NAME,
                    "source_color": self.COLOR,
                    "id": f"himalayas-{j.get('guid') or j.get('title', '')}",
                    "title": (j.get("title") or "").strip(),
                    "company": (j.get("companyName") or "").strip(),
                    "company_logo": j.get("companyLogo") or "",
                    "location": location_str,
                    "is_remote": True,
                    "salary": salary_str or "Not specified",
                    "has_salary": bool(salary_str),
                    "apply_url": j.get("applicationLink") or "",
                    "tags": tags,
                    "date": j.get("pubDate"),
                    "description": desc,
                    "excerpt": clean_html(desc)[:260] + "..."
                })
            return results
        except Exception as e:
            logger.error(f"Himalayas fetch failed: {e}")
            return []


class JobicyProvider(JobProvider):
    NAME = "Jobicy"
    COLOR = "#f59e0b"  # Amber
    HOMEPAGE = "https://jobicy.com"
    BASE_URL = "https://jobicy.com/api/v2/remote-jobs"

    async def fetch_async(self, client: httpx.AsyncClient, limit: int = 50) -> List[Dict[str, Any]]:
        try:
            url = f"{self.BASE_URL}?count={min(limit, 50)}"
            resp = await client.get(url, timeout=12.0)
            if resp.status_code != 200:
                logger.warning(f"Jobicy returned status {resp.status_code}")
                return []
            raw = resp.json()
            jobs_raw = raw.get("jobs", []) if isinstance(raw, dict) else []
            results = []
            for j in jobs_raw[:limit]:
                tags = []
                if j.get("jobIndustry"):
                    tags.append(str(j.get("jobIndustry")))
                if j.get("jobType"):
                    tags.append(str(j.get("jobType")))
                if j.get("jobLevel"):
                    tags.append(str(j.get("jobLevel")))

                desc = j.get("jobDescription") or j.get("jobExcerpt") or ""

                results.append({
                    "source": self.NAME,
                    "source_color": self.COLOR,
                    "id": f"jobicy-{j.get('id')}",
                    "title": (j.get("jobTitle") or "").strip(),
                    "company": (j.get("companyName") or "").strip(),
                    "company_logo": j.get("companyLogo") or "",
                    "location": j.get("jobGeo") or "Worldwide / Remote",
                    "is_remote": True,
                    "salary": "Not specified",
                    "has_salary": False,
                    "apply_url": j.get("url") or "",
                    "tags": tags,
                    "date": j.get("pubDate"),
                    "description": desc,
                    "excerpt": clean_html(desc)[:260] + "..."
                })
            return results
        except Exception as e:
            logger.error(f"Jobicy fetch failed: {e}")
            return []


class ArbeitnowProvider(JobProvider):
    NAME = "Arbeitnow"
    COLOR = "#38bdf8"  # Sky
    HOMEPAGE = "https://www.arbeitnow.com"
    URL = "https://www.arbeitnow.com/api/job-board-api"

    async def fetch_async(self, client: httpx.AsyncClient, limit: int = 50) -> List[Dict[str, Any]]:
        try:
            resp = await client.get(self.URL, timeout=12.0)
            if resp.status_code != 200:
                logger.warning(f"Arbeitnow returned status {resp.status_code}")
                return []
            raw = resp.json()
            jobs_raw = raw.get("data", []) if isinstance(raw, dict) else []
            results = []
            for j in jobs_raw:
                is_remote = bool(j.get("remote", False))
                tags = [str(t).strip() for t in j.get("tags") or [] if t]
                desc = j.get("description", "")

                results.append({
                    "source": self.NAME,
                    "source_color": self.COLOR,
                    "id": f"arbeitnow-{j.get('slug')}",
                    "title": (j.get("title") or "").strip(),
                    "company": (j.get("company_name") or "").strip(),
                    "company_logo": "",
                    "location": j.get("location") or ("Remote" if is_remote else "On-site"),
                    "is_remote": is_remote,
                    "salary": "Not specified",
                    "has_salary": False,
                    "apply_url": j.get("url") or "",
                    "tags": tags,
                    "date": j.get("created_at"),
                    "description": desc,
                    "excerpt": clean_html(desc)[:260] + "..."
                })
                if len(results) >= limit:
                    break
            return results
        except Exception as e:
            logger.error(f"Arbeitnow fetch failed: {e}")
            return []


class RemotiveProvider(JobProvider):
    NAME = "Remotive"
    COLOR = "#ec4899"  # Pink / Magenta
    HOMEPAGE = "https://remotive.com"
    URL = "https://remotive.com/api/remote-jobs"

    async def fetch_async(self, client: httpx.AsyncClient, limit: int = 15) -> List[Dict[str, Any]]:
        try:
            resp = await client.get(self.URL, timeout=12.0)
            if resp.status_code != 200:
                logger.warning(f"Remotive returned status {resp.status_code}")
                return []
            raw = resp.json()
            jobs_raw = raw.get("jobs", []) if isinstance(raw, dict) else []
            results = []
            for j in jobs_raw[:limit]:
                tags = [str(t).strip() for t in j.get("tags") or [] if t]
                if j.get("category") and j.get("category") not in tags:
                    tags.insert(0, str(j.get("category")))

                salary_str = (j.get("salary") or "").strip()
                desc = j.get("description", "")

                results.append({
                    "source": self.NAME,
                    "source_color": self.COLOR,
                    "id": f"remotive-{j.get('id')}",
                    "title": (j.get("title") or "").strip(),
                    "company": (j.get("company_name") or "").strip(),
                    "company_logo": j.get("company_logo") or j.get("company_logo_url") or "",
                    "location": j.get("candidate_required_location") or "Worldwide / Remote",
                    "is_remote": True,
                    "salary": salary_str or "Not specified",
                    "has_salary": bool(salary_str),
                    "apply_url": j.get("url") or "",
                    "tags": tags,
                    "date": j.get("publication_date"),
                    "description": desc,
                    "excerpt": clean_html(desc)[:260] + "..."
                })
            return results
        except Exception as e:
            logger.error(f"Remotive fetch failed: {e}")
            return []


class LinkedInProvider(JobProvider):
    NAME = "LinkedIn"
    COLOR = "#0a66c2"  # Official LinkedIn Blue
    HOMEPAGE = "https://www.linkedin.com/jobs"

    def __init__(self):
        from linkedin_scraper import scraper
        self.scraper = scraper

    async def fetch_async(self, client: httpx.AsyncClient, limit: int = 60) -> List[Dict[str, Any]]:
        try:
            # Scrape latest tech & remote postings via LinkedIn scraper
            jobs = await self.scraper.scrape_jobs_async(
                keywords="developer engineer",
                location="Remote",
                remote_only=True,
                time_filter="week",
                limit=limit,
                fetch_details=False
            )
            return jobs
        except Exception as e:
            logger.error(f"LinkedIn fetch failed: {e}")
            return []


class JobAggregator:
    """
    High-performance async job aggregator with in-memory TTL caching.
    """
    def __init__(self, cache_ttl_seconds: int = 300):
        self.providers: List[JobProvider] = [
            RemoteOKProvider(),
            HimalayasProvider(),
            JobicyProvider(),
            ArbeitnowProvider(),
            RemotiveProvider(),
            LinkedInProvider()
        ]
        self.cache_ttl = cache_ttl_seconds
        self._cached_jobs: List[Dict[str, Any]] = []
        self._last_fetch_time: float = 0
        self._lock = asyncio.Lock()

    def get_providers_info(self) -> List[Dict[str, str]]:
        return [
            {
                "name": p.NAME,
                "color": p.COLOR,
                "homepage": p.HOMEPAGE
            }
            for p in self.providers
        ]

    async def refresh_cache_async(self, force: bool = False) -> List[Dict[str, Any]]:
        async with self._lock:
            now = time.time()
            if not force and self._cached_jobs and (now - self._last_fetch_time) < self.cache_ttl:
                return self._cached_jobs

            logger.info("Fetching jobs concurrently from all 6 providers...")
            async with httpx.AsyncClient(headers=DEFAULT_HEADERS, timeout=14.0) as client:
                tasks = [p.fetch_async(client, limit=50) for p in self.providers]
                results = await asyncio.gather(*tasks, return_exceptions=True)

            all_jobs: List[Dict[str, Any]] = []
            for p, res in zip(self.providers, results):
                if isinstance(res, Exception):
                    logger.error(f"Provider {p.NAME} raised error: {res}")
                elif isinstance(res, list):
                    logger.info(f"Provider {p.NAME} returned {len(res)} jobs")
                    all_jobs.extend(res)

            # Deduplicate by normalized (company, title)
            seen = set()
            deduped = []
            for j in all_jobs:
                key = (j.get("company", "").strip().lower(), j.get("title", "").strip().lower())
                if key not in seen and key != ("", ""):
                    seen.add(key)
                    if not j.get("date_ts"):
                        j["date_ts"] = parse_date_to_timestamp(j.get("date"))
                    deduped.append(j)

            # Sort with latest postings on top
            deduped.sort(key=lambda x: x.get("date_ts", 0), reverse=True)

            self._cached_jobs = deduped
            self._last_fetch_time = time.time()
            logger.info(f"Cache updated with {len(deduped)} total unique jobs (sorted newest first)")
            return self._cached_jobs

    async def search_async(
        self,
        keyword: Optional[str] = None,
        provider: Optional[str] = None,
        remote_only: bool = True,
        salary_only: bool = False,
        force_refresh: bool = False
    ) -> List[Dict[str, Any]]:
        jobs = await self.refresh_cache_async(force=force_refresh)

        # Filter remote
        if remote_only:
            jobs = [j for j in jobs if j.get("is_remote", False)]

        # Filter provider
        if provider and provider.lower() != "all":
            jobs = [j for j in jobs if j.get("source", "").lower() == provider.lower()]

        # Filter salary
        if salary_only:
            jobs = [j for j in jobs if j.get("has_salary", False)]

        # Filter keyword
        if keyword:
            q = keyword.strip().lower()
            filtered = []
            for j in jobs:
                title_match = q in j.get("title", "").lower()
                company_match = q in j.get("company", "").lower()
                location_match = q in j.get("location", "").lower()
                desc_match = q in j.get("description", "").lower()
                tags_match = any(q in str(t).lower() for t in j.get("tags", []))

                if title_match or company_match or location_match or desc_match or tags_match:
                    filtered.append(j)
            jobs = filtered

        return jobs

    def get_stats(self) -> Dict[str, Any]:
        jobs = self._cached_jobs
        by_provider = {}
        with_salary = 0
        for j in jobs:
            src = j.get("source", "Unknown")
            by_provider[src] = by_provider.get(src, 0) + 1
            if j.get("has_salary"):
                with_salary += 1

        return {
            "total_jobs": len(jobs),
            "by_provider": by_provider,
            "with_salary": with_salary,
            "cache_age_seconds": int(time.time() - self._last_fetch_time) if self._last_fetch_time else 0,
            "last_updated": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(self._last_fetch_time)) if self._last_fetch_time else "Never"
        }


# Global singleton instance for app reuse
aggregator = JobAggregator(cache_ttl_seconds=300)

if __name__ == "__main__":
    async def main():
        print("Testing JobAggregator in async mode...")
        t0 = time.time()
        jobs = await aggregator.search_async(keyword="engineer", remote_only=True)
        print(f"Retrieved {len(jobs)} jobs in {time.time() - t0:.2f}s")
        for j in jobs[:5]:
            print(f"• [{j['source']}] {j['title']} @ {j['company']} ({j['location']}) - {j['salary']}")
        stats = aggregator.get_stats()
        print("\nAggregator stats:", stats)

    asyncio.run(main())
