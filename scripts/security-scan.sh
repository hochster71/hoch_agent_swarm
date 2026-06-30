#!/bin/bash
# Security scanning script for CI/CD pipeline

set -e

echo "========================================"
echo "Security Vulnerability Scanning"
echo "========================================"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

FAILED=0

# Check if scanners are installed
check_tool() {
    if command -v "$1" &> /dev/null; then
        echo -e "${GREEN}✓${NC} $1 found"
        return 0
    else
        echo -e "${YELLOW}!${NC} $1 not installed (skipping)"
        return 1
    fi
}

# Install missing tools
install_scanners() {
    echo ""
    echo "Installing security scanners..."
    
    # npm audit (bundled with npm)
    echo "✓ npm audit (bundled)"
    
    # pip audit
    if ! command -v pip-audit &> /dev/null; then
        pip install pip-audit > /dev/null 2>&1 && echo "✓ pip-audit installed" || echo "! pip-audit install failed"
    fi
    
    # trivy (for container scanning)
    if ! command -v trivy &> /dev/null; then
        echo "Note: Install trivy manually: https://github.com/aquasecurity/trivy#installation"
    else
        echo "✓ trivy found"
    fi
}

# Scan NPM dependencies
scan_npm() {
    echo ""
    echo "Scanning NPM dependencies..."
    if npm audit --production 2>&1 | grep -q "0 vulnerabilities"; then
        echo -e "${GREEN}✓${NC} No NPM vulnerabilities found"
    else
        echo -e "${RED}✗${NC} NPM vulnerabilities found!"
        npm audit --production
        FAILED=$((FAILED + 1))
    fi
}

# Scan Python dependencies
scan_python() {
    echo ""
    echo "Scanning Python dependencies..."
    if command -v pip-audit &> /dev/null; then
        if pip-audit --desc 2>&1 | grep -q "No known vulnerabilities found"; then
            echo -e "${GREEN}✓${NC} No Python vulnerabilities found"
        else
            echo -e "${RED}✗${NC} Python vulnerabilities found!"
            pip-audit --desc
            FAILED=$((FAILED + 1))
        fi
    fi
}

# Scan Docker images
scan_containers() {
    echo ""
    echo "Scanning Docker images..."
    if command -v trivy &> /dev/null; then
        for image in hoch-api:latest hoch-worker:latest hoch-screenshot:latest; do
            if docker image inspect "$image" > /dev/null 2>&1; then
                echo "  Scanning $image..."
                if trivy image --severity HIGH,CRITICAL "$image" 2>&1 | grep -q "0 vulnerabilities"; then
                    echo -e "  ${GREEN}✓${NC} $image: no high/critical vulnerabilities"
                else
                    echo -e "  ${YELLOW}!${NC} $image has vulnerabilities - review output"
                    trivy image --severity HIGH,CRITICAL "$image"
                fi
            fi
        done
    fi
}

# Check for security files
check_security_files() {
    echo ""
    echo "Checking security configurations..."
    
    if [ -f ".env.example" ]; then
        echo -e "${GREEN}✓${NC} .env.example exists"
    else
        echo -e "${RED}✗${NC} .env.example missing"
        FAILED=$((FAILED + 1))
    fi
    
    if [ -f "backend/security.py" ]; then
        echo -e "${GREEN}✓${NC} backend/security.py exists"
    else
        echo -e "${RED}✗${NC} backend/security.py missing"
        FAILED=$((FAILED + 1))
    fi
    
    if grep -q "USER appuser" Dockerfile.api; then
        echo -e "${GREEN}✓${NC} Non-root user in Dockerfile.api"
    else
        echo -e "${RED}✗${NC} Non-root user missing in Dockerfile.api"
        FAILED=$((FAILED + 1))
    fi
    
    if grep -q "HEALTHCHECK" Dockerfile.api; then
        echo -e "${GREEN}✓${NC} HEALTHCHECK in Dockerfile.api"
    else
        echo -e "${RED}✗${NC} HEALTHCHECK missing in Dockerfile.api"
        FAILED=$((FAILED + 1))
    fi
}

# Main execution
main() {
    check_tool "npm"
    check_tool "pip"
    check_tool "docker"
    
    install_scanners
    
    scan_npm
    scan_python
    check_security_files
    
    if [ $FAILED -eq 0 ]; then
        echo ""
        echo -e "${GREEN}========================================"
        echo "✓ All security checks passed!"
        echo "========================================${NC}"
        exit 0
    else
        echo ""
        echo -e "${RED}========================================"
        echo "✗ $FAILED check(s) failed"
        echo "========================================${NC}"
        exit 1
    fi
}

main "$@"
