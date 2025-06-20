from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
import httpx
from langchain.prompts import PromptTemplate
from typing import Optional, List, Dict
import asyncio
import json
import sys
import subprocess

app = FastAPI()

class StartupInfo(BaseModel):
    name: str
    niche: str
    traction: str
    goals: str
    extra_info: Optional[str] = ""

class InvestorInfo(BaseModel):
    name: str
    bio: Optional[str] = ""
    interests: Optional[str] = ""
    linkedin: Optional[str] = ""
    notable_investments: Optional[str] = ""
    location: Optional[str] = ""

class PitchRequest(BaseModel):
    startup: StartupInfo
    investor: InvestorInfo
    tone: Optional[str] = "professional"
    feedback: Optional[bool] = True

class InvestorSearchRequest(BaseModel):
    keywords: str  # e.g. "investor venture capital site:linkedin.com/in"
    num_results: int = 5

class InvestorEnrichRequest(BaseModel):
    linkedin_url: str

class AutoEnrichRequest(BaseModel):
    name: str
    location: Optional[str] = None
    keywords: Optional[str] = None  # extra keywords for search

# --- Enhanced Prompt Template ---
pitch_template = PromptTemplate(
    input_variables=[
        "startup_name", "startup_niche", "startup_traction", "startup_goals", "startup_extra_info",
        "investor_name", "investor_bio", "investor_interests", "investor_linkedin", "investor_notable_investments", "investor_location"
    ],
    template=(
        "You are an expert startup advisor. Write a personalized investor pitch email for the startup '{startup_name}'. "
        "The pitch is for {investor_name}. Use the following context about the investor to personalize the email. "
        "Their bio is: '{investor_bio}'. They are interested in: '{investor_interests}'. "
        "LinkedIn: {investor_linkedin}. Notable investments: {investor_notable_investments}. Location: {investor_location}.\n\n"
        "Make sure the email includes: "
        "1. A strong 1-liner hook after the greeting. "
        "2. A line about why this investor is a fit, using their bio, interests, investments, and location. "
        "3. A brief explanation of the unique tech. "
        "4. A breakdown of how the funding will be used. "
        "5. A specific call-to-action (e.g., a 15-minute call next week).\n\n"
        "---\n"
        "STARTUP DETAILS:\n"
        "Niche: {startup_niche}\n"
        "Traction: {startup_traction}\n"
        "Goals: {startup_goals}\n"
        "Additional Info: {startup_extra_info}\n"
        "---\n\n"
        "INVESTOR PITCH EMAIL:"
    )
)

SERPAPI_KEY = os.getenv("SERPAPI_KEY")
PROXYCURL_KEY = os.getenv("PROXYCURL_KEY")
if not SERPAPI_KEY:
    raise RuntimeError("SERPAPI_KEY not set in environment variables.")

@app.post("/search_investors")
async def search_investors(req: InvestorSearchRequest):
    params = {
        "engine": "google",
        "q": req.keywords,
        "api_key": SERPAPI_KEY,
        "num": req.num_results
    }
    async with httpx.AsyncClient() as client:
        response = await client.get("https://serpapi.com/search", params=params)
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail=f"SerpAPI Google Search error: {response.text}")
        data = response.json()
        linkedin_results = []
        crunchbase_results = []
        for item in data.get("organic_results", [])[:req.num_results * 2]:  # scan more for both types
            link = item.get("link", "")
            title = item.get("title", "")
            snippet = item.get("snippet", "")
            if "linkedin.com/in" in link:
                linkedin_results.append({"title": title, "url": link, "snippet": snippet})
            elif "crunchbase.com" in link:
                crunchbase_results.append({"title": title, "url": link, "snippet": snippet})
            # Stop if we have enough of both
            if len(linkedin_results) >= req.num_results and len(crunchbase_results) >= req.num_results:
                break
        return {
            "linkedin": linkedin_results[:req.num_results],
            "crunchbase": crunchbase_results[:req.num_results]
        }

@app.post("/enrich_investor")
async def enrich_investor(req: InvestorEnrichRequest):
    params = {
        "engine": "linkedin_profile",
        "url": req.linkedin_url,
        "api_key": SERPAPI_KEY
    }
    async with httpx.AsyncClient() as client:
        response = await client.get("https://serpapi.com/search", params=params)
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail=f"SerpAPI LinkedIn Profile error: {response.text}")
        data = response.json()
        profile = data.get("linkedin_profile", {})
        return {
            "name": profile.get("name", ""),
            "bio": profile.get("about", ""),
            "interests": ", ".join(profile.get("interests", [])) if profile.get("interests") else "",
            "linkedin": req.linkedin_url,
            "notable_investments": ", ".join(profile.get("featured", [])) if profile.get("featured") else "",
            "location": profile.get("location", "")
        }

@app.post("/auto_enrich_investor")
async def auto_enrich_investor(req: AutoEnrichRequest):
    # Step 1: Use SerpAPI to find LinkedIn URL
    search_keywords = req.keywords or f'{req.name} investor site:linkedin.com/in'
    if req.location:
        search_keywords += f' {req.location}'
    params = {
        "engine": "google",
        "q": search_keywords,
        "api_key": SERPAPI_KEY,
        "num": 1
    }
    async with httpx.AsyncClient() as client:
        response = await client.get("https://serpapi.com/search", params=params)
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail=f"SerpAPI Google Search error: {response.text}")
        data = response.json()
        linkedin_url = None
        snippet = ""
        for item in data.get("organic_results", []):
            link = item.get("link", "")
            if "linkedin.com/in" in link:
                linkedin_url = link
                snippet = item.get("snippet", "")
                break
        if not linkedin_url:
            raise HTTPException(status_code=404, detail="No LinkedIn profile found for this name.")

    # Step 2: Use SerpAPI to search Crunchbase for the same name
    crunchbase_bio = ""
    notable_investments = ""
    cb_params = {
        "engine": "google",
        "q": f'{req.name} site:crunchbase.com',
        "api_key": SERPAPI_KEY,
        "num": 1
    }
    async with httpx.AsyncClient() as client:
        cb_response = await client.get("https://serpapi.com/search", params=cb_params)
        if cb_response.status_code == 200:
            cb_data = cb_response.json()
            for item in cb_data.get("organic_results", []):
                link = item.get("link", "")
                if "crunchbase.com" in link:
                    crunchbase_bio = item.get("snippet", "")
                    # Try to extract notable investments from the snippet
                    # e.g. "Notable investments include Uber, Twitter, AngelList."
                    import re
                    match = re.search(r'Notable investments? (include|includes|such as|:)? ([^.]+)', crunchbase_bio, re.IGNORECASE)
                    if match:
                        notable_investments = match.group(2).strip()
                    break

    # Step 3: Try Proxycurl for LinkedIn enrichment if key is set
    if PROXYCURL_KEY:
        proxycurl_url = "https://nubela.co/proxycurl/api/v2/linkedin"  # Free tier supports this endpoint
        headers = {"Authorization": f"Bearer {PROXYCURL_KEY}"}
        params = {"url": linkedin_url, "use_cache": "if-present"}
        async with httpx.AsyncClient() as client:
            resp = await client.get(proxycurl_url, headers=headers, params=params)
            if resp.status_code == 200:
                pdata = resp.json()
                return {
                    "name": pdata.get("full_name", req.name),
                    "bio": pdata.get("summary", snippet),
                    "interests": ", ".join(pdata.get("activities", [])) if pdata.get("activities") else "",
                    "linkedin": linkedin_url,
                    "notable_investments": notable_investments or (", ".join(pdata.get("experiences", [{}])[0].get("notable_investments", [])) if pdata.get("experiences") else ""),
                    "location": pdata.get("city", ""),
                    "crunchbase_bio": crunchbase_bio
                }
            # If Proxycurl fails, fallback to snippet
    # Fallback: Use snippet from SerpAPI and Crunchbase
    return {
        "name": req.name,
        "bio": snippet,
        "interests": "",
        "linkedin": linkedin_url,
        "notable_investments": notable_investments,
        "location": "",
        "crunchbase_bio": crunchbase_bio
    }

@app.get("/")
def read_root():
    return {"message": "Backend is working!"}

@app.post("/generate")
async def generate_pitch(req: PitchRequest):
    s = req.startup
    i = req.investor
    tone = req.tone or "professional"
    feedback = req.feedback if req.feedback is not None else True
    prompt = pitch_template.format(
        startup_name=s.name,
        startup_niche=s.niche,
        startup_traction=s.traction,
        startup_goals=s.goals,
        startup_extra_info=s.extra_info or "",
        investor_name=i.name or "Investor",
        investor_bio=i.bio or "Not specified",
        investor_interests=i.interests or "Not specified",
        investor_linkedin=i.linkedin or "",
        investor_notable_investments=i.notable_investments or "",
        investor_location=i.location or ""
    )
    prompt += f"\n\nWrite the email in a {tone} tone."
    if feedback:
        prompt += ("\n---\n\nHow to make this email more effective?\n\n"
                   "Please focus on the email's content and structure. Avoid suggesting specific changes to the subject line or sender name.\n\n"
                   "1. Is the 1-liner hook effective in grabbing the investor's attention?\n"
                   "2. Is the explanation of why the investor is a fit for the startup clear and concise?\n"
                   "3. Is the unique tech explained in a way that resonates with the investor's interests and investments?\n"
                   "4. Is the breakdown of how the funding will be used clear and specific?\n"
                   "5. Is the call-to-action clear and direct?\n\n"
                   "Please provide constructive feedback and suggestions for improvement.")
    api_key = os.getenv("TOGETHER_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="Together API key not set.")
    url = "https://api.together.xyz/v1/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "meta-llama/Llama-3-8b-chat-hf",
        "prompt": prompt,
        "max_tokens": 700,
        "temperature": 0.7
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=payload)
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail=f"Together API error: {response.text}")
        data = response.json()
        return {"result": data.get("choices", [{}])[0].get("text", "")}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)