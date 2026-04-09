import requests
import sys
import json
import time
from datetime import datetime

class GOscraperAPITester:
    def __init__(self, base_url="http://localhost:8000/api"):
        self.base_url = base_url.rstrip("/")
        self.tests_run = 0
        self.tests_passed = 0
        self.session_id = f"test_session_{datetime.now().strftime('%H%M%S')}"

    def run_test(self, name, method, endpoint, expected_status, data=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}" if endpoint else f"{self.base_url}/"
        headers = {'Content-Type': 'application/json'}

        self.tests_run += 1
        print(f"\n[*] Testing {name}...")
        print(f"    URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=60)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=60)
            elif method == 'PATCH':
                response = requests.patch(url, json=data, headers=headers, timeout=60)
            else:
                print(f"    [!] Unsupported method: {method}")
                return False

            status_ok = response.status_code == expected_status
            if status_ok:
                self.tests_passed += 1
                print(f"    [+] Passed - Status {response.status_code}")
                return True
            else:
                print(f"    [-] Failed - Expected {expected_status}, got {response.status_code}")
                print(f"    Response: {response.text}")
                return False
        except Exception as e:
            print(f"    [!] Error: {str(e)}")
            return False

    def test_health(self):
        """Test the health check endpoint"""
        return self.run_test("Health Check", "GET", "health", 200)

    def test_stats(self):
        """Test the statistics endpoint"""
        return self.run_test("Aggregate Stats", "GET", "stats", 200)

    def test_leads_get(self):
        """Test getting leads"""
        return self.run_test("Get Leads", "GET", "leads", 200)

    def test_businesses_get(self):
        """Test getting businesses"""
        return self.run_test("Get Businesses", "GET", "businesses", 200)

    def test_chat(self):
        """Test the AI chat assistant"""
        chat_data = {
            "session_id": self.session_id,
            "message": "Hello, what industries can you scrape?"
        }
        return self.run_test("AI Chat Assistant", "POST", "chat", 200, chat_data)

    def test_bulk_save(self):
        """Test bulk saving business records"""
        bulk_data = [
            {
                "name": "Test Corp",
                "website": "testcorp.com",
                "emails": ["info@testcorp.com"],
                "source": "api_test"
            }
        ]
        return self.run_test("Bulk Business Save", "POST", "businesses/bulk", 200, bulk_data)

    def test_scrape_google(self):
        """Test Google Search scraper (Sync/Legacy)"""
        search_data = {
            "queries": ["fintech startups in london"],
            "max_pages": 1
        }
        return self.run_test("Google Search Scraper", "POST", "search/google", 200, search_data)

    def test_scrape_linkedin(self):
        """Test LinkedIn Scraper (Legacy)"""
        linkedin_data = {
            "company_urls": ["https://www.linkedin.com/company/google"],
            "max_results": 5
        }
        return self.run_test("LinkedIn Scraper", "POST", "search/linkedin", 200, linkedin_data)

def main():
    print("============================================================")
    print("🚀 GOscraper Industrial API v3.0 - Integration Suite")
    print("============================================================")
    
    # Wait a moment for server to be fully ready if it just started
    time.sleep(2)
    
    tester = GOscraperAPITester()
    
    tester.test_health()
    tester.test_stats()
    tester.test_leads_get()
    tester.test_businesses_get()
    tester.test_chat()
    tester.test_bulk_save()
    
    # Note: Scrapers might take longer or fail if API keys are missing
    print("\n[!] Testing Scrapers (Expect longer latency)...")
    tester.test_scrape_google()
    tester.test_scrape_linkedin()

    print("\n" + "="*60)
    print(f"FINAL RESULTS")
    print(f"Tests passed: {tester.tests_passed}/{tester.tests_run}")
    rate = (tester.tests_passed / tester.tests_run) * 100 if tester.tests_run > 0 else 0
    print(f"Success rate: {rate:.1f}%")
    
    if tester.tests_passed == tester.tests_run:
        print("[+] All industrial modules operational.")
    else:
        print("[!] Some components reported failures.")
    print("="*60)

if __name__ == "__main__":
    main()