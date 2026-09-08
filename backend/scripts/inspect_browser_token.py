from playwright.sync_api import sync_playwright
import base64
import json
import requests

RAILWAY_API = "https://ai-job-assistant-production-8870.up.railway.app/api/v1"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto('https://ai-job-assistant-ten-ivory.vercel.app/login')
    page.fill('input[type="email"]', 'candidate@jobassistant.ai')
    page.fill('input[type="password"]', 'Password123!')
    page.click('button[type="submit"]')
    page.wait_for_url('**/resume', timeout=15000)
    token = page.evaluate("() => localStorage.getItem('access_token')")
    print('Token in browser:', token[:30] + '...')
    payload_str = base64.b64decode(token.split('.')[1] + '==').decode('utf-8')
    print('Decoded JWT payload:', payload_str)

    # Now inspect /auth/me with that token
    headers = {"Authorization": f"Bearer {token}"}
    me = requests.get(f"{RAILWAY_API}/auth/me", headers=headers).json()
    print('/auth/me response:', me)

    # Inspect /resume with that token
    resumes = requests.get(f"{RAILWAY_API}/resume", headers=headers).json()
    print('/resume count with browser token:', len(resumes))
    for r in resumes:
        print(' - Resume:', r.get('id'), r.get('title'))

    browser.close()
