# Capitalize CrewAI Backend

Capitalize CrewAI Backend is a Python FastAPI service that runs a CrewAI-powered commercial real estate deal screening workflow. It accepts Offering Memorandum text, extracts key underwriting metrics, flags investment risks, generates a structured audit report, and saves the result to Supabase.

## What It Does

- Receives OM/deal text from a frontend app
- Runs CrewAI agents for deal analysis
- Extracts key CRE metrics such as occupancy, DSCR, cap rate, NOI growth, debt maturity, and market vacancy
- Flags risk triggers based on underwriting thresholds
- Generates a structured JSON investment risk report
- Saves the completed audit into Supabase
- Returns the report to the frontend for display

## Tech Stack

- Python
- FastAPI
- CrewAI
- Anthropic Claude
- Supabase
- ngrok for local demo tunneling

## Architecture

```text
Lovable Frontend
        ↓
ngrok Public URL
        ↓
FastAPI Backend
        ↓
CrewAI Agents
        ↓
Supabase Database
        ↓
Lovable Dashboard
