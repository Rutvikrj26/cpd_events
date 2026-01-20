#!/bin/bash

# =============================================================================
# CPD Events Backend - Security Audit Script
# =============================================================================
# Runs multiple security scanning tools to identify vulnerabilities
#
# Usage: ./scripts/security_audit.sh
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

echo "🔒 CPD Events Backend - Security Audit"
echo "======================================"
echo ""
echo "Project root: $PROJECT_ROOT"
echo ""

# Create reports directory
mkdir -p security_reports
REPORTS_DIR="$PROJECT_ROOT/security_reports"

# -----------------------------------------------------------------------------
# 1. Check for known vulnerabilities in dependencies (Safety)
# -----------------------------------------------------------------------------
echo "📦 [1/5] Checking dependencies for known vulnerabilities (Safety)..."
echo ""

poetry run safety check --json > "$REPORTS_DIR/safety_report.json" 2>&1 || {
    echo "⚠️  Safety found vulnerabilities. Check $REPORTS_DIR/safety_report.json"
}

poetry run safety check --output=text | tee "$REPORTS_DIR/safety_report.txt" || true
echo ""

# -----------------------------------------------------------------------------
# 2. Alternative dependency check (pip-audit)
# -----------------------------------------------------------------------------
echo "📦 [2/5] Running pip-audit for additional dependency checks..."
echo ""

poetry run pip-audit --format json > "$REPORTS_DIR/pip_audit_report.json" 2>&1 || {
    echo "⚠️  pip-audit found issues. Check $REPORTS_DIR/pip_audit_report.json"
}

poetry run pip-audit --format text | tee "$REPORTS_DIR/pip_audit_report.txt" || true
echo ""

# -----------------------------------------------------------------------------
# 3. Static code analysis for security issues (Bandit)
# -----------------------------------------------------------------------------
echo "🔍 [3/5] Scanning code for security issues (Bandit)..."
echo ""

poetry run bandit -r src/ \
    -f json \
    -o "$REPORTS_DIR/bandit_report.json" \
    --exclude "*/tests/*,*/test_*.py,*/.venv/*" \
    2>&1 || {
    echo "⚠️  Bandit found security issues. Check $REPORTS_DIR/bandit_report.json"
}

# Generate text report for easy reading
poetry run bandit -r src/ \
    -f txt \
    --exclude "*/tests/*,*/test_*.py,*/.venv/*" \
    | tee "$REPORTS_DIR/bandit_report.txt" || true
echo ""

# -----------------------------------------------------------------------------
# 4. Check for hardcoded secrets
# -----------------------------------------------------------------------------
echo "🔑 [4/5] Checking for hardcoded secrets..."
echo ""

# Look for common secret patterns
if command -v grep &> /dev/null; then
    grep -r -i -E "(password|secret|api_key|token)\s*=\s*['\"][^'\"]{8,}['\"]" src/ \
        --include="*.py" \
        --exclude-dir=tests \
        --exclude="test_*.py" \
        --exclude-dir=.venv \
        --exclude-dir=migrations \
        > "$REPORTS_DIR/hardcoded_secrets.txt" 2>&1 || {
        echo "✅ No obvious hardcoded secrets found"
    }
    
    if [ -s "$REPORTS_DIR/hardcoded_secrets.txt" ]; then
        echo "⚠️  Potential hardcoded secrets found!"
        cat "$REPORTS_DIR/hardcoded_secrets.txt"
    else
        echo "✅ No hardcoded secrets detected" | tee "$REPORTS_DIR/hardcoded_secrets.txt"
    fi
else
    echo "⚠️  grep not available, skipping hardcoded secrets check"
fi
echo ""

# -----------------------------------------------------------------------------
# 5. Django security check
# -----------------------------------------------------------------------------
echo "🛡️  [5/5] Running Django security checks..."
echo ""

cd src
poetry run python manage.py check \
    --deploy \
    --settings=config.settings.production \
    2>&1 | tee "$REPORTS_DIR/django_check.txt" || {
    echo "⚠️  Django security check found issues"
}
cd ..
echo ""

# -----------------------------------------------------------------------------
# Generate summary report
# -----------------------------------------------------------------------------
echo "📊 Generating summary report..."
echo ""

cat > "$REPORTS_DIR/SUMMARY.md" << 'EOF'
# Security Audit Summary

**Date:** $(date)
**Project:** CPD Events Backend

## Reports Generated

1. **Safety Report** - Known vulnerabilities in dependencies
   - JSON: `safety_report.json`
   - Text: `safety_report.txt`

2. **Pip Audit Report** - Alternative dependency vulnerability check
   - JSON: `pip_audit_report.json`
   - Text: `pip_audit_report.txt`

3. **Bandit Report** - Static code analysis for security issues
   - JSON: `bandit_report.json`
   - Text: `bandit_report.txt`

4. **Hardcoded Secrets Check** - Search for exposed credentials
   - Text: `hardcoded_secrets.txt`

5. **Django Security Check** - Django-specific security validation
   - Text: `django_check.txt`

## Next Steps

1. Review each report file
2. Prioritize HIGH and CRITICAL vulnerabilities
3. Update vulnerable dependencies: `poetry update <package>`
4. Fix security issues in code identified by Bandit
5. Remove any hardcoded secrets found
6. Address Django security warnings

## Useful Commands

```bash
# Update specific package
poetry update <package-name>

# Update all dependencies
poetry update

# Re-run security audit
./scripts/security_audit.sh
```

EOF

# Replace $(date) with actual date
sed -i "s|\$(date)|$(date '+%Y-%m-%d %H:%M:%S')|g" "$REPORTS_DIR/SUMMARY.md"

echo "✅ Security audit complete!"
echo ""
echo "📁 Reports saved to: $REPORTS_DIR/"
echo ""
echo "📋 Files generated:"
ls -lh "$REPORTS_DIR/"
echo ""
echo "📖 Read the summary: cat $REPORTS_DIR/SUMMARY.md"
echo ""
echo "⚠️  IMPORTANT: Review all reports and address HIGH/CRITICAL issues before deploying!"
