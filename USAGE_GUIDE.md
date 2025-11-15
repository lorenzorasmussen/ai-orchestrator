# AI Provider Orchestrator - Usage Guide

## Quick Start

### 1. Installation
```bash
# Clone the repository
git clone https://github.com/lorenzorasmussen/ai-orchestrator.git
cd ai-orchestrator

# Install dependencies
pip install -r requirements.txt

# Make scripts executable
chmod +x setup_providers.sh
chmod +x ai_provider_orchestrator.py
chmod +x zed_integration.py
chmod +x web_interface.py
chmod +x test_integration.py
```

### 2. Provider Setup
```bash
# Run the automated setup script
./setup_providers.sh

# Or manually configure providers
# Edit ai_providers.json with your API keys and preferences
```

### 3. Test Integration
```bash
# Run comprehensive tests
python3 test_integration.py

# Run specific test category
python3 test_integration.py --category availability

# Run tests for specific provider
python3 test_integration.py --provider gemini
```

## Usage Methods

### Method 1: Command Line Interface (CLI)
```bash
# List available providers
python3 ai_provider_orchestrator.py --list-providers

# Start a session
python3 ai_provider_orchestrator.py --start gemini

# Send a message
python3 ai_provider_orchestrator.py --send SESSION_ID "Explain this Python code"

# Interactive mode
python3 ai_provider_orchestrator.py --interactive
```

### Method 2: Web Interface
```bash
# Start the web interface
python3 web_interface.py --host 127.0.0.1 --port 5000

# Open browser to http://localhost:5000
# Use the web UI to manage sessions and chat
```

### Method 3: Zed Editor Integration
```bash
# Use Zed integration with context
python3 zed_integration.py --explain gemini --file my_code.py --selection "code snippet"

# Generate code
python3 zed_integration.py --generate copilot "Create a REST API endpoint" --file api.py

# Fix code issues
python3 zed_integration.py --fix qwen "TypeError: cannot concatenate str and int" --file app.py
```

### Method 4: Python API
```python
import asyncio
from ai_provider_orchestrator import AIProviderOrchestrator

async def main():
    orchestrator = AIProviderOrchestrator()
    
    # Start session
    session_id = await orchestrator.start_session("gemini")
    
    # Send message
    response = await orchestrator.send_message(
        session_id, 
        "Write a Python function to calculate factorial"
    )
    print(response)
    
    # Get history
    history = orchestrator.get_session_history(session_id)
    print(history)
    
    # Stop session
    await orchestrator.stop_session(session_id)

asyncio.run(main())
```

## Provider-Specific Setup

### Gemini CLI
```bash
# Install Google AI SDK
pip install google-generativeai

# Get API key from https://makersuite.google.com/app/apikey
export GOOGLE_AI_API_KEY="your-api-key"

# Test
python3 ai_provider_orchestrator.py --start gemini
```

### Ollama
```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Pull a model
ollama pull llama2

# Start server
ollama serve

# Test
python3 ai_provider_orchestrator.py --start ollama
```

### GitHub Copilot
```bash
# Install CLI
npm install -g @githubnext/github-copilot-cli

# Authenticate
copilot auth

# Test
python3 ai_provider_orchestrator.py --start copilot
```

### Qwen (Local)
```bash
# Install dependencies
pip install torch transformers accelerate vllm

# Start API server
python -m vllm.entrypoints.openai.api_server \
  --model Qwen/Qwen-Code-7B-Chat \
  --port 8000

# Update ai_providers.json with endpoint: http://localhost:8000/v1
```

### Z.ai
```bash
# Sign up at https://z.ai
# Get API key
# Update ai_providers.json with your Z.ai API key

# Test
python3 ai_provider_orchestrator.py --start zai
```

## Configuration

### Provider Configuration (ai_providers.json)
```json
{
  "name": "my-provider",
  "provider_type": "openai-compatible",
  "api_endpoint": "https://api.example.com/v1",
  "api_key": "your-api-key",
  "model": "model-name",
  "max_tokens": 2048,
  "temperature": 0.7,
  "timeout": 30,
  "env_vars": {
    "CUSTOM_VAR": "value"
  },
  "additional_args": ["--custom-arg"]
}
```

### Zed Editor Configuration
1. Copy `zed_config.json` contents to your Zed settings
2. Update `/path/to/ai-orchestrator/` to your installation path
3. Restart Zed
4. Use keyboard shortcuts:
   - `Ctrl+Alt+A+E`: Explain code
   - `Ctrl+Alt+A+I`: Improve code
   - `Ctrl+Alt+A+G`: Generate code
   - `Ctrl+Alt+A+F`: Fix code
   - `Ctrl+Alt+A+C`: Start chat

## Advanced Usage

### Multi-Provider Comparison
```bash
# Using CLI
python3 ai_provider_orchestrator.py --start gemini
python3 ai_provider_orchestrator.py --start ollama
python3 ai_provider_orchestrator.py --start copilot

# Send same question to all
python3 ai_provider_orchestrator.py --send GEMINI_SESSION "What is the best Python web framework?"
python3 ai_provider_orchestrator.py --send OLLAMA_SESSION "What is the best Python web framework?"
python3 ai_provider_orchestrator.py --send COPILOT_SESSION "What is the best Python web framework?"
```

### Session Management
```bash
# List all active sessions
python3 ai_provider_orchestrator.py --list-sessions

# Get session history
python3 ai_provider_orchestrator.py --history SESSION_ID

# Stop specific session
python3 ai_provider_orchestrator.py --stop SESSION_ID

# Stop all sessions
python3 ai_provider_orchestrator.py --stop-all
```

### Web Interface Features
- **Dashboard**: Overview of all providers and sessions
- **Real-time Chat**: WebSocket-based chat interface
- **Provider Comparison**: Compare responses across providers
- **Session History**: View conversation history
- **Configuration Management**: Edit provider settings

### Error Handling
```python
try:
    session_id = await orchestrator.start_session("gemini")
    response = await orchestrator.send_message(session_id, "Hello")
except ValueError as e:
    print(f"Configuration error: {e}")
except RuntimeError as e:
    print(f"Provider error: {e}")
except TimeoutError as e:
    print(f"Request timeout: {e}")
```

## Troubleshooting

### Common Issues

1. **Provider not available**
   ```bash
   # Check if provider is installed
   which gemini  # or ollama, copilot, etc.
   
   # Check configuration
   python3 ai_provider_orchestrator.py --list-providers
   ```

2. **API authentication errors**
   ```bash
   # Verify API key is set
   echo $GOOGLE_AI_API_KEY
   
   # Test API connectivity
   curl -H "Authorization: Bearer $API_KEY" https://api.example.com/models
   ```

3. **Session timeouts**
   ```json
   // Increase timeout in ai_providers.json
   {
     "timeout": 60  // seconds
   }
   ```

4. **Web interface not accessible**
   ```bash
   # Check if port is available
   netstat -an | grep 5000
   
   # Try different port
   python3 web_interface.py --port 8080
   ```

### Debug Mode
```bash
# Enable debug logging
python3 ai_provider_orchestrator.py --interactive 2>&1 | tee debug.log

# Web interface debug mode
python3 web_interface.py --debug
```

### Performance Optimization
```json
{
  "max_tokens": 1024,     // Reduce for faster responses
  "temperature": 0.1,      // Lower for more deterministic responses
  "timeout": 15            // Adjust based on your needs
}
```

## Integration Examples

### Code Review Workflow
```bash
# 1. Start session with code-focused provider
python3 ai_provider_orchestrator.py --start copilot

# 2. Send code for review
python3 ai_provider_orchestrator.py --send SESSION_ID "Review this code for security issues:
import os
exec(os.environ['USER_INPUT'])"

# 3. Get suggestions and apply fixes
```

### Learning Workflow
```bash
# 1. Start session with explanation-focused provider
python3 ai_provider_orchestrator.py --start gemini

# 2. Ask for explanations
python3 ai_provider_orchestrator.py --send SESSION_ID "Explain how decorators work in Python"

# 3. Follow up with questions
python3 ai_provider_orchestrator.py --send SESSION_ID "Can you show a practical example?"
```

### Documentation Generation
```bash
# 1. Use Zed integration
python3 zed_integration.py --generate qwen "Generate API documentation" --file my_api.py

# 2. Review and refine generated documentation
# 3. Add to your project
```

## Best Practices

1. **Choose the right provider for the task**:
   - Gemini: General coding and explanations
   - Ollama: Privacy-focused, local processing
   - Copilot: Code completion and suggestions
   - Qwen: Programming and technical tasks

2. **Manage sessions efficiently**:
   - Stop sessions when done to free resources
   - Use conversation history for context
   - Clear history for new topics

3. **Secure your API keys**:
   - Use environment variables
   - Don't commit API keys to version control
   - Rotate keys regularly

4. **Monitor performance**:
   - Use the test suite to benchmark providers
   - Monitor response times
   - Adjust timeouts based on usage patterns

## Support

- **Documentation**: [README.md](README.md)
- **Issues**: [GitHub Issues](https://github.com/lorenzorasmussen/ai-orchestrator/issues)
- **Discussions**: [GitHub Discussions](https://github.com/lorenzorasmussen/ai-orchestrator/discussions)
- **Tests**: Run `python3 test_integration.py` for diagnostics

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.