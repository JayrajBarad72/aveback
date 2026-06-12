"""
Scout Agent — Finds qualified leads globally
Target: Decision makers at 20-500 employee companies who actually buy AI security tools
NOT: Big enterprises (Infosys, Wipro) or wrong departments (sales, HR, marketing)
"""
import json
import requests
import os
from agents.base_agent import BaseAgent
from database import Lead, SessionLocal
from datetime import datetime

# ── WHO WE TARGET ─────────────────────────────────────────────────────────────
# Company size: 20-500 employees (SMB sweet spot)
# Geography: Global — US, UK, EU, Australia, Canada, Middle East, India SMBs
# Industries: Any company handling sensitive data

TARGET_COMPANIES = {
    "Legal": [
        # US law firms
        "lathropgpm.com", "foxrothschild.com", "fisherphillips.com",
        "grsm.com", "hklaw.com", "bclplaw.com", "seyfarth.com",
        # UK law firms
        "weightmans.com", "brownejacobson.com", "bevanbrittan.com",
        # Australia
        "maddocks.com.au", "corrs.com.au", "sparke.com.au",
        # Canada
        "mcmillan.ca", "dentons.com", "blakes.com",
    ],
    "Healthcare": [
        # US healthcare
        "teamhealth.com", "envision.com", "acuity-healthcare.com",
        "primedica.com", "mdvip.com", "concentra.com",
        # UK
        "spirehealthcare.com", "ramsayhealth.co.uk",
        # Australia
        "healthscope.com.au", "cabrini.com.au",
        # Middle East
        "mediclinic.ae", "nmc.ae", "aster.ae",
        # India SMB (NOT large hospital chains)
        "drreddys.com", "cloudninehospital.com",
    ],
    "Finance": [
        # US fintech/NBFC
        "kabbage.com", "fundbox.com", "bluevine.com", "ondeck.com",
        "greensky.com", "avant.com", "lendingclub.com",
        # UK fintech
        "oaknorth.com", "iwoca.co.uk", "funding-circle.com",
        # Australia
        "prospa.com.au", "moula.com.au", "spotcap.com",
        # Middle East fintech
        "beehive.finance", "liwwa.com", "capiter.com",
        # India fintech SMB
        "lendingkart.com", "neogrowth.in", "aye.finance",
    ],
    "IT_SMB": [
        # US IT consulting/MSP (50-300 employees)
        "ntiva.com", "isg-one.com", "datalinknetworks.com",
        "presidio.com", "cpurge.com", "logically.ai",
        "clearnetwork.com", "stratospherenetworks.com",
        # UK MSP
        "pomeroy.com", "fordway.com", "littlefish.co.uk",
        # Australia IT
        "versent.com.au", "itoc.com.au", "empired.com",
        # Canada IT
        "sievert.ca", "compugen.com", "pythian.com",
    ],
    "Consulting": [
        # US consulting (50-300 employees)
        "propellergroup.com", "guidehouse.com", "navigant.com",
        "chartis.com", "kpmg.com", "rsm.com", "plante.com",
        # UK
        "moorhouse.com", "pa.com", "clarasys.com",
        # Australia
        "kordamentha.com", "pitcher.com.au", "mcgrathnicol.com",
    ],
    "Manufacturing": [
        # US mid-size manufacturers
        "haynes.com", "materion.com", "insteel.com",
        "aptargroup.com", "kaman.com", "watts.com",
        # UK
        "bodycote.com", "renold.com", "luxfer.com",
        # Australia
        "boral.com.au", "incitec.com.au", "orica.com",
    ]
}

# ── WHO IS A QUALIFIED LEAD (job title filter) ─────────────────────────────────
QUALIFIED_TITLES = [
    # C-Suite
    "ceo", "cto", "ciso", "coo", "cio", "chief executive",
    "chief technology", "chief information", "chief security", "chief operating",
    # IT Leadership
    "it manager", "it director", "it head", "head of it", "vp it",
    "it infrastructure", "systems administrator", "sysadmin",
    "network administrator", "it administrator",
    # Security
    "security manager", "security officer", "information security",
    "cybersecurity", "compliance officer", "compliance manager",
    "data protection", "dpo", "gdpr", "risk officer", "risk manager",
    # Tech Leadership
    "vp engineering", "director of engineering", "head of engineering",
    "engineering manager", "technical director", "technology director",
    # Founders
    "founder", "co-founder", "managing director", "managing partner",
    "owner", "president", "partner",
    # Operations
    "operations director", "operations manager", "head of operations",
]

# ── WHO IS NOT A QUALIFIED LEAD ────────────────────────────────────────────────
DISQUALIFIED_TITLES = [
    "sales", "marketing", "business development", "account executive",
    "account manager", "recruiter", "hr ", "human resources",
    "talent", "analyst", "associate", "intern", "coordinator",
    "assistant", "receptionist", "secretary", "administrative",
    "graphic", "designer", "copywriter", "social media",
    "seo", "content", "customer success", "support",
]

def is_qualified_title(title: str) -> bool:
    """Returns True if job title is a decision maker we want to target"""
    if not title:
        return False
    title_lower = title.lower()

    # Disqualify first
    for bad in DISQUALIFIED_TITLES:
        if bad in title_lower:
            return False

    # Qualify
    for good in QUALIFIED_TITLES:
        if good in title_lower:
            return True

    return False


class ScoutAgent(BaseAgent):
    def __init__(self):
        super().__init__("Scout Agent", "Lead Finder")
        self.hunter_key = os.getenv("HUNTER_API_KEY", "beb5cd3914af45403b8b788eb367d0f7249c9561")

    def search_leads(self, industry: str, count: int = 10) -> list:
        self.log("search_leads", f"Searching {industry} globally for decision makers")
        all_leads = []
        companies = TARGET_COMPANIES.get(industry, [])

        for domain in companies[:8]:  # Check 8 companies per industry
            try:
                url = "https://api.hunter.io/v2/domain-search"
                params = {
                    "domain": domain,
                    "api_key": self.hunter_key,
                    "limit": 10,
                    "type": "personal"
                }
                resp = requests.get(url, params=params, timeout=15)
                if resp.status_code != 200:
                    continue

                data = resp.json().get("data", {})
                company_name = data.get("organization", domain.split(".")[0].title())
                emails_found = data.get("emails", [])

                for e in emails_found:
                    title = e.get("position", "") or ""
                    first = e.get("first_name", "")
                    last = e.get("last_name", "")
                    email = e.get("value", "")
                    confidence = e.get("confidence", 0)

                    # Filter: must be decision maker + high confidence email
                    if not is_qualified_title(title):
                        self.log("search_leads", f"Skipped {title} at {domain} — not decision maker")
                        continue

                    if confidence < 70:
                        self.log("search_leads", f"Skipped {email} — low confidence {confidence}%")
                        continue

                    all_leads.append({
                        "company": company_name,
                        "contact_name": f"{first} {last}".strip(),
                        "title": title,
                        "email": email,
                        "industry": industry,
                        "domain": domain,
                        "confidence": confidence,
                        "country": data.get("country", "Global"),
                    })

                if len(all_leads) >= count:
                    break

            except Exception as e:
                self.log("search_leads", f"Hunter error for {domain}: {e}", "error")
                continue

        self.log("search_leads", f"Found {len(all_leads)} qualified decision makers in {industry}")
        return all_leads[:count]

    def score_and_save_leads(self, leads: list, industry: str) -> int:
        """Score leads with AI and save to DB"""
        if not leads:
            return 0

        db = self.db
        saved = 0

        for lead in leads:
            # Check duplicate
            existing = db.query(Lead).filter(Lead.email == lead["email"]).first()
            if existing:
                continue

            # AI scoring
            prompt = f"""Score this lead for SecureAI Gateway (enterprise AI security, on-premise DLP).
Company: {lead['company']}
Contact: {lead['contact_name']}
Title: {lead['title']}
Industry: {industry}
Email confidence: {lead.get('confidence', 0)}%

Score 0-100 based on:
- Decision making authority (CTO/CISO/IT Manager = high, founder = high)
- Industry compliance needs (healthcare/legal/finance = high)
- Likely AI adoption stage
- Budget authority

Return JSON only: {{"score": 85, "notes": "why they need SecureAI Gateway specifically"}}"""

            try:
                result = self.think(prompt)
                scored = json.loads(result.replace("```json","").replace("```","").strip())
                score = scored.get("score", 70)
                notes = scored.get("notes", "")
            except:
                score = 70
                notes = f"{lead['title']} at {lead['company']} in {industry}"

            new_lead = Lead(
                company=lead["company"],
                contact_name=lead["contact_name"],
                email=lead["email"],
                industry=industry,
                country=lead.get("country", "Global"),
                score=score,
                status="new",
                notes=f"[{lead['title']}] {notes}",
                created_at=datetime.utcnow()
            )
            db.add(new_lead)
            db.commit()
            saved += 1
            self.log("save_lead", f"Saved: {lead['contact_name']} ({lead['title']}) at {lead['company']} — score {score}")

        return saved

    def run_full_scout(self) -> dict:
        """Full scout cycle — all industries"""
        total_saved = 0
        results = {}

        for industry in TARGET_COMPANIES.keys():
            try:
                leads = self.search_leads(industry, count=5)
                saved = self.score_and_save_leads(leads, industry)
                total_saved += saved
                results[industry] = {"found": len(leads), "saved": saved}
                self.log("run_full_scout", f"{industry}: found {len(leads)}, saved {saved}")
            except Exception as e:
                self.log("run_full_scout", f"{industry} error: {e}", "error")
                results[industry] = {"error": str(e)}

        return {"total_saved": total_saved, "by_industry": results}
