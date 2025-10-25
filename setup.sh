

!/bin/bash

# =========================================
# CV Management System - Automated Setup
# =========================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored message
print_message() {
    color=$1
    message=$2
    echo -e "${color}${message}${NC}"
}

print_message "$BLUE" "========================================="
print_message "$BLUE" "  CV Management System Setup"
print_message "$BLUE" "========================================="
echo ""

# Check Python version
print_message "$YELLOW" "→ Checking Python version..."
if ! command -v python3 &> /dev/null; then
    print_message "$RED" "✗ Python 3 is not installed. Please install Python 3.9 or higher."
    exit 1
fi

PYTHON_VERSION=$(python3 --version | awk '{print $2}')
print_message "$GREEN" "✓ Python $PYTHON_VERSION found"
echo ""

# Create project directories
print_message "$YELLOW" "→ Creating project directories..."
mkdir -p downloads logs credentials
print_message "$GREEN" "✓ Directories created: downloads/, logs/, credentials/"
echo ""

# Create virtual environment
print_message "$YELLOW" "→ Creating virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    print_message "$GREEN" "✓ Virtual environment created"
else
    print_message "$YELLOW" "⚠ Virtual environment already exists, skipping..."
fi
echo ""

# Activate virtual environment
print_message "$YELLOW" "→ Activating virtual environment..."
source venv/bin/activate
print_message "$GREEN" "✓ Virtual environment activated"
echo ""

# Upgrade pip
print_message "$YELLOW" "→ Upgrading pip..."
pip install --upgrade pip > /dev/null 2>&1
print_message "$GREEN" "✓ pip upgraded"
echo ""

# Install dependencies
print_message "$YELLOW" "→ Installing dependencies (this may take a few minutes)..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt > /dev/null 2>&1
    print_message "$GREEN" "✓ All dependencies installed"
else
    print_message "$RED" "✗ requirements.txt not found"
    exit 1
fi
echo ""

# Create .env file from template
print_message "$YELLOW" "→ Setting up environment configuration..."
if [ ! -f ".env" ]; then
    if [ -f ".env.template" ]; then
        cp .env.template .env
        print_message "$GREEN" "✓ .env file created from template"
        print_message "$YELLOW" "⚠ IMPORTANT: Please edit .env file with your API credentials"
    else
        print_message "$RED" "✗ .env.template not found"
    fi
else
    print_message "$YELLOW" "⚠ .env file already exists, skipping..."
fi
echo ""

# Create .gitignore if it doesn't exist
print_message "$YELLOW" "→ Setting up .gitignore..."
if [ ! -f ".gitignore" ]; then
    cat > .gitignore << 'EOF'
# Environment
.env
.env.local
venv/
ENV/

# Credentials
credentials/
*.json
!requirements.txt

# Python
__pycache__/
*.pyc
*.pyo

# Logs
logs/
*.log

# Downloads
downloads/
temp/

# IDE
.vscode/
.idea/
*.swp

# OS
.DS_Store
Thumbs.db
EOF
    print_message "$GREEN" "✓ .gitignore created"
else
    print_message "$YELLOW" "⚠ .gitignore already exists, skipping..."
fi
echo ""

# Check if credentials file exists
print_message "$YELLOW" "→ Checking Google credentials..."
if [ -f "credentials/google-service-account.json" ]; then
    print_message "$GREEN" "✓ Google service account credentials found"
else
    print_message "$YELLOW" "⚠ Google service account credentials not found"
    print_message "$YELLOW" "  Please download from Google Cloud Console and save to:"
    print_message "$YELLOW" "  credentials/google-service-account.json"
fi
echo ""

# Initialize git repository
print_message "$YELLOW" "→ Initializing git repository..."
if [ ! -d ".git" ]; then
    git init > /dev/null 2>&1
    print_message "$GREEN" "✓ Git repository initialized"
else
    print_message "$YELLOW" "⚠ Git repository already exists, skipping..."
fi
echo ""

# Create README if it doesn't exist
print_message "$YELLOW" "→ Checking documentation..."
if [ -f "README.md" ]; then
    print_message "$GREEN" "✓ README.md found"
else
    print_message "$YELLOW" "⚠ README.md not found"
fi
echo ""

# Summary
print_message "$BLUE" "========================================="
print_message "$BLUE" "  Setup Complete!"
print_message "$BLUE" "========================================="
echo ""

print_message "$GREEN" "✓ Virtual environment created and activated"
print_message "$GREEN" "✓ All dependencies installed"
print_message "$GREEN" "✓ Project structure created"
echo ""

print_message "$YELLOW" "📋 Next Steps:"
echo ""
print_message "$BLUE" "1. Configure Environment Variables:"
echo "   nano .env"
echo "   # Fill in your API credentials"
echo ""

print_message "$BLUE" "2. Add Google Service Account Credentials:"
echo "   # Download from Google Cloud Console"
echo "   # Save to: credentials/google-service-account.json"
echo ""

print_message "$BLUE" "3. Test the Application:"
echo "   python main.py"
echo ""

print_message "$BLUE" "4. Expose Webhook (for local testing):"
echo "   # In a new terminal:"
echo "   ngrok http 5000"
echo ""

print_message "$BLUE" "5. Update Twilio Webhook URL:"
echo "   # Go to Twilio Console"
echo "   # Set webhook to: https://your-ngrok-url/webhook"
echo ""

print_message "$YELLOW" "📚 Documentation:"
echo "   README.md         - Complete setup guide"
echo "   DEPLOYMENT.md     - Production deployment"
echo "   PROJECT_REPORT.md - Technical overview"
echo ""

print_message "$GREEN" "🚀 Ready to start! Run: python main.py"
echo ""

print_message "$YELLOW" "Need help? Check README.md for detailed instructions."