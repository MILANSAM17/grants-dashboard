import json
import re
import time
import random
import os
import hashlib
from datetime import datetime, timedelta
import shutil
import sys
import urllib.request
import urllib.error

# --- CONFIGURATION ---
GRANTS_FILE = 'grants.js'
LOGS_DIR = 'logs'
LOG_FILE = os.path.join(LOGS_DIR, 'agent_log.json')
BACKUP_DIR = 'backups'
WEBHOOK_URL = os.environ.get('GRANT_ALERT_WEBHOOK')  # Set this in GitHub Secrets

# --- CLASS: SCORING ENGINE ---
class GrantScorer:
    """
    Calculates a relevance score (0-100) based on multiple factors:
    - Eligibility Match
    - Funding Amount vs Effort
    - Deadline Urgency
    - Source Reliability
    """
    
    def __init__(self):
        self.weights = {
            "eligibility": 0.4,
            "funding": 0.3,
            "urgency": 0.2,
            "reliability": 0.1
        }

    def calculate_score(self, grant):
        score = 0.0
        
        # 1. Eligibility Check (Simple Keyword Matching for now)
        # Ideally this would match against a user profile
        eligibility_score = 100
        if "student" in grant.get('eligibility_summary', '').lower(): 
            eligibility_score = 50 # Assume we are a startup, not students
        if "non-profit" in grant.get('sector_focus', '').lower():
            eligibility_score = 60
            
        score += eligibility_score * self.weights['eligibility']
        
        # 2. Funding Analysis
        funding_str = grant.get('funding_amount', '0')
        funding_score = 50 # Default neutral
        if "Equity" in grant.get('funding_type', ''):
            funding_score = 70 # High value but dilutive
        if "Grant" in grant.get('funding_type', ''):
            funding_score = 95 # Free money!
        if "Credits" in grant.get('funding_type', ''):
            funding_score = 60 # Good but restricted use
            
        score += funding_score * self.weights['funding']
        
        # 3. Urgency (Deadline)
        deadline = grant.get('deadline', '')
        urgency_score = 50
        if deadline.lower() == 'open all year':
            urgency_score = 80 # Good because low pressure
        else:
            try:
                # Basic date parsing (assuming YYYY-MM-DD or simple standard formats)
                deadline_date = datetime.strptime(deadline, "%Y-%m-%d")
                days_left = (deadline_date - datetime.now()).days
                
                if days_left < 0: urgency_score = 0 # Expired
                elif days_left < 7: urgency_score = 90 # ACTION NEEDED NOW
                elif days_left < 30: urgency_score = 85
                elif days_left > 90: urgency_score = 60 # Far away
            except:
                urgency_score = 50 # Unknown format
        
        score += urgency_score * self.weights['urgency']
        
        # 4. Source Reliability
        source_type = grant.get('source_category', 'Unknown')
        reliability_score = 50
        if source_type == 'Gov': reliability_score = 100
        elif source_type == 'Accelerator': reliability_score = 90
        elif source_type == 'Private': reliability_score = 80
        
        score += reliability_score * self.weights['reliability']
        
        return int(score)

    def determine_priority(self, score):
        if score >= 90: return "HIGH"
        if score >= 75: return "MEDIUM"
        return "LOW"

# --- CLASS: ALERT MANAGER ---
class AlertManager:
    def __init__(self):
        self.alerts_sent = 0

    def send_webhook(self, payload):
        if not WEBHOOK_URL:
            # print(f"⚠️ [MOCK ALERT] Webhook not set. Payload: {json.dumps(payload)}")
            return
        
        try:
            req = urllib.request.Request(
                WEBHOOK_URL, 
                data=json.dumps(payload).encode('utf-8'),
                headers={'Content-Type': 'application/json'}
            )
            urllib.request.urlopen(req)
            print("🚀 Alert sent successfully!")
        except Exception as e:
            print(f"❌ Failed to send alert: {e}")

    def check_new_grant(self, grant):
        """Checks if a newly added grant allows for an alert."""
        if grant.get('relevance_score', 0) > 85:
            message = {
                "program_name": grant['program_name'],
                "funding_amount": grant['funding_amount'],
                "country": grant['country'],
                "deadline": grant['deadline'],
                "relevance_score": grant['relevance_score'],
                "application_link": grant['application_link'],
                "summary": f"🏆 New High Score Grant: {grant['program_name']} ({grant['relevance_score']})"
            }
            print(f"\n🔔 TRYING ALERT: Score {grant['relevance_score']} > 85")
            self.send_webhook(message)
            self.alerts_sent += 1

    def check_deadlines(self, grants):
        """Checks for grants expiring soon (7 days or 3 days)."""
        today = datetime.now()
        for grant in grants:
            if grant.get('status') in ['Applied', 'Rejected', 'Awarded']:
                continue # Skip closed items
                
            deadline = grant.get('deadline', '')
            if deadline.lower() == 'open all year': continue
            
            try:
                d_date = datetime.strptime(deadline, "%Y-%m-%d")
                days_left = (d_date - today).days
                
                # Alert on exactly 7 days or 3 days left
                if days_left in [7, 3]:
                    message = {
                        "text": (
                            f"⏳ *DEADLINE ALERT: {days_left} Days Left*\n\n"
                            f"📌 {grant['program_name']}\n"
                            f"⚠️ Act fast!"
                        )
                    }
                    self.send_webhook(message)
                    print(f"⏰ Deadline Alert sent for {grant['program_name']}")
            except:
                pass

# --- CLASS: GRANT MANAGER ---
class GrantManager:
    def __init__(self):
        self.grants = []
        self.ensure_dirs()
        self.scorer = GrantScorer()
        self.alerter = AlertManager()
    
    def ensure_dirs(self):
        if not os.path.exists(LOGS_DIR): os.makedirs(LOGS_DIR)
        if not os.path.exists(BACKUP_DIR): os.makedirs(BACKUP_DIR)

    def load_grants(self):
        if not os.path.exists(GRANTS_FILE):
            return []
        
        with open(GRANTS_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
            
        if 'window.grantsData =' in content:
            json_str = content.replace('window.grantsData = ', '').strip().rstrip(';')
        else:
            json_str = content 
            
        try:
            self.grants = json.loads(json_str)
            # Migration
            for g in self.grants:
                if 'id' not in g: g['id'] = self.generate_id(g)
            return self.grants
        except json.JSONDecodeError:
            return []

    def generate_id(self, grant):
        unique_string = f"{grant.get('program_name','')}|{grant.get('provider','')}"
        return hashlib.md5(unique_string.encode()).hexdigest()

    def save_grants(self):
        # Backup
        timestamp = datetime.now().strftime("%Y%m%d")
        backup_file = os.path.join(BACKUP_DIR, f'grants_{timestamp}.js')
        if not os.path.exists(backup_file) and os.path.exists(GRANTS_FILE):
             shutil.copy(GRANTS_FILE, backup_file)
        
        # Save
        with open(GRANTS_FILE, 'w', encoding='utf-8') as f:
            f.write(f"window.grantsData = {json.dumps(self.grants, indent=2)};")
        print(f"💾 Database saved. Total grants: {len(self.grants)}")

    def add_grant(self, new_grant):
        # 1. Enrich
        new_grant['id'] = self.generate_id(new_grant)
        new_grant['source_category'] = new_grant.get('source_category', 'Private')
        new_grant['relevance_score'] = self.scorer.calculate_score(new_grant)
        new_grant['priority'] = self.scorer.determine_priority(new_grant['relevance_score'])
        new_grant['status'] = "Not Applied"
        new_grant['notes'] = ""
        new_grant['added_date'] = datetime.now().strftime("%Y-%m-%d")
        new_grant['last_updated'] = datetime.now().strftime("%Y-%m-%d")
        # New Enriched Fields
        new_grant['awards_available'] = new_grant.get('awards_available', 'Unknown')
        new_grant['open_date'] = new_grant.get('open_date', 'Unknown')

        # 2. Dedup
        existing = next((g for g in self.grants if g['id'] == new_grant['id']), None)
        
        if existing:
            changes = []
            for key in ['deadline', 'funding_amount', 'application_link']:
                if existing.get(key) != new_grant.get(key):
                    changes.append(key)
            
            if changes:
                print(f"🔄 Grant Updated: {new_grant['program_name']} (Changes: {', '.join(changes)})")
                existing.update({k: v for k, v in new_grant.items() if k not in ['status', 'notes', 'added_date']})
                existing['last_updated'] = datetime.now().strftime("%Y-%m-%d")
                return "UPDATED"
            else:
                return "DUPLICATE"
        else:
            self.grants.insert(0, new_grant)
            # 3. ALERT
            self.alerter.check_new_grant(new_grant)
            return "ADDED"
            
    def run_deadline_check(self):
        self.alerter.check_deadlines(self.grants)

# --- CLASS: LOGGER ---
class Auditor:
    def log_run(self, grants_scanned, grants_added, errors=None):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "grants_scanned": grants_scanned,
            "grants_added": grants_added,
            "errors": errors or []
        }
        
        logs = []
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, 'r') as f:
                try: logs = json.load(f)
                except: pass
        
        logs.append(entry)
        logs = logs[-50:]
        
        with open(LOG_FILE, 'w') as f:
            json.dump(logs, f, indent=2)

# --- SIMULATION LOGIC ---
def ai_scan_simulation(manager):
    print("\n🔍 AI Agent Initialized (v2.1 - Alerts Enabled)...")
    time.sleep(1)
    
    # Mock Findings
    potential_findings = [
        {
            "program_name": "OpenAI Residency",
            "provider": "OpenAI",
            "country": "US (Remote Friendly)",
            "sector_focus": "AI, ML Research",
            "funding_type": "Salary + Equity",
            "funding_amount": "$210,000 / year",
            "eligibility_summary": "Exceptional researchers.",
            "deadline": "2026-06-01", 
            "application_link": "https://openai.com/careers",
            "source_category": "Private",
            "effort_level": "High"
        },
        {
            "program_name": "Fast Track High Score Grant",
            "provider": "Test Provider",
            "country": "Global",
            "sector_focus": "General",
            "funding_type": "Grant",
            "funding_amount": "$100,000",
            "eligibility_summary": "Open to all.",
            "deadline": "2026-03-01", 
            "application_link": "https://example.com",
            "source_category": "Gov", # Boosts score
            "effort_level": "Low",
             "awards_available": "50 Spots",
            "open_date": "2026-01-01"
        },
        {
            "program_name": "NSF SBIR Phase I",
            "provider": "National Science Foundation",
            "country": "USA",
            "sector_focus": "DeepTech, R&D",
            "funding_type": "Grant (Non-dilutive)",
            "funding_amount": "$275,000",
            "eligibility_summary": "US-based small businesses engaging in R&D.",
            "deadline": "2026-07-05", 
            "application_link": "https://seedfund.nsf.gov/",
            "source_category": "Gov",
            "effort_level": "High",
            "awards_available": "300+ Awards",
            "open_date": "2026-03-15"
        },
        {
            "program_name": "Y Combinator S26",
            "provider": "Y Combinator",
            "country": "Global (Remote Friendly)",
            "sector_focus": "Tech, B2B, Consumer",
            "funding_type": "Equity ($125k for 7%)",
            "funding_amount": "$500,000",
            "eligibility_summary": "Early stage startups.",
            "deadline": "2026-04-15", 
            "application_link": "https://www.ycombinator.com/apply",
            "source_category": "Accelerator",
            "effort_level": "Medium",
            "awards_available": "250 Cohort Seats",
            "open_date": "2026-01-15"
        },
        {
            "program_name": "UNICEF Innovation Fund",
            "provider": "UNICEF",
            "country": "Global (Emerging Markets)",
            "sector_focus": "Social Impact, Open Source",
            "funding_type": "Grant",
            "funding_amount": "$100,000 (0% Equity)",
            "eligibility_summary": "Open source technology for children.",
            "deadline": "2026-08-01", 
            "application_link": "https://www.unicefinnovationfund.org/",
            "source_category": "Non-Profit",
            "effort_level": "High",
            "awards_available": "Varies",
            "open_date": "2026-06-01"
        },
        {
            "program_name": "Thiel Fellowship",
            "provider": "Thiel Foundation",
            "country": "Global",
            "sector_focus": "Builders",
            "funding_type": "Grant",
            "funding_amount": "$100,000",
            "eligibility_summary": "Under 23, drop out of school.",
            "deadline": "Rolling", 
            "application_link": "https://thielfellowship.org/",
            "source_category": "Private",
            "effort_level": "Medium",
            "awards_available": "20 Fellows",
            "open_date": "Rolling"
        },
        {
            "program_name": "Epic Games MegaGrants",
            "provider": "Epic Games",
            "country": "Global",
            "sector_focus": "Gaming, 3D, Creative",
            "funding_type": "Grant",
            "funding_amount": "$5,000 - $500,000",
            "eligibility_summary": "Creators using Unreal Engine or open source 3D content.",
            "deadline": "Rolling", 
            "application_link": "https://www.unrealengine.com/en-US/megagrants",
            "source_category": "Private",
            "effort_level": "Medium",
            "awards_available": "Rolling Basis",
            "open_date": "Rolling"
        },
        {
            "program_name": "Reach Capital EdTech Fellowship",
            "provider": "Reach Capital",
            "country": "USA / Global",
            "sector_focus": "EdTech, Learning",
            "funding_type": "Equity",
            "funding_amount": "$150,000",
            "eligibility_summary": "Founders building the future of learning.",
            "deadline": "2026-05-20", 
            "application_link": "https://reachcapital.com",
            "source_category": "VC",
            "effort_level": "High",
            "awards_available": "10 Teams",
            "open_date": "2026-02-01"
        },
        {
            "program_name": "Google for Startups: AI Fund",
            "provider": "Google",
            "country": "Europe / Israel",
            "sector_focus": "AI, Cloud, Data",
            "funding_type": "Equity-Free Support",
            "funding_amount": "$350,000 (Cloud Credits)",
            "eligibility_summary": "AI-first startups.",
            "deadline": "2026-04-01", 
            "application_link": "https://campus.co/",
            "source_category": "Private",
            "effort_level": "Low",
            "awards_available": "20 Startups",
            "open_date": "2026-01-20"
        },
        {
            "program_name": "a16z GAMES SPEEDRUN",
            "provider": "Andreessen Horowitz",
            "country": "Global",
            "sector_focus": "Gaming, Web3",
            "funding_type": "Equity ($500k)",
            "funding_amount": "$500,000",
            "eligibility_summary": "High potential gaming startups.",
            "deadline": "2026-05-01", 
            "application_link": "https://a16z.com/speedrun/",
            "source_category": "VC",
            "effort_level": "High",
            "awards_available": "40 Teams",
            "open_date": "2026-03-01"
        },
        {
            "program_name": "Apple Entrepreneur Camp",
            "provider": "Apple",
            "country": "Global",
            "sector_focus": "App Dev, iOS",
            "funding_type": "Mentorship + Hardware",
            "funding_amount": "Unknown",
            "eligibility_summary": "Underrepresented founders building apps.",
            "deadline": "2026-09-01", 
            "application_link": "https://developer.apple.com/entrepreneur-camp/",
            "source_category": "Corporate",
            "effort_level": "Medium",
            "awards_available": "Varies",
            "open_date": "Rolling"
        },
        {
            "program_name": "Google Play Indie Games Fund",
            "provider": "Google Play",
            "country": "Latin America",
            "sector_focus": "App Dev, Gaming",
            "funding_type": "Grant + Support",
            "funding_amount": "$2,000,000 Fund",
            "eligibility_summary": "Indie game studios and app developers.",
            "deadline": "2026-08-15", 
            "application_link": "https://developer.android.com/distribute/google-play/indie-games-fund",
            "source_category": "Corporate",
            "effort_level": "High",
            "awards_available": "10 Studios",
            "open_date": "2026-06-01"
        },
        {
            "program_name": "Apple Entrepreneur Camp",
            "provider": "Apple",
            "country": "Global",
            "sector_focus": "App Dev, iOS",
            "funding_type": "Mentorship + Hardware",
            "funding_amount": "Unknown",
            "eligibility_summary": "Underrepresented founders building apps.",
            "deadline": "2026-09-01", 
            "application_link": "https://developer.apple.com/entrepreneur-camp/",
            "source_category": "Corporate",
            "effort_level": "Medium",
            "awards_available": "Varies",
            "open_date": "Rolling"
        },
        {
            "program_name": "Google Play Indie Games Fund",
            "provider": "Google Play",
            "country": "Latin America",
            "sector_focus": "App Dev, Gaming",
            "funding_type": "Grant + Support",
            "funding_amount": "$2,000,000 Fund",
            "eligibility_summary": "Indie game studios and app developers.",
            "deadline": "2026-08-15", 
            "application_link": "https://developer.android.com/distribute/google-play/indie-games-fund",
            "source_category": "Corporate",
            "effort_level": "High",
            "awards_available": "10 Studios",
            "open_date": "2026-06-01"
        }
    ]
    
    findings_count = len(potential_findings)
    added_count = 0
    
    for grant in potential_findings:
        result = manager.add_grant(grant)
        if result == "ADDED":
            print(f"✨ [NEW] {grant['program_name']} (Score: {grant.get('relevance_score')})")
            added_count += 1
        elif result == "UPDATED":
            print(f"📝 [UPDATE] {grant['program_name']}")
            added_count += 1 
        else:
            print(f"⚠️ [SKIP] {grant['program_name']} (Duplicate)")
    
    # Run daily checks
    manager.run_deadline_check()
            
    return findings_count, added_count

def main():
    manager = GrantManager()
    auditor = Auditor()
    
    manager.load_grants()
    
    # Headless / Auto Mode
    if len(sys.argv) > 1 and sys.argv[1] == '--auto':
        print("🤖 CLOUD AGENT MODE: Starting automated scan...")
        scanned, added = ai_scan_simulation(manager)
        if added > 0:
            manager.save_grants()
        auditor.log_run(scanned, added)
        print("✅ [AUTO] Scan complete.")
        return

    # Interactive Mode
    print("==========================================")
    print("   🧠 INTELLIGENT GRANT AGENT v2.1   ")
    print("   🔔 Alerts System: ACTIVE          ")
    print("==========================================")
    
    if WEBHOOK_URL:
        print(f"🔗 Webhook Configured: YES")
    else:
        print(f"⚠️ Webhook Configured: NO (Set GRANT_ALERT_WEBHOOK env var)")

    while True:
        print("\nCOMMANDS:")
        print("1. [SCAN]   Run AI Scan (Scoring + Dedup + Alerts)")
        print("2. [STATUS] Show Database Stats")
        print("3. [TEST]   Send Test Alert")
        print("4. [EXIT]   Quit")
        
        choice = input("\nSelect command: ").strip()
        
        if choice == '1':
            scanned, added = ai_scan_simulation(manager)
            if added > 0:
                manager.save_grants()
            auditor.log_run(scanned, added)
            
        elif choice == '2':
            grants = manager.grants
            print(f"\n📊 STATUS REPORT")
            print(f"Total Grants: {len(grants)}")
            high_pri = len([g for g in grants if g.get('priority') == 'HIGH'])
            print(f"High Priority: {high_pri}")
            print(f"Alerts Sent Session: {manager.alerter.alerts_sent}")

        elif choice == '3':
            print("\n🚀 Sending Test Alert...")
            # Send dummy structured data
            manager.alerter.send_webhook({
                "program_name": "TEST GRANT 2026",
                "funding_amount": "$1,000,000",
                "country": "Global",
                "deadline": "2026-12-31",
                "relevance_score": 99,
                "application_link": "https://example.com/test",
                "summary": "🔔 This is a TEST alert."
            })
        
        elif choice == '4':
            print("Goodbye! 👋")
            break

if __name__ == "__main__":
    main()
