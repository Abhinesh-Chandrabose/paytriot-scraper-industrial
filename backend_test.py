import requests
import sys
import json
from datetime import datetime

class GOscraperAPITester:
    def __init__(self, base_url="https://web-scraper-30.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.session_id = f"test_session_{datetime.now().strftime('%H%M%S')}"

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}" if endpoint else f"{self.api_url}/"
        default_headers = {'Content-Type': 'application/json'}
        if headers:
            default_headers.update(headers)

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=default_headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=default_headers, timeout=10)
            elif method == 'DELETE':
                response = requests.delete(url, headers=default_headers, timeout=10)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    print(f"   Response: {json.dumps(response_data, indent=2)[:200]}...")
                except:
                    print(f"   Response: {response.text[:200]}...")
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                print(f"   Response: {response.text[:300]}")

            return success, response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text

        except requests.exceptions.Timeout:
            print(f"❌ Failed - Request timed out")
            return False, {}
        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_health_check(self):
        """Test API health check"""
        return self.run_test("API Health Check", "GET", "", 200)

    def test_businesses_get(self):
        """Test get businesses list"""
        return self.run_test("Get Businesses List", "GET", "businesses", 200)

    def test_businesses_post(self):
        """Test create business record"""
        test_business = {
            "name": "Test Company",
            "website": "https://test.com",
            "emails": ["test@test.com"],
            "phones": ["+1234567890"],
            "sector": "Technology",
            "source": "manual"
        }
        return self.run_test("Create Business Record", "POST", "businesses", 200, test_business)

    def test_businesses_export_csv(self):
        """Test CSV export"""
        return self.run_test("Export Businesses CSV", "GET", "businesses/export/csv", 200)

    def test_search_history(self):
        """Test get search history"""
        return self.run_test("Get Search History", "GET", "search/history", 200)

    def test_chat_basic(self):
        """Test basic chat functionality"""
        chat_data = {
            "session_id": self.session_id,
            "message": "Hello, what can you help me with?"
        }
        return self.run_test("AI Chat Basic Test", "POST", "chat", 200, chat_data)

    def test_chat_history(self):
        """Test get chat history"""
        return self.run_test("Get Chat History", "GET", f"chat/history/{self.session_id}", 200)

    def test_businesses_clear(self):
        """Test clear all businesses"""
        return self.run_test("Clear All Businesses", "DELETE", "businesses", 200)

    def test_google_search_async(self):
        """Test Google search async endpoint (without waiting for completion)"""
        search_data = {
            "queries": ["test company contact information"],
            "country_code": "us",
            "language_code": "en",
            "max_pages": 1,
            "results_per_page": 5
        }
        print("\n⚠️  Note: Testing async endpoint only - not waiting for Apify actor completion")
        return self.run_test("Google Search Async", "POST", "search/google/async", 200, search_data)

    def test_linkedin_search_async(self):
        """Test LinkedIn search async endpoint (without waiting for completion)"""
        linkedin_data = {
            "company_urls": ["https://linkedin.com/company/google"],
            "max_results": 10
        }
        print("\n⚠️  Note: Testing async endpoint only - not waiting for Apify actor completion")
        return self.run_test("LinkedIn Search Async", "POST", "search/linkedin/async", 200, linkedin_data)

def main():
    print("🚀 Starting GOscraper API Testing...")
    print("=" * 60)
    
    tester = GOscraperAPITester()
    
    # Test basic API functionality
    print("\n📋 BASIC API TESTS")
    print("-" * 30)
    tester.test_health_check()
    tester.test_businesses_get()
    tester.test_search_history()
    
    # Test business CRUD operations
    print("\n📊 BUSINESS CRUD TESTS")
    print("-" * 30)
    tester.test_businesses_post()
    tester.test_businesses_export_csv()
    
    # Test AI chat functionality
    print("\n🤖 AI CHAT TESTS")
    print("-" * 30)
    tester.test_chat_basic()
    tester.test_chat_history()
    
    # Test async scraping endpoints (without waiting for completion)
    print("\n🔍 SCRAPING ASYNC TESTS")
    print("-" * 30)
    tester.test_google_search_async()
    tester.test_linkedin_search_async()
    
    # Cleanup
    print("\n🧹 CLEANUP TESTS")
    print("-" * 30)
    tester.test_businesses_clear()
    
    # Print final results
    print("\n" + "=" * 60)
    print(f"📊 FINAL RESULTS")
    print(f"Tests passed: {tester.tests_passed}/{tester.tests_run}")
    success_rate = (tester.tests_passed / tester.tests_run * 100) if tester.tests_run > 0 else 0
    print(f"Success rate: {success_rate:.1f}%")
    
    if success_rate >= 80:
        print("🎉 Backend API testing completed successfully!")
        return 0
    else:
        print("⚠️  Some backend API tests failed. Check the details above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())