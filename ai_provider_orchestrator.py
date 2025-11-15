#!/usr/bin/env python3
"""
AI Provider Orchestration System for Zed Editor

A comprehensive system to manage multiple AI provider sessions from within Zed,
supporting Gemini CLI, Qwen-code, Ollama, GitHub Copilot, and other AI providers.

Author: OpenCode Research Assistant
License: MIT
"""

import asyncio
import json
import logging
import os
import subprocess
import sys
import tempfile
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import threading
import time


class ProviderType(Enum):
    """Supported AI provider types."""
    GEMINI_CLI = "gemini-cli"
    QWEN_CODE = "qwen-code"
    OLLAMA = "ollama"
    GITHUB_COPILOT = "github-copilot"
    OPENAI_COMPATIBLE = "openai-compatible"
    CUSTOM = "custom"


class SessionStatus(Enum):
    """AI session status states."""
    INACTIVE = "inactive"
    STARTING = "starting"
    ACTIVE = "active"
    ERROR = "error"
    TERMINATING = "terminating"


@dataclass
class ProviderConfig:
    """Configuration for an AI provider."""
    name: str
    provider_type: ProviderType
    command: Optional[str] = None
    api_endpoint: Optional[str] = None
    api_key: Optional[str] = None
    model: Optional[str] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    timeout: int = 30
    env_vars: Dict[str, str] = field(default_factory=dict)
    additional_args: List[str] = field(default_factory=list)


@dataclass
class AISession:
    """Represents an active AI session."""
    session_id: str
    provider_config: ProviderConfig
    status: SessionStatus
    process: Optional[subprocess.Popen] = None
    created_at: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)
    conversation_history: List[Dict[str, Any]] = field(default_factory=list)


class AIProvider(ABC):
    """Abstract base class for AI providers."""
    
    def __init__(self, config: ProviderConfig):
        self.config = config
        self.logger = logging.getLogger(f"ai_provider.{config.name}")
    
    @abstractmethod
    async def start_session(self) -> AISession:
        """Start a new AI session."""
        pass
    
    @abstractmethod
    async def send_message(self, session: AISession, message: str) -> str:
        """Send a message to AI session."""
        pass
    
    @abstractmethod
    async def stop_session(self, session: AISession) -> bool:
        """Stop an AI session."""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is available."""
        pass


class GeminiCLIProvider(AIProvider):
    """Gemini CLI provider implementation."""
    
    async def start_session(self) -> AISession:
        """Start Gemini CLI session."""
        session_id = str(uuid.uuid4())
        session = AISession(
            session_id=session_id,
            provider_config=self.config,
            status=SessionStatus.STARTING
        )
        
        try:
            cmd = [self.config.command] + self.config.additional_args
            env = os.environ.copy()
            env.update(self.config.env_vars)
            
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env
            )
            
            session.process = process
            session.status = SessionStatus.ACTIVE
            self.logger.info(f"Started Gemini CLI session: {session_id}")
            
        except Exception as e:
            session.status = SessionStatus.ERROR
            self.logger.error(f"Failed to start Gemini CLI session: {e}")
            
        return session
    
    async def send_message(self, session: AISession, message: str) -> str:
        """Send message to Gemini CLI."""
        if not session.process or session.status != SessionStatus.ACTIVE:
            raise RuntimeError("Session is not active")
        
        try:
            session.process.stdin.write(message + "\n")
            session.process.stdin.flush()
            
            # Read response with timeout
            response = await asyncio.wait_for(
                self._read_output(session.process),
                timeout=self.config.timeout
            )
            
            session.last_activity = time.time()
            session.conversation_history.append({
                "role": "user",
                "content": message,
                "timestamp": time.time()
            })
            session.conversation_history.append({
                "role": "assistant", 
                "content": response,
                "timestamp": time.time()
            })
            
            return response
            
        except asyncio.TimeoutError:
            raise TimeoutError("AI response timeout")
        except Exception as e:
            self.logger.error(f"Failed to send message: {e}")
            raise
    
    async def stop_session(self, session: AISession) -> bool:
        """Stop Gemini CLI session."""
        if session.process:
            try:
                session.process.terminate()
                await asyncio.sleep(1)
                if session.process.poll() is None:
                    session.process.kill()
                session.status = SessionStatus.INACTIVE
                return True
            except Exception as e:
                self.logger.error(f"Failed to stop session: {e}")
                return False
        return False
    
    async def _read_output(self, process: subprocess.Popen) -> str:
        """Read output from process asynchronously."""
        loop = asyncio.get_event_loop()
        
        def read():
            return process.stdout.readline()
        
        line = await loop.run_in_executor(None, read)
        return line.strip()
    
    def is_available(self) -> bool:
        """Check if Gemini CLI is available."""
        try:
            result = subprocess.run(
                [self.config.command, "--version"],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False


class OllamaProvider(AIProvider):
    """Ollama provider implementation."""
    
    async def start_session(self) -> AISession:
        """Start Ollama session."""
        session_id = str(uuid.uuid4())
        session = AISession(
            session_id=session_id,
            provider_config=self.config,
            status=SessionStatus.ACTIVE  # Ollama uses HTTP API, no persistent process
        )
        
        # Verify Ollama is running and model is available
        if not await self._check_model():
            session.status = SessionStatus.ERROR
            raise RuntimeError(f"Model {self.config.model} not available")
        
        self.logger.info(f"Started Ollama session: {session_id}")
        return session
    
    async def send_message(self, session: AISession, message: str) -> str:
        """Send message to Ollama via HTTP API."""
        import aiohttp
        
        if not self.config.api_endpoint:
            raise RuntimeError("API endpoint not configured")
        
        url = f"{self.config.api_endpoint}/api/generate"
        payload = {
            "model": self.config.model,
            "prompt": message,
            "stream": False
        }
        
        if self.config.max_tokens:
            payload["options"] = {"num_predict": self.config.max_tokens}
        
        try:
            async with aiohttp.ClientSession() as http_session:
                async with http_session.post(
                    url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        response_text = result.get("response", "")
                        
                        session.last_activity = time.time()
                        session.conversation_history.append({
                            "role": "user",
                            "content": message,
                            "timestamp": time.time()
                        })
                        session.conversation_history.append({
                            "role": "assistant",
                            "content": response_text,
                            "timestamp": time.time()
                        })
                        
                        return response_text
                    else:
                        raise RuntimeError(f"HTTP {response.status}: {await response.text()}")
        
        except Exception as e:
            self.logger.error(f"Failed to send message to Ollama: {e}")
            raise
    
    async def stop_session(self, session: AISession) -> bool:
        """Stop Ollama session (no-op for HTTP API)."""
        session.status = SessionStatus.INACTIVE
        return True
    
    async def _check_model(self) -> bool:
        """Check if model is available in Ollama."""
        import aiohttp
        
        if not self.config.api_endpoint or not self.config.model:
            return False
        
        try:
            url = f"{self.config.api_endpoint}/api/tags"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=5) as response:
                    if response.status == 200:
                        data = await response.json()
                        models = [model["name"] for model in data.get("models", [])]
                        return self.config.model in models
        except Exception:
            pass
        
        return False
    
    def is_available(self) -> bool:
        """Check if Ollama is available."""
        try:
            import requests
            if self.config.api_endpoint:
                response = requests.get(f"{self.config.api_endpoint}/api/version", timeout=5)
                return response.status_code == 200
        except Exception:
            pass
        return False


class GitHubCopilotProvider(AIProvider):
    """GitHub Copilot provider implementation."""
    
    async def start_session(self) -> AISession:
        """Start GitHub Copilot session."""
        session_id = str(uuid.uuid4())
        session = AISession(
            session_id=session_id,
            provider_config=self.config,
            status=SessionStatus.STARTING
        )
        
        # GitHub Copilot uses `copilot` command
        try:
            cmd = ["copilot", "explain"] + self.config.additional_args
            env = os.environ.copy()
            env.update(self.config.env_vars)
            
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env
            )
            
            session.process = process
            session.status = SessionStatus.ACTIVE
            self.logger.info(f"Started GitHub Copilot session: {session_id}")
            
        except Exception as e:
            session.status = SessionStatus.ERROR
            self.logger.error(f"Failed to start GitHub Copilot session: {e}")
            
        return session
    
    async def send_message(self, session: AISession, message: str) -> str:
        """Send message to GitHub Copilot."""
        if not session.process or session.status != SessionStatus.ACTIVE:
            raise RuntimeError("Session is not active")
        
        try:
            session.process.stdin.write(message + "\n")
            session.process.stdin.flush()
            
            response = await asyncio.wait_for(
                self._read_output(session.process),
                timeout=self.config.timeout
            )
            
            session.last_activity = time.time()
            session.conversation_history.append({
                "role": "user",
                "content": message,
                "timestamp": time.time()
            })
            session.conversation_history.append({
                "role": "assistant",
                "content": response,
                "timestamp": time.time()
            })
            
            return response
            
        except asyncio.TimeoutError:
            raise TimeoutError("AI response timeout")
        except Exception as e:
            self.logger.error(f"Failed to send message: {e}")
            raise
    
    async def stop_session(self, session: AISession) -> bool:
        """Stop GitHub Copilot session."""
        if session.process:
            try:
                session.process.terminate()
                await asyncio.sleep(1)
                if session.process.poll() is None:
                    session.process.kill()
                session.status = SessionStatus.INACTIVE
                return True
            except Exception as e:
                self.logger.error(f"Failed to stop session: {e}")
                return False
        return False
    
    async def _read_output(self, process: subprocess.Popen) -> str:
        """Read output from process asynchronously."""
        loop = asyncio.get_event_loop()
        
        def read():
            return process.stdout.readline()
        
        line = await loop.run_in_executor(None, read)
        return line.strip()
    
    def is_available(self) -> bool:
        """Check if GitHub Copilot is available."""
        try:
            result = subprocess.run(
                ["copilot", "--version"],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False


class OpenAICompatibleProvider(AIProvider):
    """OpenAI-compatible API provider implementation."""
    
    async def start_session(self) -> AISession:
        """Start OpenAI-compatible session."""
        session_id = str(uuid.uuid4())
        session = AISession(
            session_id=session_id,
            provider_config=self.config,
            status=SessionStatus.ACTIVE
        )
        
        # Verify API connectivity
        if not await self._check_connectivity():
            session.status = SessionStatus.ERROR
            raise RuntimeError("API endpoint not reachable")
        
        self.logger.info(f"Started OpenAI-compatible session: {session_id}")
        return session
    
    async def send_message(self, session: AISession, message: str) -> str:
        """Send message to OpenAI-compatible API."""
        import aiohttp
        
        if not self.config.api_endpoint:
            raise RuntimeError("API endpoint not configured")
        
        url = f"{self.config.api_endpoint}/chat/completions"
        headers = {"Content-Type": "application/json"}
        
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        
        payload = {
            "model": self.config.model or "gpt-3.5-turbo",
            "messages": [{"role": "user", "content": message}],
            "stream": False
        }
        
        if self.config.max_tokens:
            payload["max_tokens"] = self.config.max_tokens
        
        if self.config.temperature is not None:
            payload["temperature"] = self.config.temperature
        
        try:
            async with aiohttp.ClientSession() as http_session:
                async with http_session.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        response_text = result["choices"][0]["message"]["content"]
                        
                        session.last_activity = time.time()
                        session.conversation_history.append({
                            "role": "user",
                            "content": message,
                            "timestamp": time.time()
                        })
                        session.conversation_history.append({
                            "role": "assistant",
                            "content": response_text,
                            "timestamp": time.time()
                        })
                        
                        return response_text
                    else:
                        raise RuntimeError(f"HTTP {response.status}: {await response.text()}")
        
        except Exception as e:
            self.logger.error(f"Failed to send message to OpenAI-compatible API: {e}")
            raise
    
    async def stop_session(self, session: AISession) -> bool:
        """Stop OpenAI-compatible session (no-op for HTTP API)."""
        session.status = SessionStatus.INACTIVE
        return True
    
    async def _check_connectivity(self) -> bool:
        """Check API connectivity."""
        import aiohttp
        
        if not self.config.api_endpoint:
            return False
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.config.api_endpoint}/models",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    return response.status == 200
        except Exception:
            pass
        
        return False
    
    def is_available(self) -> bool:
        """Check if OpenAI-compatible API is available."""
        try:
            import requests
            if self.config.api_endpoint:
                response = requests.get(
                    f"{self.config.api_endpoint}/models",
                    timeout=5,
                    headers={"Authorization": f"Bearer {self.config.api_key}"} if self.config.api_key else None
                )
                return response.status_code == 200
        except Exception:
            pass
        return False


class AIProviderOrchestrator:
    """Main orchestrator for managing multiple AI providers."""
    
    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file or "ai_providers.json"
        self.providers: Dict[str, AIProvider] = {}
        self.sessions: Dict[str, AISession] = {}
        self.logger = logging.getLogger("ai_orchestrator")
        self._setup_logging()
        self._load_providers()
    
    def _setup_logging(self):
        """Setup logging configuration."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    def _load_providers(self):
        """Load provider configurations."""
        config_path = Path(self.config_file)
        
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    configs = json.load(f)
                
                for config_data in configs:
                    config = ProviderConfig(**config_data)
                    provider = self._create_provider(config)
                    self.providers[config.name] = provider
                    
                self.logger.info(f"Loaded {len(self.providers)} provider configurations")
            except Exception as e:
                self.logger.error(f"Failed to load provider configurations: {e}")
        else:
            self._create_default_config()
    
    def _create_default_config(self):
        """Create default provider configuration."""
        default_configs = [
            {
                "name": "gemini",
                "provider_type": "gemini-cli",
                "command": "gemini",
                "model": "gemini-pro",
                "max_tokens": 2048,
                "temperature": 0.7
            },
            {
                "name": "ollama",
                "provider_type": "ollama",
                "api_endpoint": "http://localhost:11434",
                "model": "llama2",
                "max_tokens": 2048,
                "temperature": 0.7
            },
            {
                "name": "copilot",
                "provider_type": "github-copilot",
                "command": "copilot",
                "max_tokens": 2048
            },
            {
                "name": "qwen",
                "provider_type": "openai-compatible",
                "api_endpoint": "http://localhost:8000/v1",
                "api_key": "your-api-key",
                "model": "qwen-coder",
                "max_tokens": 2048,
                "temperature": 0.7
            }
        ]
        
        try:
            with open(self.config_file, 'w') as f:
                json.dump(default_configs, f, indent=2)
            self.logger.info(f"Created default configuration: {self.config_file}")
        except Exception as e:
            self.logger.error(f"Failed to create default configuration: {e}")
    
    def _create_provider(self, config: ProviderConfig) -> AIProvider:
        """Create provider instance based on type."""
        provider_map = {
            ProviderType.GEMINI_CLI: GeminiCLIProvider,
            ProviderType.OLLAMA: OllamaProvider,
            ProviderType.GITHUB_COPILOT: GitHubCopilotProvider,
            ProviderType.OPENAI_COMPATIBLE: OpenAICompatibleProvider,
        }
        
        provider_class = provider_map.get(config.provider_type)
        if not provider_class:
            raise ValueError(f"Unsupported provider type: {config.provider_type}")
        
        return provider_class(config)
    
    def list_providers(self) -> List[str]:
        """List available provider names."""
        return list(self.providers.keys())
    
    def list_sessions(self) -> List[Dict[str, Any]]:
        """List active sessions."""
        sessions_info = []
        for session_id, session in self.sessions.items():
            sessions_info.append({
                "session_id": session_id,
                "provider": session.provider_config.name,
                "status": session.status.value,
                "created_at": session.created_at,
                "last_activity": session.last_activity,
                "conversation_length": len(session.conversation_history)
            })
        return sessions_info
    
    def get_provider(self, name: str) -> Optional[AIProvider]:
        """Get provider by name."""
        return self.providers.get(name)
    
    async def start_session(self, provider_name: str) -> Optional[str]:
        """Start a new session with specified provider."""
        provider = self.get_provider(provider_name)
        if not provider:
            raise ValueError(f"Provider not found: {provider_name}")
        
        if not provider.is_available():
            raise RuntimeError(f"Provider not available: {provider_name}")
        
        session = await provider.start_session()
        self.sessions[session.session_id] = session
        
        self.logger.info(f"Started session {session.session_id} with provider {provider_name}")
        return session.session_id
    
    async def send_message(self, session_id: str, message: str) -> str:
        """Send message to a session."""
        session = self.sessions.get(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")
        
        provider = self.get_provider(session.provider_config.name)
        if not provider:
            raise ValueError(f"Provider not found: {session.provider_config.name}")
        
        return await provider.send_message(session, message)
    
    async def stop_session(self, session_id: str) -> bool:
        """Stop a session."""
        session = self.sessions.get(session_id)
        if not session:
            return False
        
        provider = self.get_provider(session.provider_config.name)
        if provider:
            success = await provider.stop_session(session)
            if success:
                del self.sessions[session_id]
                self.logger.info(f"Stopped session: {session_id}")
            return success
        
        return False
    
    async def stop_all_sessions(self) -> int:
        """Stop all active sessions."""
        stopped_count = 0
        session_ids = list(self.sessions.keys())
        
        for session_id in session_ids:
            if await self.stop_session(session_id):
                stopped_count += 1
        
        self.logger.info(f"Stopped {stopped_count} sessions")
        return stopped_count
    
    def get_session_history(self, session_id: str) -> List[Dict[str, Any]]:
        """Get conversation history for a session."""
        session = self.sessions.get(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")
        
        return session.conversation_history.copy()


# CLI Interface
async def main():
    """Main CLI interface."""
    import argparse
    
    parser = argparse.ArgumentParser(description="AI Provider Orchestrator")
    parser.add_argument("--config", help="Configuration file path")
    parser.add_argument("--list-providers", action="store_true", help="List available providers")
    parser.add_argument("--list-sessions", action="store_true", help="List active sessions")
    parser.add_argument("--start", metavar="PROVIDER", help="Start session with provider")
    parser.add_argument("--stop", metavar="SESSION_ID", help="Stop session")
    parser.add_argument("--stop-all", action="store_true", help="Stop all sessions")
    parser.add_argument("--send", metavar=("SESSION_ID", "MESSAGE"), nargs=2, 
                       help="Send message to session")
    parser.add_argument("--history", metavar="SESSION_ID", help="Get session history")
    parser.add_argument("--interactive", action="store_true", help="Interactive mode")
    
    args = parser.parse_args()
    
    orchestrator = AIProviderOrchestrator(args.config)
    
    if args.list_providers:
        providers = orchestrator.list_providers()
        print("Available providers:")
        for provider in providers:
            print(f"  - {provider}")
    
    elif args.list_sessions:
        sessions = orchestrator.list_sessions()
        print("Active sessions:")
        for session in sessions:
            print(f"  Session: {session['session_id']}")
            print(f"    Provider: {session['provider']}")
            print(f"    Status: {session['status']}")
            print(f"    Created: {time.ctime(session['created_at'])}")
            print(f"    Messages: {session['conversation_length']}")
            print()
    
    elif args.start:
        try:
            session_id = await orchestrator.start_session(args.start)
            print(f"Started session: {session_id}")
        except Exception as e:
            print(f"Error starting session: {e}")
    
    elif args.stop:
        try:
            success = await orchestrator.stop_session(args.stop)
            if success:
                print(f"Stopped session: {args.stop}")
            else:
                print(f"Failed to stop session: {args.stop}")
        except Exception as e:
            print(f"Error stopping session: {e}")
    
    elif args.stop_all:
        try:
            count = await orchestrator.stop_all_sessions()
            print(f"Stopped {count} sessions")
        except Exception as e:
            print(f"Error stopping sessions: {e}")
    
    elif args.send:
        session_id, message = args.send
        try:
            response = await orchestrator.send_message(session_id, message)
            print(f"Response: {response}")
        except Exception as e:
            print(f"Error sending message: {e}")
    
    elif args.history:
        try:
            history = orchestrator.get_session_history(args.history)
            print(f"Session history for {args.history}:")
            for entry in history:
                print(f"{entry['role']}: {entry['content']}")
                print(f"  Time: {time.ctime(entry['timestamp'])}")
                print()
        except Exception as e:
            print(f"Error getting history: {e}")
    
    elif args.interactive:
        print("AI Provider Orchestrator - Interactive Mode")
        print("Commands: providers, sessions, start <provider>, stop <session_id>,")
        print("         send <session_id> <message>, history <session_id>, quit")
        print()
        
        while True:
            try:
                command = input("orchestrator> ").strip().split()
                if not command:
                    continue
                
                cmd = command[0].lower()
                
                if cmd == "quit":
                    await orchestrator.stop_all_sessions()
                    break
                
                elif cmd == "providers":
                    providers = orchestrator.list_providers()
                    print("Available providers:", ", ".join(providers))
                
                elif cmd == "sessions":
                    sessions = orchestrator.list_sessions()
                    if sessions:
                        for session in sessions:
                            print(f"{session['session_id']} ({session['provider']}) - {session['status']}")
                    else:
                        print("No active sessions")
                
                elif cmd == "start" and len(command) > 1:
                    try:
                        session_id = await orchestrator.start_session(command[1])
                        print(f"Started session: {session_id}")
                    except Exception as e:
                        print(f"Error: {e}")
                
                elif cmd == "stop" and len(command) > 1:
                    try:
                        success = await orchestrator.stop_session(command[1])
                        print(f"{'Stopped' if success else 'Failed to stop'} session: {command[1]}")
                    except Exception as e:
                        print(f"Error: {e}")
                
                elif cmd == "send" and len(command) > 2:
                    session_id = command[1]
                    message = " ".join(command[2:])
                    try:
                        response = await orchestrator.send_message(session_id, message)
                        print(f"Response: {response}")
                    except Exception as e:
                        print(f"Error: {e}")
                
                elif cmd == "history" and len(command) > 1:
                    try:
                        history = orchestrator.get_session_history(command[1])
                        for entry in history:
                            print(f"{entry['role']}: {entry['content']}")
                    except Exception as e:
                        print(f"Error: {e}")
                
                else:
                    print("Unknown command or missing arguments")
                    
            except KeyboardInterrupt:
                await orchestrator.stop_all_sessions()
                break
    
    else:
        parser.print_help()


if __name__ == "__main__":
    asyncio.run(main())