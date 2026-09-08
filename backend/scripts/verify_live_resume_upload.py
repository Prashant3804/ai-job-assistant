import io
import json
import requests
import fitz

RAILWAY_API = "https://ai-job-assistant-production-8870.up.railway.app/api/v1"

def main():
    print("=" * 60)
    print("LIVE RESUME UPLOAD & AUTHENTICATION VERIFICATION")
    print("=" * 60)

    # Step 1: Login
    login_payload = {
        "email": "candidate@jobassistant.ai",
        "password": "Password123!",
    }
    print(f"\n1. Authenticating with candidate credentials against {RAILWAY_API}/auth/login...")
    res = requests.post(f"{RAILWAY_API}/auth/login", json=login_payload, timeout=15)
    print(f"   Login Status: {res.status_code}")
    if res.status_code != 200:
        print(f"   Login failed: {res.text}")
        return

    token_data = res.json()
    token = token_data.get("access_token")
    print(f"   JWT Obtained: {token[:25]}... (length {len(token)})")

    # Generate sample test PDF
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text(
        (50, 72),
        "Harsh Vardhan\nharsh.candidate@example.com | +91 9876543210\n"
        "Senior Full Stack & AI Systems Engineer\n"
        "Skills: Python, FastAPI, React, Next.js, PostgreSQL, Docker, PyTorch\n"
        "Experience: 5 years designing scalable cloud architectures and ML microservices.\n"
        "Education: B.Tech in Computer Science, IIT Delhi"
    )
    pdf_bytes = doc.tobytes()
    doc.close()

    # Step 2: Test unauthenticated upload (must fail with 401)
    print("\n2. Testing unauthenticated upload (Expected 401)...")
    files = {"file": ("harsh_vardhan_resume.pdf", pdf_bytes, "application/pdf")}
    data = {"title": "Harsh Vardhan - Senior Engineer"}
    unauth_res = requests.post(f"{RAILWAY_API}/resume/upload", data=data, files=files, timeout=15)
    print(f"   Unauthenticated status: {unauth_res.status_code}")
    print(f"   Unauthenticated response: {unauth_res.text}")

    # Step 3: Test authenticated upload
    print("\n3. Testing authenticated upload with Bearer token...")
    files = {"file": ("harsh_vardhan_resume.pdf", pdf_bytes, "application/pdf")}
    auth_headers = {"Authorization": f"Bearer {token}"}
    auth_res = requests.post(f"{RAILWAY_API}/resume/upload", headers=auth_headers, data=data, files=files, timeout=30)
    print(f"   Authenticated status: {auth_res.status_code}")
    if auth_res.status_code in [200, 201]:
        upload_data = auth_res.json()
        resume_id = upload_data.get("resume_id")
        print(f"   Uploaded Resume ID: {resume_id}")
        structured = upload_data.get("structured_data", {})
        print(f"   Candidate Name: {structured.get('personal', {}).get('name')}")
        print(f"   Candidate Skills: {structured.get('skills', {})}")
        print(f"   Raw Text preview: {upload_data.get('raw_text', '')[:120]}...")
    else:
        print(f"   Authenticated upload failed: {auth_res.text}")

    # Step 4: Verify GET /resume
    print("\n4. Verifying GET /resume...")
    get_res = requests.get(f"{RAILWAY_API}/resume", headers=auth_headers, timeout=15)
    print(f"   GET /resume status: {get_res.status_code}")
    if get_res.status_code == 200:
        resumes = get_res.json()
        print(f"   Resumes count: {len(resumes)}")
        for r in resumes[:3]:
            print(f"   - ID: {r.get('id')}, Title: {r.get('title')}, Created: {r.get('created_at')}")
    else:
        print(f"   GET /resume error: {get_res.text}")

    # Step 5: Verify GET /resume/profile
    print("\n5. Verifying GET /resume/profile...")
    profile_res = requests.get(f"{RAILWAY_API}/resume/profile", headers=auth_headers, timeout=15)
    print(f"   GET /resume/profile status: {profile_res.status_code}")
    if profile_res.status_code == 200:
        profile = profile_res.json()
        print(f"   Profile Headline: {profile.get('headline')}")
        print(f"   Profile Location: {profile.get('location')}")
        print(f"   Profile Skills Count: {len(profile.get('skills', []))}")
        for s in profile.get('skills', [])[:5]:
            print(f"     * {s.get('name')} ({s.get('category')})")
    else:
        print(f"   GET /resume/profile error: {profile_res.text}")

if __name__ == "__main__":
    main()
