import json
import os
import requests
from bs4 import BeautifulSoup
from agents.base_agent import BaseAgent
from database import Lead, Metric
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

HUNTER_API_KEY = os.getenv("HUNTER_API_KEY")

# Real target companies by industry — AI security buyers
TARGET_COMPANIES = {
    "IT": [
        "infosys.com", "wipro.com", "hcltech.com", "techmahindra.com",
        "mphasis.com", "hexaware.com", "mindtree.com", "persistent.com",
        "zensar.com", "cyient.com", "niit.com", "mastech.com"
    ],
    "Healthcare": [
        "apollohospitals.com", "fortishealthcare.com", "manipalhospitals.com",
        "narayanahealth.org", "maxhealthcare.in", "medanta.org",
        "carehosp.com", "aartihospitals.com"
    ],
    "Finance": [
        "hdfcbank.com", "icicibank.com", "axisbank.com", "kotakbank.com",
        "yesbank.in", "idfcfirstbank.com", "rblbank.com", "federalbank.co.in",
        "bajajfinserv.in", "muthootfinance.com"
    ],
    "R&D": [
        "drreddy.com", "sunpharma.com", "cipla.com", "lupin.com",
        "biocon.com", "divis.in", "aurobindo.com", "torrentpharma.com"
    ]
}

class ScoutAgent(BaseAgent):
    def __init__(self):
        super().__init__("Scout Agent", "Lead Finder")

    def search_leads(self, industry: str, country: str = "global", count: int = 10) -> list:
        self.log("search_leads", f"Searching {industry} companies")
        all_leads = []

        # 1. Hunter.io domain search on target companies
        domains = TARGET_COMPANIES.get(industry, TARGET_COMPANIES["IT"])
        self.log("hunter_search", f"Searching {len(domains)} domains via Hunter.io")

        for domain in domains[:6]:
            leads = self._hunter_domain_search(domain, industry)
            all_leads.extend(leads)
            if len(all_leads) >= count:
                break

        # 2. If still not enough, use AI to generate realistic leads
        if len(all_leads) < 3:
            self.log("ai_fallback", "Using AI fallback for lead generation")
            ai_leads = self._ai_generate_leads(industry, country, count)
            all_leads.extend(ai_leads)

        # 3. AI score all leads
        if all_leads:
            all_leads = self._ai_score_leads(all_leads[:count], industry)

        # 4. Save to DB
        saved = self._save_leads(all_leads[:count])
        self.log("search_leads", f"Saved {saved} leads for {industry}", "success")
        return all_leads[:count]

    def _hunter_domain_search(self, domain: str, industry: str) -> list:
        try:
            url = "https://api.hunter.io/v2/domain-search"
            params = {
                "domain": domain,
                "api_key": HUNTER_API_KEY,
                "limit": 5,
                "type": "personal",
                "seniority": "senior,executive"
            }
            resp = requests.get(url, params=params, timeout=12)
            if resp.status_code != 200:
                return []

            data = resp.json()
            company = data.get("data", {}).get("organization", domain.split(".")[0].title())
            country = data.get("data", {}).get("country", "Global")
            emails = data.get("data", {}).get("emails", [])

            leads = []
            for e in emails[:3]:
                name = f"{e.get('first_name','')} {e.get('last_name','')}".strip()
                if not name:
                    continue
                leads.append({
                    "company": company,
                    "contact_name": name,
                    "email": e.get("value", ""),
                    "title": e.get("position", ""),
                    "industry": industry,
                    "company_size": "200-1000",
                    "country": country or "India",
                    "website": f"https://{domain}",
                    "source": "Hunter.io",
                    "score": min(e.get("confidence", 70), 95),
                    "notes": ""
                })
            return leads

        except Exception as e:
            self.log("hunter_domain", f"{domain}: {str(e)}", "error")
            return []

    def _ai_generate_leads(self, industry: str, country: str, count: int) -> list:
        prompt = f"""
Generate {count} realistic B2B leads for {industry} companies that would need SecureAI Gateway.
SecureAI Gateway = Enterprise AI access control, DLP, usage monitoring for ChatGPT/Copilot/Claude.

Requirements:
- Real-sounding company names (mid-size, 100-1000 employees)
- Decision maker titles: CTO, CISO, IT Manager, VP Technology, Head of IT
- Realistic work emails matching company domain
- Mix of countries: India, USA, UK, Singapore, UAE
- Focus on companies actively using AI tools

Return JSON array (exactly {min(count,8)} items):
[{{
  "company": "Acme Technologies",
  "contact_name": "Rajesh Kumar",
  "email": "rajesh.kumar@acmetech.com",
  "title": "CTO",
  "industry": "{industry}",
  "company_size": "250-500",
  "country": "India",
  "website": "https://acmetech.com",
  "source": "AI Research",
  "score": 78,
  "notes": "Specific reason why they need SecureAI Gateway"
}}]
Return only JSON array. Make data realistic and varied.
"""
        result = self.think(prompt)
        try:
            clean = result.replace("```json","").replace("```","").strip()
            leads = json.loads(clean)
            self.log("ai_generate", f"Generated {len(leads)} AI leads")
            return leads
        except Exception as e:
            self.log("ai_generate", str(e), "error")
            return []

    def _ai_score_leads(self, leads: list, industry: str) -> list:
        if not leads:
            return []
        try:
            leads_data = [{"i":i,"company":l.get("company"),"title":l.get("title",""),"size":l.get("company_size",""),"country":l.get("country","")} for i,l in enumerate(leads)]
            leads_json = json.dumps(leads_data)
            prompt = "Score these " + industry + " leads for SecureAI Gateway (0-100) and add specific notes.\n"
            prompt += "Leads: " + leads_json + "\n\n"
            prompt += "Score based on: AI adoption likelihood, company size, decision maker seniority, compliance needs.\n"
            prompt += "Return JSON: [{" + '"index":0,"score":85,"notes":"why they urgently need SecureAI Gateway"' + "}]\n"
            prompt += "Return only JSON."
            result = self.think(prompt)
            clean = result.replace("```json","").replace("```","").strip()
            scores = json.loads(clean)
            for s in scores:
                idx = s.get("index", 0)
                if idx < len(leads):
                    leads[idx]["score"] = s.get("score", leads[idx].get("score", 70))
                    if s.get("notes"):
                        leads[idx]["notes"] = s.get("notes")
        except Exception as e:
            self.log("ai_score", str(e), "error")
        return leads

    def search_by_domain(self, domain: str) -> list:
        """Manually search a specific company domain"""
        leads = self._hunter_domain_search(domain, "Unknown")
        if leads:
            saved = self._save_leads(leads)
            self.log("search_by_domain", f"Found {len(leads)} contacts at {domain}")
        return leads

    def _save_leads(self, leads: list) -> int:
        db = self.db
        saved = 0
        for lead_data in leads:
            try:
                email = lead_data.get("email", "")
                if email:
                    existing = db.query(Lead).filter(Lead.email == email).first()
                    if existing:
                        continue
                lead = Lead(
                    company=lead_data.get("company", "Unknown"),
                    contact_name=lead_data.get("contact_name", ""),
                    email=email,
                    industry=lead_data.get("industry", ""),
                    company_size=str(lead_data.get("company_size", "")),
                    country=lead_data.get("country", ""),
                    source=lead_data.get("source", "Scout Agent"),
                    score=int(lead_data.get("score", 50)),
                    notes=lead_data.get("notes", ""),
                    status="new"
                )
                db.add(lead)
                saved += 1
            except Exception as e:
                self.log("save_lead", str(e), "error")
        db.commit()
        metrics = db.query(Metric).first()
        if metrics:
            metrics.total_leads += saved
            metrics.updated_at = datetime.utcnow()
            db.commit()
        return saved

    def get_all_leads(self) -> list:
        db = self.db
        leads = db.query(Lead).order_by(Lead.score.desc()).all()
        return [{"id":l.id,"company":l.company,"contact":l.contact_name,"email":l.email,
                 "industry":l.industry,"country":l.country,"score":l.score,"status":l.status,
                 "notes":l.notes,"created_at":str(l.created_at)} for l in leads]
