#!/bin/bash

# =============================================
# GitHub SBOM Fetcher - Environment Setup Script
# =============================================
# This script sets up a Python virtual environment and installs all required
# dependencies for the GitHub SBOM Fetcher project.
#
# Usage:
#   ./setup_environment.sh      # Just set up the environment
#   ./setup_environment.sh --run  # Set up and run the SBOM fetcher
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
section "GitHub SBOM Fetcher - Environment Setup"
echo "Current directory: $(pwd)"

# Check if Python 3 is installed and meets minimum version requirements
section "Checking Python Installation"
if ! command -v python3 &> /dev/null; then
    error "Python 3 is not installed.\n  Please install Python 3.8 or higher from: https://www.python.org/downloads/"
fi

# Verify Python version (3.8+ required)
PYTHON_VERSION=$(python3 -c "import sys; print('{}.{}'.format(sys.version_info.major, sys.version_info.minor))")
if [ "$(printf '%s\n' "3.8" "$PYTHON_VERSION" | sort -V | head -n1)" != "3.8" ]; then
    error "Python 3.8 or higher is required. Found Python $PYTHON_VERSION"
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
echo -e "\n🚀 Activating virtual environment..."
source venv/bin/activate || error "Failed to activate virtual environment"

# Upgrade pip to the latest version
echo -e "\n🔄 Upgrading pip..."
python -m pip install --upgrade pip || error "Failed to upgrade pip"

# =============================================
# Dependency Installation
# =============================================
section "Installing Dependencies"

# Install project dependencies
echo "📦 Installing dependencies from requirements.txt..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt || error "Failed to install dependencies"
    echo "✅ Dependencies installed successfully"
else
    error "requirements.txt not found. Please ensure you're in the project root directory"
fi
# =============================================
# Post-Installation Checks
# =============================================
section "Running Post-Installation Checks"

# Check for key.json
echo "🔑 Checking for GitHub credentials..."
if [ ! -f "key.json" ]; then
    warning "key.json not found. You'll need to create this file with your GitHub credentials."
    echo "Create a key.json file with the following format:"
    echo '{
  "github_token": "your_github_token_here"
}'
    echo -e "\nYou can create a GitHub personal access token at: https://github.com/settings/tokens"
    echo "Make sure to give it 'repo' scope permissions."
else
    echo "✅ Found key.json"
fi

# =============================================
# Run SBOM Fetcher (if requested)
# =============================================
if [ "$1" = "--run" ]; then
    section "Running SBOM Fetcher"
    if [ -f "fetch_sbom_hierarchy.py" ]; then
        if [ ! -f "key.json" ]; then
            warning "key.json not found. Running in dry-run mode..."
            python fetch_sbom_hierarchy.py --dry-run
        else
            python fetch_sbom_hierarchy.py --debug
        fi
    else
        error "fetch_sbom_hierarchy.py not found"
    fi
fi

# =============================================
# Setup Complete
# =============================================
section "Setup Complete! 🎉"

echo -e "${GREEN}✅ Environment is ready!${NC}"
echo -e "\nNext steps:"
echo "1. Activate the virtual environment:"
echo "   ${YELLOW}source venv/bin/activate${NC}"
echo -e "\n2. Run the SBOM fetcher:"
echo "   ${YELLOW}python fetch_sbom_hierarchy.py [options]${NC}"
echo -e "\n   Example (analyze a specific repository):"
echo "   ${YELLOW}python fetch_sbom_hierarchy.py --repo owner/repo${NC}"
echo -e "\n   For help with all options:"
echo "   ${YELLOW}python fetch_sbom_hierarchy.py --help${NC}"

echo -e "\n💡 ${YELLOW}Tip:${NC} Run ${YELLOW}./setup_environment.sh --run${NC} to set up and run immediately\n"

exit 0
