#!/bin/bash

# =============================================
# SBOM Fetcher v2.0 - Environment Setup Script
# =============================================
# This script sets up a Python virtual environment and installs all required
# dependencies for the production-grade SBOM Fetcher.
#
# Usage:
#   ./setup_environment.sh           # Set up the environment
#   ./setup_environment.sh --test    # Set up and run tests
#   ./setup_environment.sh --run     # Set up and run the SBOM fetcher
#
# After setup, you can activate the environment manually with:
#   source venv/bin/activate
# =============================================

# Exit on error and print commands as they're executed
set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print section headers
section() {
    echo -e "\n${GREEN}=== $1 ===${NC}"
}

# Function to print warnings
warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Function to print errors and exit
error() {
    echo -e "${RED}❌ Error: $1${NC}" >&2
    exit 1
}

# Print header
echo -e "${BLUE}"
cat << "EOF"
╔═══════════════════════════════════════════════════════╗
║   SBOM Fetcher v2.0 - Environment Setup               ║
║   Production-Grade Architecture                       ║
╚═══════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"
echo "Current directory: $(pwd)"

# Check if Python 3 is installed and meets minimum version requirements
section "Checking Python Installation"
if ! command -v python3 &> /dev/null; then
    error "Python 3 is not installed.\n  Please install Python 3.9 or higher from: https://www.python.org/downloads/"
fi

# Verify Python version (3.9+ required)
PYTHON_VERSION=$(python3 -c "import sys; print('{}.{}'.format(sys.version_info.major, sys.version_info.minor))")
if [ "$(printf '%s\n' "3.9" "$PYTHON_VERSION" | sort -V | head -n1)" != "3.9" ]; then
    error "Python 3.9 or higher is required. Found Python $PYTHON_VERSION"
fi
echo "✅ Using Python $PYTHON_VERSION"

# Check for pip
if ! command -v pip3 &> /dev/null; then
    error "pip3 is not installed. Please install pip for Python 3."
fi

echo "✅ pip is installed"

# =============================================
# Virtual Environment Setup
# =============================================
section "Setting Up Virtual Environment"

if [ ! -d "venv" ]; then
    echo "🔧 Creating virtual environment..."
    python3 -m venv venv
    echo "✅ Virtual environment created"
else
    echo "ℹ️  Virtual environment already exists"
fi

# Activate the virtual environment
if [[ -n "$VIRTUAL_ENV" ]]; then
  echo "✅ Virtual environment is active: $VIRTUAL_ENV"
else
  echo -e "\n🚀 Activating virtual environment..."
  source venv/bin/activate || error "Failed to activate virtual environment"
fi

# Upgrade pip to the latest version
echo -e "\n🔄 Upgrading pip..."
python -m pip install --upgrade pip -q || error "Failed to upgrade pip"
echo "✅ pip upgraded"

# =============================================
# Dependency Installation
# =============================================
section "Installing Dependencies"

# Install project dependencies
echo "📦 Installing runtime dependencies from requirements.txt..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt -q || error "Failed to install dependencies"
    echo "✅ Runtime dependencies installed successfully"
else
    error "requirements.txt not found. Please ensure you're in the project root directory"
fi

# Install development dependencies from pyproject.toml
echo -e "\n📦 Installing development dependencies (pytest, black, mypy, etc.)..."
if [ -f "pyproject.toml" ]; then
    pip install -e ".[dev]" -q || warning "Failed to install some development dependencies"
    echo "✅ Development dependencies installed"
else
    warning "pyproject.toml not found. Skipping dev dependencies."
fi

# =============================================
# Post-Installation Checks
# =============================================
section "Running Post-Installation Checks"

# Verify package is importable
echo "🔍 Verifying package installation..."
python -c "import sbom_fetcher; print(f'✅ Package version: {sbom_fetcher.__version__}')" || error "Failed to import sbom_fetcher package"

# Check for keys.json
echo -e "\n🔑 Checking for GitHub credentials..."
if [ ! -f "keys.json" ]; then
    warning "keys.json not found. You'll need to create this file with your GitHub credentials."
    echo -e "\nCreate a keys.json file with the following format:"
    cat << 'EOF'
{
  "github_token": "your_github_token_here"
}
EOF
    echo -e "\n💡 You can create a GitHub personal access token at:"
    echo "   https://github.com/settings/tokens"
    echo "   Make sure to give it 'repo' scope permissions."
else
    echo "✅ Found keys.json"
fi

# =============================================
# Run Tests (if requested)
# =============================================
if [ "$1" = "--test" ]; then
    section "Running Tests"
    echo "🧪 Running test suite with pytest..."
    
    if [ -d "tests" ] && [ "$(ls -A tests 2>/dev/null)" ]; then
        pytest tests/ -v --cov=sbom_fetcher --cov-report=term-missing || warning "Some tests failed"
    else
        warning "No tests found in tests/ directory. Tests need to be adapted from archive_v1/"
        echo "ℹ️  Original tests are in archive_v1/tests/"
        echo "   Adapt them by updating imports to use the new package structure."
    fi
    exit 0
fi

# =============================================
# Run SBOM Fetcher (if requested)
# =============================================
if [ "$1" = "--run" ]; then
    section "Running SBOM Fetcher"
    
    if [ ! -f "keys.json" ]; then
        error "keys.json not found. Please create it with your GitHub token before running."
    fi
    
    echo "🚀 Running SBOM Fetcher with sample repository..."
    echo -e "\n${YELLOW}Enter repository owner (e.g., tedg-dev):${NC}"
    read -r GH_USER
    echo -e "${YELLOW}Enter repository name (e.g., beatBot):${NC}"
    read -r GH_REPO
    
    echo -e "\n📥 Fetching SBOM for $GH_USER/$GH_REPO..."
    python -m sbom_fetcher --gh-user "$GH_USER" --gh-repo "$GH_REPO" --debug || error "SBOM fetch failed"
    
    exit 0
fi

# =============================================
# Setup Complete
# =============================================
section "Setup Complete! 🎉"

echo -e "${GREEN}✅ Environment is ready!${NC}"
echo -e "\n${BLUE}Next steps:${NC}"
echo -e "\n1️⃣  Activate the virtual environment:"
echo "   source venv/bin/activate"

echo -e "\n2️⃣  Run the SBOM fetcher:"
echo -e "   ${GREEN}python -m sbom_fetcher --gh-user OWNER --gh-repo REPO${NC}"
echo -e "\n   Examples:"
echo "   python -m sbom_fetcher --gh-user tedg-dev --gh-repo beatBot"
echo "   python -m sbom_fetcher --gh-user tedg-dev --gh-repo beatBot --debug"
echo "   python -m sbom_fetcher --gh-user tedg-dev --gh-repo beatBot --output-dir ./my_sboms"

echo -e "\n3️⃣  Optional: Run tests (after adapting from archive_v1/tests/):"
echo "   pytest tests/ -v"

echo -e "\n${BLUE}📚 Documentation:${NC}"
echo "   - README.md - User guide"
echo "   - REFACTORING_COMPLETE.md - Architecture documentation"
echo "   - archive_v1/ - Original implementation"

echo -e "\n${BLUE}💡 Quick Tips:${NC}"
echo "   - Run: ./setup_environment.sh --run   (interactive mode)"
echo "   - Run: ./setup_environment.sh --test  (run test suite)"
echo "   - Use --debug flag for detailed logging"
echo "   - Check pyproject.toml for project configuration"

echo -e "\n${BLUE}🏗️  Architecture:${NC}"
echo "   Domain       → Pure business models & exceptions"
echo "   Infrastructure → HTTP client, filesystem, config"
echo "   Services     → GitHub API, mappers, parsers, reporters"
echo "   Application  → CLI & entry point"

echo -e "\n${GREEN}Happy SBOM fetching! 🚀${NC}\n"
