#!/bin/bash

# Verification script for CTFd Docker Challenges v3.0.0 migration
# Tests that all jQuery, inline handlers, and Bootstrap 4 patterns are removed

set -e

PLUGIN_DIR="docker_challenges"
FAILED=0

echo "🔍 CTFd Docker Challenges Migration Verification"
echo "================================================"
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test 1: Check for jQuery usage
echo "📋 Test 1: Checking for jQuery usage..."
JQUERY_MATCHES=$(grep -r '\$(' ${PLUGIN_DIR}/assets/*.js 2>/dev/null | grep -v 'CTFd.lib.\$' | wc -l || echo 0)
if [ "$JQUERY_MATCHES" -eq 0 ]; then
    echo -e "${GREEN}✅ PASS${NC}: No jQuery usage found in plugin code"
else
    echo -e "${RED}❌ FAIL${NC}: Found $JQUERY_MATCHES jQuery references"
    grep -n '\$(' ${PLUGIN_DIR}/assets/*.js | grep -v 'CTFd.lib.\$'
    FAILED=$((FAILED + 1))
fi
echo ""

# Test 2: Check for inline onclick handlers
echo "📋 Test 2: Checking for inline onclick handlers..."
ONCLICK_MATCHES=$(grep -r 'onclick=' ${PLUGIN_DIR}/templates/*.html ${PLUGIN_DIR}/assets/*.html 2>/dev/null | wc -l || echo 0)
if [ "$ONCLICK_MATCHES" -eq 0 ]; then
    echo -e "${GREEN}✅ PASS${NC}: No inline onclick handlers found"
else
    echo -e "${RED}❌ FAIL${NC}: Found $ONCLICK_MATCHES inline onclick handlers"
    grep -n 'onclick=' ${PLUGIN_DIR}/templates/*.html ${PLUGIN_DIR}/assets/*.html
    FAILED=$((FAILED + 1))
fi
echo ""

# Test 3: Check for Bootstrap 4 data-toggle attributes
echo "📋 Test 3: Checking for Bootstrap 4 data attributes..."
DATA_TOGGLE_MATCHES=$(grep -r 'data-toggle' ${PLUGIN_DIR}/ 2>/dev/null | wc -l || echo 0)
if [ "$DATA_TOGGLE_MATCHES" -eq 0 ]; then
    echo -e "${GREEN}✅ PASS${NC}: No Bootstrap 4 data-toggle attributes found"
else
    echo -e "${RED}❌ FAIL${NC}: Found $DATA_TOGGLE_MATCHES data-toggle attributes (should be data-bs-toggle)"
    grep -n 'data-toggle' ${PLUGIN_DIR}/
    FAILED=$((FAILED + 1))
fi
echo ""

# Test 4: Check for Alpine.js components
echo "📋 Test 4: Checking for Alpine.js directives..."
ALPINE_MATCHES=$(grep -r 'x-data\|x-show\|x-text\|x-model\|@click' ${PLUGIN_DIR}/templates/*.html ${PLUGIN_DIR}/assets/*.html 2>/dev/null | wc -l || echo 0)
if [ "$ALPINE_MATCHES" -gt 0 ]; then
    echo -e "${GREEN}✅ PASS${NC}: Found $ALPINE_MATCHES Alpine.js directives"
else
    echo -e "${YELLOW}⚠️  WARN${NC}: No Alpine.js directives found (expected in docker_config.html and view.html)"
    FAILED=$((FAILED + 1))
fi
echo ""

# Test 5: Check for Bootstrap 5 data-bs attributes
echo "📋 Test 5: Checking for Bootstrap 5 data attributes..."
DATA_BS_MATCHES=$(grep -r 'data-bs-toggle\|data-bs-dismiss' ${PLUGIN_DIR}/ 2>/dev/null | wc -l || echo 0)
if [ "$DATA_BS_MATCHES" -gt 0 ]; then
    echo -e "${GREEN}✅ PASS${NC}: Found $DATA_BS_MATCHES Bootstrap 5 data attributes"
else
    echo -e "${RED}❌ FAIL${NC}: No Bootstrap 5 data attributes found (should have data-bs-toggle, data-bs-dismiss)"
    FAILED=$((FAILED + 1))
fi
echo ""

# Test 6: Check for ChallengeResponse import
echo "📋 Test 6: Checking for ChallengeResponse imports..."
CHALLENGE_RESPONSE=$(grep -r 'from CTFd.plugins.challenges import.*ChallengeResponse' ${PLUGIN_DIR}/models/*.py 2>/dev/null | wc -l || echo 0)
if [ "$CHALLENGE_RESPONSE" -eq 2 ]; then
    echo -e "${GREEN}✅ PASS${NC}: Found ChallengeResponse imports in both challenge types"
else
    echo -e "${RED}❌ FAIL${NC}: Expected 2 ChallengeResponse imports, found $CHALLENGE_RESPONSE"
    grep -n 'ChallengeResponse' ${PLUGIN_DIR}/models/*.py
    FAILED=$((FAILED + 1))
fi
echo ""

# Test 7: Check for fetch() API usage
echo "📋 Test 7: Checking for fetch() API usage..."
FETCH_MATCHES=$(grep -r 'fetch(' ${PLUGIN_DIR}/assets/*.js 2>/dev/null | wc -l || echo 0)
if [ "$FETCH_MATCHES" -gt 0 ]; then
    echo -e "${GREEN}✅ PASS${NC}: Found $FETCH_MATCHES fetch() API calls"
else
    echo -e "${RED}❌ FAIL${NC}: No fetch() API usage found (expected in form JS files)"
    FAILED=$((FAILED + 1))
fi
echo ""

# Test 8: Check for $.get or $.getJSON usage
echo "📋 Test 8: Checking for jQuery AJAX patterns..."
JQUERY_AJAX=$(grep -rE '\$\.(get|getJSON|ajax)' ${PLUGIN_DIR}/assets/*.js 2>/dev/null | wc -l || echo 0)
if [ "$JQUERY_AJAX" -eq 0 ]; then
    echo -e "${GREEN}✅ PASS${NC}: No jQuery AJAX patterns found"
else
    echo -e "${RED}❌ FAIL${NC}: Found $JQUERY_AJAX jQuery AJAX calls (should use fetch())"
    grep -n -E '\$\.(get|getJSON|ajax)' ${PLUGIN_DIR}/assets/*.js
    FAILED=$((FAILED + 1))
fi
echo ""

# Summary
echo "================================================"
if [ "$FAILED" -eq 0 ]; then
    echo -e "${GREEN}🎉 ALL TESTS PASSED!${NC}"
    echo ""
    echo "Migration verification successful!"
    echo "Ready for integration testing with docker-compose.test.yml"
    exit 0
else
    echo -e "${RED}❌ $FAILED TEST(S) FAILED${NC}"
    echo ""
    echo "Please review the failures above and fix the issues."
    exit 1
fi
