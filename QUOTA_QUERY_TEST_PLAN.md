# Quota Query Improvements - Testing & Verification Plan

## Overview
This document describes how to test and verify the quota query improvements that add retry logic, better filtering, and error handling.

## Quick Start - Test the Fix Locally

### Step 1: Prepare Test Environment
```bash
# Make sure you have valid AWS credentials
# Create a test file: test_quota_query.py
```

### Step 2: Test Code
```python
import json
import requests

# Start your Flask app first (locally or on server)
# Default: http://localhost:5000

def test_quota_query():
    """Test the improved quota query endpoint"""
    
    # Get these from your AWS account
    payload = {
        "access_key": "YOUR_AWS_ACCESS_KEY",
        "secret_key": "YOUR_AWS_SECRET_KEY", 
        "regions": ["us-east-1"],  # Start with one region
        "quota_types": ["tpm", "tpd"],
        "models": ["Claude Sonnet 4.5"],
        "force_refresh": False  # First run: builds cache
    }
    
    response = requests.post(
        "http://localhost:5000/api/query_quotas",
        json=payload,
        timeout=30
    )
    
    result = response.json()
    print(f"Status: {result.get('ok')}")
    print(f"Total quotas: {result.get('total')}")
    print(f"Errors: {result.get('errors')}")
    print(f"Quotas sample:")
    for q in result.get('quotas', [])[:3]:
        print(f"  - {q['name']}: {q.get('value')} (default: {q.get('default_value')})")
    
    return result

if __name__ == "__main__":
    result = test_quota_query()
```

## What to Verify

### 1. Quota Completeness ✓
**Expected:** All Claude quotas for selected models should be returned
- [ ] No missing TPM quotas
- [ ] No missing TPD quotas  
- [ ] Cross-region quotas included if applicable
- [ ] Batch inference quotas EXCLUDED (as expected)

**How to check:**
```bash
# Run query with debug output
# Check server logs for: 
# "[Quota Query Debug] Found X quotas from code_map with Y entries"
# Compare X (results) with Y (expected from cache)
```

### 2. Retry Logic Under Load ✓
**Expected:** Query succeeds even if AWS throttles
- [ ] First run with `force_refresh: true` doesn't fail under throttling
- [ ] Retries with exponential backoff (2s, 4s, 8s)
- [ ] Success rate increases vs old implementation

**How to test:**
```bash
# Test 1: Force refresh (rebuilds entire quota map)
curl -X POST http://localhost:5000/api/query_quotas \
  -H "Content-Type: application/json" \
  -d '{
    "access_key": "...",
    "secret_key": "...",
    "regions": ["us-east-1"],
    "force_refresh": true
  }' \
  --max-time 60

# Check that it doesn't fail with 500 error
```

### 3. Performance ✓
**Expected metrics:**
- First query (rebuild cache): 2-3 seconds
- Subsequent queries: 500ms-1s per region
- No timeouts

**How to measure:**
```bash
# Time the first query
time curl -X POST http://localhost:5000/api/query_quotas ...

# Time a subsequent query
time curl -X POST http://localhost:5000/api/query_quotas ...
```

### 4. Multi-Region Queries ✓
**Expected:** Handle 3-5 regions concurrently without issues
- [ ] 3 regions: ~1-2 seconds
- [ ] 5 regions: ~2-3 seconds
- [ ] All regions succeed or show specific error

**How to test:**
```json
{
  "access_key": "...",
  "secret_key": "...",
  "regions": ["us-east-1", "eu-west-1", "ap-southeast-1"],
  "quota_types": ["tpm", "tpd"],
  "models": ["Claude Sonnet 4.5", "Claude Opus 5"]
}
```

### 5. Cache Persistence ✓
**Expected:** `outputs/quota_codes.json` is created and reused
- [ ] File exists after first query: `outputs/quota_codes.json`
- [ ] File contains ~100+ entries (all Claude quotas)
- [ ] File is used for subsequent queries (faster)
- [ ] `force_refresh: true` rebuilds the file

**How to check:**
```bash
# Check file size
ls -lh outputs/quota_codes.json

# View sample content
cat outputs/quota_codes.json | jq 'keys | .[0:5]'
```

### 6. Error Handling ✓
**Expected:** Clear error messages for common issues
- [ ] Permission errors show IAM hints
- [ ] Throttling errors are retried (not shown to user)
- [ ] Invalid regions caught early
- [ ] Invalid credentials reported clearly

**How to test:**
```bash
# Test 1: Invalid credentials
curl -X POST http://localhost:5000/api/query_quotas \
  -d '{"access_key": "AKIAIOSFODNN7EXAMPLE", "secret_key": "invalid", ...}'

# Test 2: Missing permissions (intentionally)
# Use an IAM user without servicequotas permission

# Test 3: No regions specified
curl -X POST http://localhost:5000/api/query_quotas \
  -d '{"access_key": "...", "secret_key": "...", "regions": []}'
```

## Deployment Testing

### On EC2 Production

**Before deployment:**
```bash
# Backup current version
cd ~/app
git stash

# Test current version one more time
curl https://your-cloudfront-domain.com/api/query_quotas -X POST ...
```

**Deploy new version:**
```bash
# Pull new code
git pull

# Restart app
sudo systemctl restart bedrock-app

# Check service status
sudo systemctl status bedrock-app

# Check logs
sudo journalctl -u bedrock-app -n 50 -f
```

**Verify after deployment:**
```bash
# Same test queries as Step 2
curl https://your-cloudfront-domain.com/api/query_quotas -X POST ...

# Check for any errors in server logs
```

## Expected Improvements

### Before Fix
- Sometimes returns 30-40 quotas when 48 available
- Fails under AWS throttling (retry 500 errors)
- Batch quotas polluted the results
- No debug information

### After Fix  
- Always returns complete quota set (48 quotas for all Claude models)
- Retries automatically on throttling
- Clean quota list (batch/customization excluded)
- Debug logs show quota count and map size
- Consistent results across multiple runs

## Troubleshooting During Testing

### Q: Still getting incomplete quotas?
**A:**
1. Check cache: `ls outputs/quota_codes.json` 
2. Force rebuild: `force_refresh: true`
3. Check logs for errors: `sudo journalctl -u bedrock-app -n 100`
4. Verify IAM permissions

### Q: Query is slow (takes 5+ seconds)?
**A:**
1. First run always slower (building cache) - this is expected
2. Reduce number of regions/models being queried
3. Check AWS throttling in logs: look for "ThrottlingException"

### Q: "Permission Denied" errors?
**A:**
1. Check IAM user has these permissions:
   - `servicequotas:GetServiceQuota`
   - `servicequotas:GetAWSDefaultServiceQuota`
   - `servicequotas:ListAWSDefaultServiceQuotas`
2. Test with root AWS credentials first to isolate issue

### Q: Cache not updating after `force_refresh`?
**A:**
1. Check `/outputs/` directory exists: `mkdir -p ~/app/outputs`
2. Check directory permissions: `chmod 755 ~/app/outputs`
3. Restart app: `sudo systemctl restart bedrock-app`

## Success Criteria ✓

**All of the following should be true:**
- [ ] First query (with rebuild) completes in <5 seconds
- [ ] Subsequent queries complete in <2 seconds
- [ ] All expected quotas returned (no missing TPD/TPM)
- [ ] Batch inference quotas are excluded
- [ ] Multi-region queries work (3+ regions)
- [ ] Error messages are clear and actionable
- [ ] Cache file is created and persisted
- [ ] No 500 errors on repeated queries
- [ ] Works identically locally and on EC2

## Rollback Plan

If issues arise:
```bash
cd ~/app
git revert <commit_hash>
git push
sudo systemctl restart bedrock-app
```

---

**Questions or issues?** Check the `QUOTA_FIXES.md` documentation file for detailed technical information.
