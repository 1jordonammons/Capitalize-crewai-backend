import os
import json
import re
from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel
from supabase import create_client
from crewai import Agent, Task, Crew, LLM

load_dotenv()

app = FastAPI()

supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_ANON_KEY")
supabase = create_client(supabase_url, supabase_key)

claude_llm = LLM(
    model="anthropic/claude-sonnet-4-5",
    temperature=0
)

class ScreeningRequest(BaseModel):
    om_text: str
    deal_notes: str | None = None

def extract_json(text):
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("No JSON object found in CrewAI output.")
    return json.loads(match.group(0))

@app.post("/run-screening")
def run_screening(request: ScreeningRequest):
    property_document = request.om_text

    ingestion_agent = Agent(
        role="Data Ingestion Specialist",
        goal="Extract key financial and real estate metrics from Offering Memorandum text",
        backstory="Expert at parsing commercial real estate Offering Memorandums, rent rolls, financial tables, and underwriting assumptions.",
        llm=claude_llm,
        verbose=True
    )

    risk_agent = Agent(
        role="Investment Risk Auditor",
        goal="Evaluate extracted property metrics against risk thresholds and produce a structured investment risk report",
        backstory="Senior commercial real estate asset risk officer specialized in underwriting, debt risk, leasing risk, and deal screening.",
        llm=claude_llm,
        verbose=True
    )

    ingestion_task = Task(
        description=f"""
Extract key underwriting metrics from this Offering Memorandum text.

Offering Memorandum:
{property_document}

Deal notes:
{request.deal_notes or "None provided"}

Extract:
- property name
- NOI
- cap rate
- IRR
- occupancy
- DSCR
- price per unit
- debt maturity
- market vacancy
- missing or unclear metrics
""",
        expected_output="Clean extracted deal metrics from the OM.",
        agent=ingestion_agent
    )

    audit_task = Task(
        description="""
Using the extracted metrics, analyze investment risk.

Flag risks using these rules when applicable:
- Occupancy below 90% = elevated leasing risk
- DSCR below 1.25 = debt service risk
- NOI growth above 5% = aggressive growth assumption
- Debt maturity under 24 months = refinance risk
- Cap rate below 6% = pricing risk
- Missing key data = diligence risk

Return ONLY valid JSON. No markdown.

JSON format:
{
  "property_name": "string",
  "overall_risk_level": "Low | Medium | High",
  "key_metrics": {
    "noi": "string",
    "cap_rate": "string",
    "irr": "string",
    "occupancy": "string",
    "dscr": "string",
    "price_per_unit": "string",
    "debt_maturity": "string",
    "market_vacancy": "string"
  },
  "risk_triggers": [
    {
      "risk_type": "string",
      "metric": "string",
      "value": "string",
      "reason": "string"
    }
  ],
  "recommendation": "string",
  "summary": "string"
}
""",
        expected_output="Strict valid JSON risk report.",
        agent=risk_agent,
        context=[ingestion_task]
    )

    crew = Crew(
        agents=[ingestion_agent, risk_agent],
        tasks=[ingestion_task, audit_task],
        verbose=True
    )

    result = crew.kickoff()
    raw_output = result.raw if hasattr(result, "raw") else str(result)
    data_to_save = extract_json(raw_output)

    response = supabase.table("property_audits").insert({
        "property_name": data_to_save.get("property_name", "Unknown Property"),
        "audit_data": data_to_save
    }).execute()

    return {
        "success": True,
        "audit": data_to_save,
        "supabase_response": response.data
    }

@app.get("/")
def health_check():
    return {"status": "CrewAI server running"}