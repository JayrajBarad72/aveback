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
        # --- Fresh batch (added to refill pipeline) ---
        "lewissilkin.com", "kingsleynapley.co.uk", "michelmores.com",
        "burges-salmon.com", "shoosmiths.com", "trowers.com",
        "stevens-bolton.com", "wedlakebell.com", "rpc.co.uk",
        "freeths.co.uk", "millsreeve.com", "tltsolicitors.com",
        "kennedyslaw.com", "fieldfisher.com",
        "osborneclarke.com", "wfw.com", "stephenson-harwood.com",
        "buchalter.com", "nixonpeabody.com", "wsgr.com",
        "perkinscoie.com", "fenwick.com", "cooley.com",
        # US law firms (50-500 employees)
        "lathropgpm.com", "foxrothschild.com", "fisherphillips.com",
        "grsm.com", "hklaw.com", "bclplaw.com", "seyfarth.com",
        # UK law firms
        "weightmans.com", "brownejacobson.com", "bevanbrittan.com",
        "clydeco.com", "dwf.law", "shakespeares.co.uk",
        # Europe — Germany (GDPR strictest enforcement)
        "noerr.com", "gleisslutz.com", "heuking.de",
        "cbh.de", "gvw.com", "luther-lawfirm.com",
        # Europe — Netherlands
        "nautadutilh.com", "hvglaw.nl", "loyensloeff.com",
        # Europe — France
        "gide.com", "fidal.com", "linklaters.com",
        # Europe — Spain
        "uria.com", "garrigues.com", "cuatrecasas.com",
        # Europe — Nordics (very privacy-focused)
        "vinge.se", "bech-bruun.com", "kromannreumert.com",
        # Australia & Canada
        "maddocks.com.au", "corrs.com.au", "mcmillan.ca",
    ],
    "Healthcare": [
        # --- Fresh batch (added to refill pipeline) ---
        "circlehealthgroup.co.uk", "nuffieldhealth.com", "practiceplusgroup.com",
        "onewelbeck.com", "hcahealthcare.co.uk", "kingedwardvii.co.uk",
        "vita-health.co.uk", "benenden.co.uk", "bupa.com",
        "medizinische-klinik.de", "rhoen-klinikum-ag.com", "vivantes.de",
        "korian.com", "orpea.com", "domusvi.com",
        "attendo.com", "humananamedical.com", "mediclinic.com",
        "ihhhealthcare.com", "ardenthealth.com", "surgerypartners.com",
        "uspi.com", "envisionhealth.com",
        # US healthcare SMB
        "teamhealth.com", "concentra.com", "mdvip.com",
        # UK
        "spirehealthcare.com", "ramsayhealth.co.uk",
        # Europe — Germany (strict health data laws)
        "helios-gesundheit.de", "asklepios.com", "sana.de",
        # Europe — Netherlands
        "radboudumc.nl", "umcutrecht.nl",
        # Europe — Nordics
        "aleris.se", "capio.com", "falck.com",
        # Europe — France
        "elsan.fr", "ramsay-sante.fr",
        # Europe — Switzerland (banking + pharma hub)
        "kssg.ch", "hirslanden.ch", "schulthess-klinik.ch",
        # Middle East
        "mediclinic.ae", "nmc.ae", "aster.ae",
        # Australia
        "healthscope.com.au", "cabrini.com.au",
    ],
    "Finance": [
        # --- Fresh batch (added to refill pipeline) ---
        "marqeta.com", "melio.com", "brex.com",
        "ramp.com", "mercury.com", "column.com",
        "modulr.com", "gocardless.com", "wise.com",
        "zopa.com", "atombank.co.uk", "tandem.co.uk",
        "n26.com", "scalable.capital", "trade-republic.com",
        "qonto.com", "swile.co", "spendesk.com",
        "pleo.io", "lunarway.com", "northmill.com",
        "banking-circle.com", "rapyd.net", "thoughtmachine.net",
        # US fintech (50-300 employees)
        "kabbage.com", "fundbox.com", "bluevine.com",
        "greensky.com", "avant.com", "ondeck.com",
        # UK fintech
        "oaknorth.com", "iwoca.co.uk", "funding-circle.com",
        "tide.co", "starlingbank.com", "monzo.com",
        # Europe — Germany fintech (very GDPR conscious)
        "solarisbank.com", "mambu.com", "raisin.com",
        "auxmoney.com", "crosslend.com", "creditshelf.com",
        # Europe — Netherlands fintech
        "bunq.com", "adyen.com", "mollie.com",
        # Europe — France fintech
        "younited-credit.com", "lydia-app.com", "october.eu",
        # Europe — Nordics fintech
        "klarna.com", "izettle.com", "trustly.com",
        # Europe — Spain fintech
        "bizum.es", "aplazame.com", "myinvestor.es",
        # Australia fintech
        "prospa.com.au", "moula.com.au",
        # Middle East fintech
        "beehive.finance", "liwwa.com",
    ],
    "IT_SMB": [
        # --- Fresh batch (added to refill pipeline) ---
        "coretek.com", "dataprise.com", "electric.ai",
        "framework-it.com", "mindsight.com", "thrivenextgen.com",
        "anchortech.com", "netgainit.com", "cohesivenetworks.com",
        "softcat.com", "softwareone.com", "advania.co.uk",
        "node4.co.uk", "wavenet.co.uk", "cloudm.io",
        "axians.com", "devoteam.com", "reply.com",
        "tietoevry.com", "knowit.eu", "netcompany.com",
        "softwarepoint.com", "nexer.com",
        # US MSP (50-300 employees)
        "ntiva.com", "logically.ai", "clearnetwork.com",
        "stratospherenetworks.com", "cyberfort.com", "arraya.com",
        # UK MSP
        "fordway.com", "littlefish.co.uk", "ievolve.co.uk",
        # Europe — Germany IT (very security focused)
        "bechtle.com", "cancom.com", "allgeier.com",
        "datagroup.de", "computacenter.com", "ntt.com",
        # Europe — Netherlands IT
        "atos.net", "cgi.com", "capgemini.com",
        # Europe — Nordics IT
        "tieto.com", "visma.com", "basware.com",
        # Europe — France IT
        "sopragroup.com", "altran.com", "inetum.com",
        # Europe — Belgium/Luxembourg
        "nviso.eu", "cronos.be", "cegeka.com",
        # Australia IT
        "versent.com.au", "itoc.com.au",
        # Canada IT
        "compugen.com", "pythian.com",
    ],
    "Consulting": [
        # --- Fresh batch (added to refill pipeline) ---
        "alvarezandmarsal.com", "fticonsulting.com", "berkeleyresearchgroup.com",
        "thinkbrg.com", "northhighland.com", "westmonroe.com",
        "slalom.com", "publicissapient.com", "elixirr.com",
        "baringa.com", "newtoneurope.com", "gateone.co.uk",
        "qcg.de", "horvath-partners.com", "zeb-consulting.com",
        "simon-kucher.com", "oliverwyman.com", "lek.com",
        "openhealthgroup.com", "efeso.com", "argon-consult.com",
        "delta-partners.com",
        # US consulting (50-300 employees)
        "guidehouse.com", "chartis.com", "rsm.com",
        "plante.com", "propellergroup.com",
        # UK consulting
        "moorhouse.com", "pa.com", "clarasys.com",
        "mottmac.com", "arup.com",
        # Europe — Germany consulting
        "rolandberger.com", "goetzpartners.com", "detecon.com",
        "bbh.de", "bearing-point.com",
        # Europe — Netherlands consulting
        "kpmg.nl", "bcg.com", "mckinsey.com",
        # Europe — Nordics consulting
        "implement.dk", "ramboll.com", "sweco.se",
        # Europe — France consulting
        "wavestone.com", "sia-partners.com", "kearney.com",
        # Europe — Switzerland consulting
        "pricecc.com", "bain.com", "accenture.com",
        # Australia consulting
        "kordamentha.com", "pitcher.com.au",
    ],
    "Manufacturing": [
        # --- Fresh batch (added to refill pipeline) ---
        "barnesgroupinc.com", "cirrus-aircraft.com", "moog.com",
        "curtisswright.com", "esterline.com", "ducommun.com",
        "renishaw.com", "spectris.com", "morgan-electronics.com",
        "ricardo.com", "spirax-sarco.com", "rotork.com",
        "pfeiffer-vacuum.com", "jenoptik.com", "krones.com",
        "duerr.com", "gea.com", "koerber.com",
        "interroll.com", "bystronic.com", "georgfischer.com",
        "vat.ch", "comet-group.com",
        # US mid-size
        "haynes.com", "materion.com", "kaman.com",
        # UK
        "bodycote.com", "renold.com", "luxfer.com",
        # Europe — Germany manufacturing (Industry 4.0, lots of AI adoption)
        "trumpf.com", "kuka.com", "sick.com",
        "harting.com", "wago.com", "lapp.com",
        "festo.com", "balluff.com", "ifm.com",
        # Europe — Netherlands manufacturing
        "philips.com", "asml.com", "aalberts.com",
        # Europe — Nordics manufacturing
        "sandvik.com", "atlas-copco.com", "alfa-laval.com",
        # Europe — France manufacturing
        "legrand.com", "essilor.com", "rexel.com",
        # Europe — Switzerland
        "abb.com", "georg-fischer.com", "sulzer.com",
        # Australia
        "boral.com.au", "orica.com",
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

        # Skip domains we've already saved qualified leads from, so repeated
        # runs work through the full target list instead of re-hitting the
        # same first 8 domains forever.
        db = self.db
        done_companies = {
            (row[0] or "").lower() for row in db.query(Lead.company).filter(Lead.industry == industry).all()
        }

        pending = [d for d in companies if d.split(".")[0].lower() not in done_companies]
        if not pending:
            pending = companies  # exhausted the whole list, start over

        for domain in pending[:8]:  # Check up to 8 not-yet-saved companies per industry
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
