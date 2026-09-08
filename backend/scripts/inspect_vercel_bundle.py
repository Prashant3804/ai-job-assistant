import requests
import re

def main():
    r = requests.get('https://ai-job-assistant-ten-ivory.vercel.app/resume')
    print('GET /resume status:', r.status_code)
    scripts = re.findall(r'src="(/_next/static/[^"]+)"', r.text)
    print('Scripts count:', len(scripts))

    for s in scripts:
        s_url = 'https://ai-job-assistant-ten-ivory.vercel.app' + s
        s_res = requests.get(s_url)
        hits = []
        if 'getAuthToken' in s_res.text: hits.append('getAuthToken')
        if 'access_token' in s_res.text: hits.append('access_token')
        if 'ai-job-assistant-production-8870.up.railway.app' in s_res.text: hits.append('Railway URL')
        if 'Your session has expired' in s_res.text: hits.append('Your session has expired')
        if 'Authentication token required' in s_res.text: hits.append('Authentication token required')
        if 'localhost:8000' in s_res.text: hits.append('localhost:8000')
        print(s, '->', hits)

if __name__ == '__main__':
    main()
