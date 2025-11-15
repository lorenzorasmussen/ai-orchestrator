#!/bin/bash

# AI Provider Setup Script
# This script helps set up various AI providers for the AI Orchestrator

set -e

echo "🚀 AI Provider Setup Script"
echo "=========================="
echo

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if URL is accessible
check_url() {
    if command_exists curl; then
        curl -s --head --request GET "$1" | grep "200 OK" > /dev/null
    elif command_exists wget; then
        wget -q --spider "$1"
    else
        echo "⚠️  Neither curl nor wget found. Cannot check URL accessibility."
        return 1
    fi
}

# Function to install Python package
install_python_package() {
    echo "📦 Installing Python package: $1"
    pip install "$1" || {
        echo "❌ Failed to install $1"
        return 1
    }
}

# Function to install Node.js package
install_node_package() {
    echo "📦 Installing Node.js package: $1"
    npm install -g "$1" || {
        echo "❌ Failed to install $1"
        return 1
    }
}

echo "🔍 Checking system requirements..."

# Check Python
if command_exists python3; then
    echo "✅ Python 3 found: $(python3 --version)"
else
    echo "❌ Python 3 not found. Please install Python 3.7+"
    exit 1
fi

# Check Node.js (for some providers)
if command_exists node; then
    echo "✅ Node.js found: $(node --version)"
else
    echo "⚠️  Node.js not found. Some providers may require it."
fi

# Check pip
if command_exists pip; then
    echo "✅ pip found"
else
    echo "❌ pip not found. Please install pip."
    exit 1
fi

echo
echo "🔧 Setting up AI Providers..."
echo

# Gemini CLI Setup
setup_gemini() {
    echo "🤖 Setting up Gemini CLI..."
    
    if command_exists gemini; then
        echo "✅ Gemini CLI already installed"
    else
        echo "📦 Installing Google AI SDK..."
        install_python_package "google-cloud-aiplatform"
        install_python_package "google-generativeai"
        
        echo "📝 To complete Gemini CLI setup:"
        echo "   1. Get API key from: https://makersuite.google.com/app/apikey"
        echo "   2. Set environment variable: export GOOGLE_AI_API_KEY='your-api-key'"
        echo "   3. Or use gcloud auth: gcloud auth application-default login"
    fi
    
    # Test Gemini availability
    if command_exists gemini; then
        echo "🧪 Testing Gemini CLI..."
        gemini --version 2>/dev/null && echo "✅ Gemini CLI working" || echo "⚠️  Gemini CLI needs configuration"
    fi
}

# Ollama Setup
setup_ollama() {
    echo "🦙 Setting up Ollama..."
    
    if command_exists ollama; then
        echo "✅ Ollama already installed"
    else
        echo "📦 Installing Ollama..."
        if [[ "$OSTYPE" == "linux-gnu"* ]]; then
            curl -fsSL https://ollama.ai/install.sh | sh
        elif [[ "$OSTYPE" == "darwin"* ]]; then
            if command_exists brew; then
                brew install ollama
            else
                echo "📥 Please download Ollama from: https://ollama.ai/download"
            fi
        else
            echo "📥 Please download Ollama from: https://ollama.ai/download"
        fi
    fi
    
    # Check if Ollama is running
    if check_url "http://localhost:11434/api/version" 2>/dev/null; then
        echo "✅ Ollama server is running"
        
        # Ask about model installation
        echo "🤖 Available models: llama2, codellama, mistral, vicuna"
        read -p "Install a model? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            read -p "Enter model name (e.g., llama2): " model_name
            if [[ -n "$model_name" ]]; then
                echo "📦 Installing $model_name model..."
                ollama pull "$model_name"
            fi
        fi
    else
        echo "⚠️  Ollama server not running. Start with: ollama serve"
    fi
}

# GitHub Copilot Setup
setup_copilot() {
    echo "🐙 Setting up GitHub Copilot CLI..."
    
    if command_exists copilot; then
        echo "✅ GitHub Copilot CLI already installed"
    else
        echo "📦 Installing GitHub Copilot CLI..."
        install_node_package "@githubnext/github-copilot-cli"
    fi
    
    # Test Copilot availability
    if command_exists copilot; then
        echo "🧪 Testing GitHub Copilot CLI..."
        copilot --version 2>/dev/null && echo "✅ GitHub Copilot CLI working" || echo "⚠️  GitHub Copilot CLI needs authentication"
        
        echo "📝 To complete setup:"
        echo "   1. Authenticate: copilot auth"
        echo "   2. Follow the browser authentication flow"
    fi
}

# Qwen Setup
setup_qwen() {
    echo "🧠 Setting up Qwen..."
    
    echo "📦 Installing Qwen dependencies..."
    install_python_package "torch"
    install_python_package "transformers"
    install_python_package "accelerate"
    install_python_package "vllm"
    
    echo "📝 Qwen setup options:"
    echo "   1. Local setup: Requires GPU and significant RAM"
    echo "   2. API setup: Use external API service"
    echo "   3. Docker setup: Use pre-built container"
    
    read -p "Choose setup method (1/2/3): " -n 1 -r
    echo
    
    case $REPLY in
        1)
            echo "🔧 Setting up local Qwen..."
            echo "⚠️  Local setup requires significant resources (8GB+ RAM, GPU recommended)"
            echo "📥 Download instructions: https://github.com/QwenLM/Qwen"
            ;;
        2)
            echo "🌐 Configure API endpoint in ai_providers.json"
            echo "   Example: http://localhost:8000/v1"
            ;;
        3)
            echo "🐳 Docker setup:"
            echo "   docker run -p 8000:8000 qwen/qwen-api-server"
            ;;
        *)
            echo "❌ Invalid choice"
            ;;
    esac
}

# Z.ai Setup
setup_zai() {
    echo "⚡ Setting up Z.ai..."
    
    echo "📝 Z.ai is a commercial service. To set up:"
    echo "   1. Sign up at: https://z.ai"
    echo "   2. Get your API key"
    echo "   3. Update ai_providers.json with your API key"
    echo "   4. Configure endpoint: https://api.z.ai/v1"
    
    # Test API connectivity (will fail without API key, but shows endpoint is reachable)
    if check_url "https://api.z.ai" 2>/dev/null; then
        echo "✅ Z.ai API endpoint is reachable"
    else
        echo "⚠️  Cannot reach Z.ai API endpoint"
    fi
}

# Custom Provider Setup
setup_custom() {
    echo "🔧 Setting up custom OpenAI-compatible provider..."
    
    echo "📝 To configure a custom provider:"
    echo "   1. Ensure it supports OpenAI chat completions API"
    echo "   2. Update ai_providers.json with:"
    echo "      - api_endpoint: Your provider's API URL"
    echo "      - api_key: Your API key (if required)"
    echo "      - model: Model name"
    echo "      - Other parameters as needed"
    
    echo "🧪 Testing API endpoint format..."
    read -p "Enter your API endpoint (e.g., http://localhost:8000/v1): " api_endpoint
    
    if [[ -n "$api_endpoint" ]]; then
        if check_url "$api_endpoint/models" 2>/dev/null; then
            echo "✅ API endpoint is reachable"
        else
            echo "⚠️  Cannot reach API endpoint. Check URL and network connectivity."
        fi
    fi
}

# Main setup menu
main_menu() {
    echo "🎯 Select providers to set up:"
    echo "1) Gemini CLI"
    echo "2) Ollama"
    echo "3) GitHub Copilot"
    echo "4) Qwen"
    echo "5) Z.ai"
    echo "6) Custom OpenAI-compatible provider"
    echo "7) Set up all providers"
    echo "8) Exit"
    echo
    
    while true; do
        read -p "Enter your choice (1-8): " -n 1 -r
        echo
        
        case $REPLY in
            1)
                setup_gemini
                break
                ;;
            2)
                setup_ollama
                break
                ;;
            3)
                setup_copilot
                break
                ;;
            4)
                setup_qwen
                break
                ;;
            5)
                setup_zai
                break
                ;;
            6)
                setup_custom
                break
                ;;
            7)
                setup_gemini
                setup_ollama
                setup_copilot
                setup_qwen
                setup_zai
                break
                ;;
            8)
                echo "👋 Exiting setup script"
                exit 0
                ;;
            *)
                echo "❌ Invalid choice. Please enter 1-8."
                ;;
        esac
    done
}

# Configuration validation
validate_config() {
    echo "🔍 Validating configuration..."
    
    if [[ -f "ai_providers.json" ]]; then
        echo "✅ Configuration file found"
        
        # Validate JSON syntax
        if python3 -c "import json; json.load(open('ai_providers.json'))" 2>/dev/null; then
            echo "✅ Configuration file is valid JSON"
        else
            echo "❌ Configuration file has invalid JSON syntax"
            return 1
        fi
    else
        echo "⚠️  Configuration file not found. Creating default..."
        python3 ai_provider_orchestrator.py --help > /dev/null 2>&1 && echo "✅ Default configuration created" || echo "❌ Failed to create default configuration"
    fi
}

# Post-setup summary
setup_summary() {
    echo
    echo "🎉 Setup Summary"
    echo "==============="
    echo
    echo "📋 Next steps:"
    echo "1. Review and update ai_providers.json with your API keys and preferences"
    echo "2. Test individual providers:"
    echo "   python3 ai_provider_orchestrator.py --list-providers"
    echo "3. Start using the orchestrator:"
    echo "   python3 ai_provider_orchestrator.py --interactive"
    echo
    echo "📚 For detailed documentation, see README.md"
    echo "🐛 Report issues at: https://github.com/lorenzorasmussen/ai-orchestrator/issues"
    echo
}

# Main execution
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main_menu
    validate_config
    setup_summary
fi