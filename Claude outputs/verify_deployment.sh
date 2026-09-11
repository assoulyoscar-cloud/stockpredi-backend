#!/bin/bash
# StockPredi Phase 2 Deployment Verification Script
# Usage: ./verify_deployment.sh
# This script runs all verification tests after deployment

set -e

FRONTEND_URL="https://stockpredi.vercel.app"
BACKEND_URL="https://stockpredi-backend.onrender.com"

echo "=========================================="
echo "StockPredi Phase 2 - Deployment Verification"
echo "=========================================="
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

# Function to test endpoint
test_endpoint() {
  local name=$1
  local url=$2
  local expected_status=$3

  echo -n "Testing $name... "
  response=$(curl -s -w "\n%{http_code}" "$url" 2>&1 || echo "error")
  status=$(echo "$response" | tail -1)

  if [ "$status" = "$expected_status" ]; then
    echo -e "${GREEN}✓ PASS${NC} (Status: $status)"
    ((TESTS_PASSED++))
  else
    echo -e "${RED}✗ FAIL${NC} (Expected: $expected_status, Got: $status)"
    ((TESTS_FAILED++))
  fi
}

# Function to test JSON endpoint
test_json_endpoint() {
  local name=$1
  local url=$2

  echo -n "Testing $name... "
  response=$(curl -s -w "\n%{http_code}" "$url" 2>&1 || echo "error")
  status=$(echo "$response" | tail -1)
  body=$(echo "$response" | head -n-1)

  if [ "$status" = "200" ]; then
    if echo "$body" | grep -q "{"; then
      echo -e "${GREEN}✓ PASS${NC} (JSON response)"
      ((TESTS_PASSED++))
    else
      echo -e "${YELLOW}⚠ WARNING${NC} (Non-JSON response)"
      ((TESTS_FAILED++))
    fi
  else
    echo -e "${RED}✗ FAIL${NC} (Status: $status)"
    ((TESTS_FAILED++))
  fi
}

# ===== HEALTH CHECKS =====
echo ""
echo "1. HEALTH CHECKS"
echo "---"
test_endpoint "Frontend Health" "$FRONTEND_URL" "200"
test_endpoint "Backend Health" "$BACKEND_URL/health" "200"
echo ""

# ===== FRONTEND ROUTES =====
echo "2. FRONTEND ROUTES"
echo "---"
test_endpoint "Login Route" "$FRONTEND_URL/login" "200"
test_endpoint "Signup Route" "$FRONTEND_URL/signup" "200"
test_endpoint "F&B Landing" "$FRONTEND_URL/industries/food-beverage" "200"
echo ""

# ===== BACKEND API ENDPOINTS =====
echo "3. BACKEND API ENDPOINTS"
echo "---"
test_json_endpoint "Sectors List" "$BACKEND_URL/api/sectors"
test_json_endpoint "F&B Products" "$BACKEND_URL/api/sectors/fob/products"
echo ""

# ===== CORS HEADERS =====
echo "4. CORS HEADERS"
echo "---"
echo -n "Checking CORS headers... "
cors_response=$(curl -s -I -H "Origin: $FRONTEND_URL" "$BACKEND_URL/health" 2>&1)
if echo "$cors_response" | grep -qi "Access-Control-Allow-Origin"; then
  echo -e "${GREEN}✓ PASS${NC}"
  ((TESTS_PASSED++))
else
  echo -e "${RED}✗ FAIL${NC}"
  ((TESTS_FAILED++))
fi
echo ""

# ===== SECURITY HEADERS =====
echo "5. SECURITY HEADERS"
echo "---"
echo -n "Checking CSP header... "
csp_response=$(curl -s -I "$FRONTEND_URL" 2>&1)
if echo "$csp_response" | grep -qi "Content-Security-Policy"; then
  echo -e "${GREEN}✓ PASS${NC}"
  ((TESTS_PASSED++))
else
  echo -e "${YELLOW}⚠ WARNING${NC} (CSP not found)"
  ((TESTS_FAILED++))
fi

echo -n "Checking X-Frame-Options... "
if echo "$csp_response" | grep -qi "X-Frame-Options"; then
  echo -e "${GREEN}✓ PASS${NC}"
  ((TESTS_PASSED++))
else
  echo -e "${YELLOW}⚠ WARNING${NC} (X-Frame-Options not found)"
  ((TESTS_FAILED++))
fi

echo -n "Checking HSTS header... "
if echo "$csp_response" | grep -qi "Strict-Transport-Security"; then
  echo -e "${GREEN}✓ PASS${NC}"
  ((TESTS_PASSED++))
else
  echo -e "${YELLOW}⚠ WARNING${NC} (HSTS not found)"
  ((TESTS_FAILED++))
fi
echo ""

# ===== RESPONSE TIMES =====
echo "6. RESPONSE TIMES"
echo "---"
echo -n "Frontend response time... "
start_time=$(date +%s%N)
curl -s -o /dev/null "$FRONTEND_URL"
end_time=$(date +%s%N)
response_ms=$(( (end_time - start_time) / 1000000 ))
echo "${GREEN}${response_ms}ms${NC}"

echo -n "Backend response time... "
start_time=$(date +%s%N)
curl -s -o /dev/null "$BACKEND_URL/health"
end_time=$(date +%s%N)
response_ms=$(( (end_time - start_time) / 1000000 ))
echo "${GREEN}${response_ms}ms${NC}"
echo ""

# ===== SUMMARY =====
echo "=========================================="
echo "VERIFICATION SUMMARY"
echo "=========================================="
echo -e "Tests Passed: ${GREEN}$TESTS_PASSED${NC}"
echo -e "Tests Failed: ${RED}$TESTS_FAILED${NC}"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
  echo -e "${GREEN}✓ ALL TESTS PASSED${NC}"
  echo ""
  echo "StockPredi Phase 2 is ready for production!"
  exit 0
else
  echo -e "${YELLOW}⚠ SOME TESTS FAILED${NC}"
  echo ""
  echo "Review failures above and address before going live."
  exit 1
fi
