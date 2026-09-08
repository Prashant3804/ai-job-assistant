import os
import time
import json
import tempfile
import fitz
from playwright.sync_api import sync_playwright

VERCEL_URL = "https://ai-job-assistant-ten-ivory.vercel.app"
RAILWAY_API = "https://ai-job-assistant-production-8870.up.railway.app/api/v1"

def create_sample_pdf(filepath: str):
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text(
        (50, 72),
        "Harsh Vardhan\n"
        "harsh.candidate@example.com | +91 9876543210\n"
        "Senior Full Stack & AI Systems Engineer\n"
        "Skills: Python, FastAPI, React, Next.js, PostgreSQL, Docker, PyTorch\n"
        "Experience: 5 years designing scalable cloud architectures and ML microservices.\n"
        "Education: B.Tech in Computer Science, IIT Delhi"
    )
    doc.save(filepath)
    doc.close()

def main():
    print("=" * 70)
    print("REAL BROWSER VERIFICATION: VERCEL RESUME UPLOAD")
    print("=" * 70)

    # Create temporary PDF resume
    tmp_dir = tempfile.mkdtemp()
    pdf_path = os.path.join(tmp_dir, "harsh_browser_test_resume.pdf")
    create_sample_pdf(pdf_path)
    print(f"Created test resume PDF: {pdf_path}")

    network_logs = {
        "login_request": None,
        "upload_request": None,
        "upload_response": None,
        "auth_header_status": "MISSING",
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        page = context.new_page()

        # Intercept network requests
        def on_request(req):
            if "/api/v1/auth/login" in req.url:
                network_logs["login_request"] = {
                    "url": req.url,
                    "method": req.method,
                }
            elif "/api/v1/resume/upload" in req.url:
                headers = req.headers
                has_auth = "authorization" in headers and bool(headers["authorization"].strip())
                network_logs["upload_request"] = {
                    "url": req.url,
                    "method": req.method,
                    "content_type": headers.get("content-type", "Not specified"),
                    "has_auth": has_auth,
                }
                network_logs["auth_header_status"] = "PRESENT" if has_auth else "MISSING"
                print(f"\n>>> [BROWSER NETWORK EVENT] Intercepted {req.method} {req.url}")
                print(f"    Authorization Header: {network_logs['auth_header_status']}")
                print(f"    Content-Type: {headers.get('content-type', 'None')[:60]}...")

        def on_response(res):
            if "/api/v1/resume/upload" in res.url:
                try:
                    body = res.json()
                except Exception:
                    body = res.text()
                network_logs["upload_response"] = {
                    "status": res.status,
                    "body": body,
                }
                print(f">>> [BROWSER NETWORK EVENT] Received Response {res.status}")

        page.on("request", on_request)
        page.on("response", on_response)

        # -------------------------------------------------------------
        # Step 1: Visit /resume unauthenticated to verify guard / UI
        # -------------------------------------------------------------
        print(f"\n1. Navigating to {VERCEL_URL}/resume (Unauthenticated)...")
        page.goto(f"{VERCEL_URL}/resume", wait_until="networkidle")
        time.sleep(1)

        # Check for unauthenticated indicators
        content = page.content()
        has_session_banner = "Candidate Session Required" in content or "Sign in required" in content or "Sign In" in content
        print(f"   Unauthenticated warning / Sign In button visible: {has_session_banner}")

        # -------------------------------------------------------------
        # Step 2: Navigate to Login and authenticate
        # -------------------------------------------------------------
        print(f"\n2. Navigating to {VERCEL_URL}/login...")
        page.goto(f"{VERCEL_URL}/login?redirect=/resume", wait_until="networkidle")
        time.sleep(1)

        print("   Filling login form with candidate credentials...")
        test_email = os.getenv("TEST_CANDIDATE_EMAIL", "")
        test_password = os.getenv("TEST_CANDIDATE_PASSWORD", "")
        if not test_email or not test_password:
            raise ValueError("TEST_CANDIDATE_EMAIL and TEST_CANDIDATE_PASSWORD environment variables must be provided.")
        page.fill('input[type="email"]', test_email)
        page.fill('input[type="password"]', test_password)

        print("   Clicking 'Sign In as Candidate' button...")
        page.click('button[type="submit"]')

        # Wait for navigation back to /resume
        page.wait_for_url("**/resume", timeout=15000)
        print("   Redirected to /resume successfully.")
        time.sleep(2)

        # Verify token in browser localStorage
        token_in_storage = page.evaluate("() => localStorage.getItem('access_token')")
        print(f"   Browser Storage Check: Token exists in localStorage = {bool(token_in_storage)}")

        # -------------------------------------------------------------
        # Step 3: Trigger Resume File Upload from the browser
        # -------------------------------------------------------------
        print("\n3. Triggering file upload on Resume page...")
        # Target the file input
        file_input = page.locator('input[type="file"]')
        file_input.set_input_files(pdf_path)
        print(f"   Set input files to {os.path.basename(pdf_path)}")

        # Wait for the upload request and response
        print("   Waiting for upload network request to finish (up to 45s)...")
        page.wait_for_timeout(5000)

        # Check for status message in UI
        for _ in range(20):
            ui_text = page.content()
            if "Resume extracted and candidate profile updated successfully!" in ui_text:
                print("   UI Notification: 'Resume extracted and candidate profile updated successfully!' FOUND!")
                break
            elif "Extraction failed" in ui_text:
                print(f"   UI Notification: Extraction failed encountered!")
                break
            time.sleep(2)

        # Capture final screenshot for proof
        screenshot_path = os.path.join(tmp_dir, "browser_resume_upload_result.png")
        page.screenshot(path=screenshot_path)
        print(f"   Captured browser screenshot: {screenshot_path}")

        browser.close()

    # -------------------------------------------------------------
    # Step 4: Summary of Browser Verification
    # -------------------------------------------------------------
    print("\n" + "=" * 70)
    print("BROWSER NETWORK INSPECTION RESULTS")
    print("=" * 70)
    print(f"Request URL:              {network_logs['upload_request']['url'] if network_logs['upload_request'] else 'No request captured'}")
    print(f"HTTP Method:              {network_logs['upload_request']['method'] if network_logs['upload_request'] else 'N/A'}")
    print(f"Content-Type:             {network_logs['upload_request']['content_type'] if network_logs['upload_request'] else 'N/A'}")
    print(f"Authorization Header:     {network_logs['auth_header_status']}")
    print(f"Response Status:          {network_logs['upload_response']['status'] if network_logs['upload_response'] else 'N/A'}")

    if network_logs["upload_response"] and isinstance(network_logs["upload_response"]["body"], dict):
        resp_data = network_logs["upload_response"]["body"]
        print(f"Resume ID:                {resp_data.get('resume_id')}")
        print(f"Extraction Message:       {resp_data.get('message')}")
        parsed_name = resp_data.get("structured_data", {}).get("personal", {}).get("name")
        print(f"Parsed Candidate Name:    {parsed_name}")
        skills = resp_data.get("structured_data", {}).get("skills", {})
        print(f"Parsed Skills:            {skills}")

    print("=" * 70)

if __name__ == "__main__":
    main()
