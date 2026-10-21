import os
from typing import Optional
from fastapi import FastAPI, Query, HTTPException, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from job_aggregator import aggregator
from resume_analyzer import ResumeParser, ResumeAnalyzer, JobMatchingEngine

app = FastAPI(
    title="Remote Job Hub & AI Resume Matcher",
    description="Multi-source real-time job aggregation engine with instant resume analysis and personalized ranking",
    version="1.1.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure static folder exists
static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)

# Mount static assets
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/", include_in_schema=False)
async def serve_index():
    index_file = os.path.join(static_dir, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return JSONResponse({"status": "Frontend not yet built. Visit /api/jobs"})


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "remote-job-aggregator",
        "cached_jobs": len(aggregator._cached_jobs)
    }


@app.get("/api/providers")
async def get_providers():
    """Returns all integrated job providers with their brand colors and homepages."""
    return {
        "providers": aggregator.get_providers_info()
    }


@app.get("/api/stats")
async def get_stats():
    """Returns aggregator cache and source statistics."""
    return aggregator.get_stats()


@app.get("/api/jobs")
async def get_jobs(
    q: Optional[str] = Query(None, description="Search keyword in title, company, description, or tags"),
    provider: Optional[str] = Query("all", description="Filter by provider: RemoteOK, Himalayas, Jobicy, Arbeitnow, Remotive, LinkedIn, or all"),
    remote_only: bool = Query(True, description="Filter remote positions only"),
    salary_only: bool = Query(False, description="Filter positions with disclosed salary"),
    refresh: bool = Query(False, description="Force re-fetch from upstream sources"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(24, ge=1, le=100, description="Jobs per page")
):
    """
    Search and filter jobs across 6 live sources concurrently (including LinkedIn).
    """
    try:
        jobs = await aggregator.search_async(
            keyword=q,
            provider=provider,
            remote_only=remote_only,
            salary_only=salary_only,
            force_refresh=refresh
        )

        total_count = len(jobs)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_jobs = jobs[start_idx:end_idx]

        return {
            "query": q,
            "provider": provider,
            "total": total_count,
            "page": page,
            "page_size": page_size,
            "total_pages": (total_count + page_size - 1) // page_size if total_count else 0,
            "stats": aggregator.get_stats(),
            "jobs": paginated_jobs
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/resume/analyze")
async def analyze_resume(
    file: Optional[UploadFile] = File(None),
    raw_text: Optional[str] = Form(None)
):
    """
    Analyzes an uploaded resume (PDF, DOCX, TXT) or raw text.
    Extracts candidate name, years of experience, seniority, skills, and target roles.
    """
    try:
        text = ""
        filename = "pasted_resume.txt"

        if file:
            filename = file.filename
            content = await file.read()
            text = ResumeParser.extract_text(content, filename)
        elif raw_text:
            text = raw_text.strip()
        else:
            raise HTTPException(status_code=400, detail="Please upload a resume file (PDF, DOCX) or provide resume text.")

        if not text or len(text) < 30:
            raise HTTPException(status_code=400, detail="Could not extract readable text from resume. Ensure the file is not an empty or password-protected document.")

        profile = ResumeAnalyzer.analyze_resume(text)
        return {
            "status": "success",
            "filename": filename,
            "profile": profile
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to analyze resume: {str(e)}")


@app.post("/api/resume/match")
async def match_resume_to_jobs(
    file: Optional[UploadFile] = File(None),
    raw_text: Optional[str] = Form(None),
    provider: Optional[str] = Form("all"),
    salary_only: bool = Form(False),
    min_score: int = Form(20)
):
    """
    Upload resume -> Analyzes skills & experience -> Ranks all aggregated live jobs by relevance score.
    """
    try:
        text = ""
        filename = "pasted_resume.txt"

        if file:
            filename = file.filename
            content = await file.read()
            text = ResumeParser.extract_text(content, filename)
        elif raw_text:
            text = raw_text.strip()
        else:
            raise HTTPException(status_code=400, detail="Please upload a resume file (PDF, DOCX) or provide resume text.")

        # 1. Parse Candidate Profile
        profile = ResumeAnalyzer.analyze_resume(text)

        # 2. Fetch all aggregated live jobs
        all_jobs = await aggregator.search_async(
            keyword=None,
            provider=provider,
            remote_only=True,
            salary_only=salary_only,
            force_refresh=False
        )

        # 3. Score and rank jobs
        ranked_jobs = JobMatchingEngine.match_jobs(profile, all_jobs, min_score=min_score)

        return {
            "status": "success",
            "filename": filename,
            "profile": profile,
            "total_matches": len(ranked_jobs),
            "jobs": ranked_jobs
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to match resume to jobs: {str(e)}")


@app.post("/api/resume/linkedin-target-match")
async def match_resume_linkedin_target(
    file: Optional[UploadFile] = File(None),
    raw_text: Optional[str] = Form(None),
    locations: str = Form("Nepal,India"),
    include_worldwide: bool = Form(True),
    time_filter: str = Form("month"),
    max_results: int = Form(30),
    min_score: int = Form(20)
):
    """
    Dedicated endpoint for personal matching:
    Uploads resume -> parses skills, experience, and target roles
    -> searches live LinkedIn remote positions specifically accepting Nepal & India developers
    -> performs geo-eligibility screening & computes relevance fit score.
    """
    try:
        from target_job_matcher import TargetJobMatcher
        text = ""
        filename = "pasted_resume.txt"

        if file:
            filename = file.filename
            content = await file.read()
            text = ResumeParser.extract_text(content, filename)
        elif raw_text:
            text = raw_text.strip()
        else:
            raise HTTPException(status_code=400, detail="Please upload a resume file (PDF, DOCX) or provide resume text.")

        profile = ResumeAnalyzer.analyze_resume(text)
        
        target_locs = [l.strip() for l in locations.split(",") if l.strip()]
        if include_worldwide and "Worldwide" not in target_locs:
            target_locs.append("Worldwide")

        result = await TargetJobMatcher.match_resume_to_target_jobs(
            profile=profile,
            locations=target_locs,
            time_filter=time_filter,
            max_results=max_results,
            min_score=min_score
        )
        result["filename"] = filename
        result["profile"] = profile
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Target matching failed: {str(e)}")


@app.post("/api/refresh")
async def trigger_refresh():
    """Forces an immediate cache refresh from all upstream providers."""
    jobs = await aggregator.refresh_cache_async(force=True)
    return {
        "status": "refreshed",
        "total_jobs": len(jobs),
        "stats": aggregator.get_stats()
    }


@app.get("/api/linkedin/jobs")
async def get_linkedin_jobs(
    keywords: str = Query("software engineer", description="Search terms for LinkedIn jobs"),
    location: str = Query("Remote", description="Location or Remote"),
    remote_only: bool = Query(True, description="Filter for remote jobs"),
    time_filter: str = Query("24h", description="Time filter: 24h, week, month, or any"),
    limit: int = Query(25, ge=1, le=100, description="Max jobs to fetch"),
    fetch_details: bool = Query(False, description="Fetch detailed job descriptions and criteria")
):
    """
    Direct endpoint to scrape the latest LinkedIn jobs on-demand.
    Uses credentials from environment (LINKEDIN_EMAIL / LINKEDIN_PASSWORD)
    with resilient fallback.
    """
    try:
        from linkedin_scraper import scraper
        jobs = await scraper.scrape_jobs_async(
            keywords=keywords,
            location=location,
            remote_only=remote_only,
            time_filter=time_filter,
            limit=limit,
            fetch_details=fetch_details
        )
        return {
            "source": "LinkedIn",
            "keywords": keywords,
            "location": location,
            "remote_only": remote_only,
            "time_filter": time_filter,
            "total": len(jobs),
            "jobs": jobs
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LinkedIn scraper error: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
