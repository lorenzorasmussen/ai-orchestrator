# AI Provider Orchestrator for Zed Editor

A comprehensive system to manage multiple AI provider sessions from within Zed, supporting Gemini CLI, Qwen-code, Ollama, GitHub Copilot, and other AI providers.

## Features

- **Multi-Provider Support**: Gemini CLI, Ollama, GitHub Copilot, OpenAI-compatible APIs
- **Session Management**: Start, stop, and monitor multiple AI sessions simultaneously
- **Conversation History**: Track and retrieve conversation history for each session
- **Async Operations**: Non-blocking operations for better performance
- **Configuration Management**: JSON-based provider configurations
- **Interactive CLI**: User-friendly command-line interface
- **Error Handling**: Robust error handling and recovery

## Supported Providers

### 1. Gemini CLI
- **Command**: `gemini`
- **Models**: gemini-pro, gemini-pro-vision
- **Setup**: Install [Google AI Studio CLI](https://ai.google.dev/cli)

### 2. Ollama
- **API**: HTTP API on `http://localhost:11434`
- **Models**: llama2, codellama, mistral, and more
- **Setup**: Install [Ollama](https://ollama.ai/) and pull models

### 3. GitHub Copilot
- **Command**: `copilot`
- **Features**: Code explanation and generation
- **Setup**: Install [GitHub Copilot CLI](https://github.com/github/copilot-cli)

### 4. OpenAI-Compatible APIs
- **Examples**: Qwen-code, Z.ai, custom APIs
- **Protocol**: OpenAI chat completions API
- **Setup**: Configure endpoint and API key

## Installation

```bash
# Clone the repository
git clone https://github.com/lorenzorasmussen/ai-orchestrator.git
cd ai-orchestrator

# Install dependencies
pip install -r requirements.txt

# Make the script executable
chmod +x ai_provider_orchestrator.py
```

## Configuration

Edit `ai_providers.json` to configure your AI providers:

```json
{
  "name": "gemini",
  "provider_type": "gemini-cli",
  "command": "gemini",
  "model": "gemini-pro",
  "max_tokens": 2048,
  "temperature": 0.7,
  "timeout": 30,
  "env_vars": {},
  "additional_args": []
}
```

### Provider Configuration Options

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Unique provider name |
| `provider_type` | string | Provider type (gemini-cli, ollama, github-copilot, openai-compatible) |
| `command` | string | CLI command (for CLI-based providers) |
| `api_endpoint` | string | HTTP API endpoint (for API-based providers) |
| `api_key` | string | API key (for API-based providers) |
| `model` | string | Model name |
| `max_tokens` | integer | Maximum response tokens |
| `temperature` | float | Response randomness (0.0-1.0) |
| `timeout` | integer | Request timeout in seconds |
| `env_vars` | object | Environment variables |
| `additional_args` | array | Additional command-line arguments |

## Usage

### Command Line Interface

```bash
# List available providers
python ai_provider_orchestrator.py --list-providers

# List active sessions
python ai_provider_orchestrator.py --list-sessions

# Start a session with a provider
python ai_provider_orchestrator.py --start gemini

# Send a message to a session
python ai_provider_orchestrator.py --send SESSION_ID "Hello, how are you?"

# Get session history
python ai_provider_orchestrator.py --history SESSION_ID

# Stop a session
python ai_provider_orchestrator.py --stop SESSION_ID

# Stop all sessions
python ai_provider_orchestrator.py --stop-all
```

### Interactive Mode

```bash
# Start interactive mode
python ai_provider_orchestrator.py --interactive
```

Interactive commands:
- `providers` - List available providers
- `sessions` - List active sessions
- `start <provider>` - Start new session
- `stop <session_id>` - Stop session
- `send <session_id> <message>` - Send message
- `history <session_id>` - Get conversation history
- `quit` - Exit and stop all sessions

### Python API

```python
import asyncio
from ai_provider_orchestrator import AIProviderOrchestrator

async def main():
    # Initialize orchestrator
    orchestrator = AIProviderOrchestrator()
    
    # Start a session
    session_id = await orchestrator.start_session("gemini")
    
    # Send a message
    response = await orchestrator.send_message(
        session_id, 
        "Explain this Python code: print('Hello, World!')"
    )
    print(response)
    
    # Get conversation history
    history = orchestrator.get_session_history(session_id)
    print(history)
    
    # Stop the session
    await orchestrator.stop_session(session_id)

asyncio.run(main())
```

## Integration with Zed Editor

### Method 1: Zed Terminal
1. Open Zed terminal (`Ctrl+` or `Cmd+``)
2. Navigate to the ai-orchestrator directory
3. Run interactive mode: `python ai_provider_orchestrator.py --interactive`

### Method 2: Zed Commands (Advanced)
Create a Zed command in your settings:

```json
{
  "context": "Editor",
  "bindings": {
    "ctrl+alt+a": "ai_orchestrator::toggle_session"
  }
}
```

### Method 3: External Tool Integration
Add to your Zed settings:

```json
{
  "external_tools": [
    {
      "name": "AI Orchestrator",
      "command": "python",
      "args": ["path/to/ai_provider_orchestrator.py", "--interactive"],
      "working_directory": "$PROJECT_ROOT"
    }
  ]
}
```

## Provider Setup Guides

### Gemini CLI
```bash
# Install Google AI CLI
pip install google-cloud-aiplatform

# Authenticate
gcloud auth application-default login

# Set project
gcloud config set project YOUR_PROJECT_ID
```

### Ollama
```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Pull a model
ollama pull llama2
ollama pull codellama

# Start Ollama server
ollama serve
```

### GitHub Copilot CLI
```bash
# Install GitHub Copilot CLI
npm install -g @githubnext/github-copilot-cli

# Authenticate
copilot auth
```

### Qwen-code (Local Setup)
```bash
# Clone Qwen repository
git clone https://github.com/QwenLM/Qwen.git
cd Qwen

# Install dependencies
pip install -r requirements.txt

# Start API server
python -m vllm.entrypoints.openai.api_server \
  --model Qwen/Qwen-Code-7B-Chat \
  --port 8000
```

## Examples

### Code Explanation Session
```bash
# Start session with GitHub Copilot
python ai_provider_orchestrator.py --start copilot

# Send code for explanation
python ai_provider_orchestrator.py --send SESSION_ID "Explain this function:
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)"
```

### Code Generation with Ollama
```bash
# Start session with Ollama
python ai_provider_orchestrator.py --start ollama

# Generate code
python ai_provider_orchestrator.py --send SESSION_ID "Write a Python function to validate email addresses"
```

### Multi-Provider Comparison
```bash
# Start sessions with different providers
python ai_provider_orchestrator.py --start gemini
python ai_provider_orchestrator.py --start ollama
python ai_provider_orchestrator.py --start copilot

# Send same question to all
python ai_provider_orchestrator.py --send GEMINI_SESSION "What is the best way to sort a list in Python?"
python ai_provider_orchestrator.py --send OLLAMA_SESSION "What is the best way to sort a list in Python?"
python ai_provider_orchestrator.py --send COPILOT_SESSION "What is the best way to sort a list in Python?"
```

## Troubleshooting

### Common Issues

1. **Provider not available**
   - Check if the CLI tool is installed and in PATH
   - Verify API endpoints are accessible
   - Check authentication credentials

2. **Session fails to start**
   - Verify provider configuration
   - Check network connectivity
   - Review error logs

3. **Timeout errors**
   - Increase timeout value in configuration
   - Check network stability
   - Verify model availability

### Debug Mode

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Performance Tips

1. **Use appropriate timeouts** for different providers
2. **Limit concurrent sessions** to avoid resource exhaustion
3. **Clear conversation history** for long sessions
4. **Use streaming** for long responses (when supported)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

### Adding New Providers

1. Create a new provider class inheriting from `AIProvider`
2. Implement required abstract methods:
   - `start_session()`
   - `send_message()`
   - `stop_session()`
   - `is_available()`
3. Add provider type to `ProviderType` enum
4. Update provider factory in `_create_provider()`
5. Add configuration example

## License

MIT License - see LICENSE file for details.

## Support

- **Issues**: [GitHub Issues](https://github.com/lorenzorasmussen/ai-orchestrator/issues)
- **Discussions**: [GitHub Discussions](https://github.com/lorenzorasmussen/ai-orchestrator/discussions)
- **Documentation**: [Wiki](https://github.com/lorenzorasmussen/ai-orchestrator/wiki)

## Changelog

### v1.0.0 (2025-11-15)
- Initial release
- Support for Gemini CLI, Ollama, GitHub Copilot, OpenAI-compatible APIs
- Session management and conversation history
- Interactive CLI interface
- Configuration management
- Zed Editor integration guide