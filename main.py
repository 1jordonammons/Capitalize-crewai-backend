
import os
import json
import re
from dotenv import load_dotenv
from supabase import create_client
from crewai import Agent, Task, Crew, LLM

load_dotenv()

supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_ANON_KEY")
anthropic_key = os.getenv("ANTHROPIC_API_KEY")

if not supabase_url or not supabase_key:
    raise ValueError("Missing SUPABASE_URL or SUPABASE_ANON_KEY in .env")

if not anthropic_key:
    raise ValueError("Missing ANTHROPIC_API_KEY in .env")

supabase = create_client(supabase_url, supabase_key)

claude_llm = LLM(
    model="anthropic/claude-sonnet-4-5",
    temperature=0
)

ingestion_agent = Agent(
    role="Data Ingestion Specialist",
    goal="Extract raw financial data from commercial real estate property documents",
    backstory="Expert at parsing offering memorandums, rent rolls, financial tables, and real estate metrics.",
    llm=claude_llm,
    verbose=True
)

risk_agent = Agent(
    role="Investment Risk Auditor",
    goal="Evaluate extracted property metrics against strict risk thresholds",
    backstory="Senior asset risk officer specialized in commercial real estate underwriting.",
    llm=claude_llm,
    verbose=True
)

property_document = """
Property Name: Ovaltine Court
Occupancy: 82%
DSCR: 1.12
Cap Rate: 5.1%
NOI Growth Assumption: 9% annually
Market Vacancy: 7%
Debt Maturity: 18 months
"""

ingestion_task = Task(
    description=f"""
Extract the key underwriting metrics from this property document:

{property_document}

Return only a clean summary of the extracted metrics.
""",
    expected_output="A clean list of extracted underwriting metrics including property name, occupancy, DSCR, cap rate, NOI growth, vacancy, and debt maturity.",
    agent=ingestion_agent
)

audit_task = Task(
    description="""
Using the extracted underwriting metrics, analyze investment risk.

Flag risks using these thresholds:
- Occupancy below 90% = elevated leasing risk
- DSCR below 1.25 = debt service risk
- NOI growth above 5% = aggressive growth assumption
- Debt maturity under 24 months = refinance risk
- Cap rate below 6% = pricing risk

Return ONLY strict valid JSON. No markdown. No explanation.

JSON format:
{
  "property_name": "string",
  "overall_risk_level": "Low | Medium | High",
  "risk_triggers": [
    {
      "risk_type": "string",
      "metric": "string",
      "value": "string",
      "reason": "string"
    }
  ],
  "summary": "string"
}
""",
    expected_output="Strict valid JSON object with property name, overall risk level, risk triggers, and summary.",
    agent=risk_agent,
    context=[ingestion_task]
)

real_estate_crew = Crew(
    agents=[ingestion_agent, risk_agent],
    tasks=[ingestion_task, audit_task],
    verbose=True
)

print("Starting agent analysis workflow...")

result = real_estate_crew.kickoff()

raw_output = result.raw if hasattr(result, "raw") else str(result)

print("Raw agent output:")
print(raw_output)

def extract_json(text):
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("No JSON object found in agent output.")
    return json.loads(match.group(0))

try:
    data_to_save = extract_json(raw_output)

    response = supabase.table("property_audits").insert({
        "property_name": data_to_save.get("property_name", "Unknown Property"),
        "audit_data": data_to_save
    }).execute()

    print("Database sync complete. Lovable dashboard can now display the fresh audit data.")
    print(response)

except Exception as error:
    print("Pipeline finished but database sync failed.")
    print("Check JSON formatting, Supabase table schema, or environment variables.")
    print(error)

