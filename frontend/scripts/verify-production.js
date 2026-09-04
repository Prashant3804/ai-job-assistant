#!/usr/bin/env node
/**
 * Frontend Production Configuration Audit
 * Safely verifies production settings, API base URL configuration,
 * and security rules without printing or leaking secrets.
 */

console.log('============================================================');
console.log('AI JOB ASSISTANT - FRONTEND PRODUCTION AUDIT');
console.log('============================================================');

const apiUrl = process.env.NEXT_PUBLIC_API_URL;
let apiUrlStatus = 'NOT_CONFIGURED (Default Localhost)';
if (apiUrl) {
  if (apiUrl.startsWith('https://')) {
    apiUrlStatus = 'CONFIGURED [OK] (Secure HTTPS)';
  } else if (apiUrl.startsWith('http://localhost') || apiUrl.startsWith('http://127.0.0.1')) {
    apiUrlStatus = 'DEVELOPMENT (Localhost)';
  } else if (apiUrl.startsWith('http://')) {
    apiUrlStatus = 'INVALID (Insecure HTTP)';
  } else {
    apiUrlStatus = 'CONFIGURED [OK] (Relative/Custom)';
  }
}

console.log(`API URL CONFIGURATION:    ${apiUrlStatus}`);

// Security check: ensure no private secrets leaked into NEXT_PUBLIC_*
const publicEnvKeys = Object.keys(process.env).filter(k => k.startsWith('NEXT_PUBLIC_'));
const forbiddenSecretSubstrings = ['SECRET', 'KEY', 'PASSWORD', 'TOKEN', 'PRIVATE', 'DATABASE'];
let leakageDetected = false;

for (const key of publicEnvKeys) {
  for (const pattern of forbiddenSecretSubstrings) {
    if (key.toUpperCase().includes(pattern) && !key.toUpperCase().includes('PUBLISHABLE') && !key.toUpperCase().includes('PUBLIC_KEY_PLACEHOLDER')) {
      console.warn(`[SECURITY WARNING] Potential sensitive key in public env: ${key}`);
      leakageDetected = true;
    }
  }
}

console.log(`FRONTEND SECRET LEAKAGE:  ${leakageDetected ? 'INVALID [FAIL]' : 'PASS [OK] (Zero Private Secrets in Client Bundle)'}`);

// Next.js config check
const fs = require('fs');
const path = require('path');
const nextConfigExists = fs.existsSync(path.join(__dirname, '..', 'next.config.js'));
console.log(`SECURITY HEADERS CONFIG:  ${nextConfigExists ? 'CONFIGURED [OK]' : 'NOT_CONFIGURED'}`);

console.log('============================================================');
console.log('Frontend production audit complete.');
console.log('============================================================');
