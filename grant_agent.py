import json
import re
import time
import random
import os
from datetime import datetime, timedelta

# File paths
GRANTS_FILE = 'grants.js'

def load_grants():
    """Reads the grants.js file and parses the JSON data."""
    if not os.path.exists(GRANTS_FILE):
        print(f"Error: {GRANTS_FILE} not found.")
        return []
    
    with open(GRANTS_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
        
    # Strip the JavaScript assignment part to get valid JSON
    json_str = content.replace('window.grantsData = ', '').strip().rstrip(';')
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")
        return []

def save_grants(grants):
    """Writes the list of grants back to grants.js."""
    with open(GRANTS_FILE, 'w', encoding='utf-8') as f:
        f.write(f"window.grantsData = {json.dumps(grants, indent=2)};")
    print(f"✅ Successfully updated {GRANTS_FILE} with {len(grants)} grants.")

def ai_scan_simulation():
    """Simulates an AI agent scanning the web for new grants."""
    print("\n🔍 AI Agent Initialized...")
    print("📡 Connecting to global startup databases...")
    time.sleep(1)
    print("cwling: startupindia.gov.in...")
    time.sleep(0.5)
    print("cwling: ycombinator.com...")
    time.sleep(0.5)
    print("cwling: techcrunch.com/funding...")
    time.sleep(1)
    
    # Mock "New" Grants
    potential_findings = [
        {
            "program_name": "Google for Startups Cloud Program",
            "provider": "Google Cloud",
            "country": "Global",
            "sector_focus": "AI, Web3, SaaS",
            "funding_type": "Credits (Non-dilutive)",
            "funding_amount": "Up to $350,000 (Credits)",
            "eligibility_summary": "Series A or lower. Verified domain.",
            "deadline": "Open All Year",
            "application_link": "https://cloud.google.com/startup",
            "required_documents": ["Company Domain", "Funding Proof"],
            "effort_level": "Low",
            "relevance_score": 98,
            "priority": "High"
        },
        {
            "program_name": "Y Combinator W26 Batch",
            "provider": "Y Combinator",
            "country": "Global (US based)",
            "sector_focus": "Sector Agnostic",
            "funding_type": "Equity Investment",
            "funding_amount": "$500,000",
            "eligibility_summary": "Early stage. High growth potential.",
            "deadline": "2026-03-30",
            "application_link": "https://www.ycombinator.com/apply",
            "required_documents": ["Founder Video", "Demo"],
            "effort_level": "High",
            "relevance_score": 92,
            "priority": "High"
        },
        {
            "program_name": "NVIDIA Inception Program",
            "provider": "NVIDIA",
            "country": "Global",
            "sector_focus": "AI, Data Science",
            "funding_type": "Hardware Discounts & Credits",
            "funding_amount": "Varies",
            "eligibility_summary": "AI/Data Science startups.",
            "deadline": "Open All Year",
            "application_link": "https://www.nvidia.com/en-us/startups/",
            "required_documents": ["Company Details"],
            "effort_level": "Low",
            "relevance_score": 88,
            "priority": "Medium"
        }
    ]
    
    # Randomly find one
    found = random.choice(potential_findings)
    print(f"\n✨ FOUND NEW OPPORTUNITY: {found['program_name']}")
    return found

def smart_funnel_parser():
    """Takes raw text input and uses 'AI' (Regex/heuristics) to parse it."""
    print("\n📥 SMART FUNNEL ACTIVATED")
    print("Paste the raw text of a grant email or webpage description below.")
    print("Type 'END' on a new line when finished:\n")
    
    lines = []
    while True:
        line = input()
        if line.strip() == 'END':
            break
        lines.append(line)
    
    raw_text = "\n".join(lines)
    
    if not raw_text.strip():
        print("⚠️ No text provided.")
        return None

    print("\n🧠 AI Analyzing text structure...")
    time.sleep(1)

    # Heuristic Parsing
    name_match = re.search(r"(?:Grant Name|Program|Title):?\s*(.+)", raw_text, re.IGNORECASE)
    amount_match = re.search(r"(?:Amount|Funding|Value):?\s*(.+)", raw_text, re.IGNORECASE)
    deadline_match = re.search(r"(?:Deadline|Due Date|Apply by):?\s*(.+)", raw_text, re.IGNORECASE)
    link_match = re.search(r"(http[s]?://\S+)", raw_text)
    
    # Fallbacks if simple regex fails
    program_name = name_match.group(1).strip() if name_match else "Unknown Grant Program"
    funding_amount = amount_match.group(1).strip() if amount_match else "Unknown Amount"
    deadline = deadline_match.group(1).strip() if deadline_match else "Open"
    link = link_match.group(1).strip() if link_match else "#"
    
    # Construct Object
    grant = {
        "program_name": program_name,
        "provider": "External Source (Funnel)",
        "country": "Unknown",
        "sector_focus": "General",
        "funding_type": "Grant/Other",
        "funding_amount": funding_amount,
        "eligibility_summary": "See details.",
        "deadline": deadline,
        "application_link": link,
        "required_documents": ["Check website"],
        "effort_level": "Medium",
        "relevance_score": 80,
        "priority": "Medium"
    }
    
    print("\n✅ Extracted Data:")
    print(json.dumps(grant, indent=2))
    return grant

def main():
    print("==========================================")
    print("   🤖 GRANT AUTOMATION AGENT v1.0   ")
    print("==========================================")
    
    while True:
        print("\nCOMMANDS:")
        print("1. [SCAN]   Simulate AI Web Scan")
        print("2. [FUNNEL] Parse Raw Text (Smart Add)")
        print("3. [EXIT]   Quit")
        
        choice = input("\nSelect command (1-3): ").strip()
        
        if choice == '1':
            new_grant = ai_scan_simulation()
            if new_grant:
                confirm = input("Add this grant to database? (y/n): ").lower()
                if confirm == 'y':
                    grants = load_grants()
                    # Check for duplicates
                    if not any(g['program_name'] == new_grant['program_name'] for g in grants):
                        grants.insert(0, new_grant) # Add to top
                        save_grants(grants)
                    else:
                        print("⚠️ Grant already exists!")
        
        elif choice == '2':
            new_grant = smart_funnel_parser()
            if new_grant:
                confirm = input("Add this grant to database? (y/n): ").lower()
                if confirm == 'y':
                    grants = load_grants()
                    grants.insert(0, new_grant)
                    save_grants(grants)
                    
        elif choice == '3':
            print("Goodbye! 👋")
            break
        else:
            print("Invalid command.")

if __name__ == "__main__":
    main()
