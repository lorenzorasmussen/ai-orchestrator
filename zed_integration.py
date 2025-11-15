#!/usr/bin/env python3
"""
Zed Editor Integration for AI Provider Orchestrator

This script provides seamless integration between Zed Editor and the AI Provider Orchestrator,
allowing users to manage AI sessions directly from within Zed.

Features:
- Quick session management from Zed command palette
- Context-aware code analysis
- File-based interaction
- Real-time response streaming
- Session persistence across Zed restarts

Author: OpenCode Research Assistant
License: MIT
"""

import asyncio
import json
import os
import sys
import tempfile
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional
import argparse
from dataclasses import dataclass
import logging

# Add the orchestrator to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from ai_provider_orchestrator import AIProviderOrchestrator, AISession
except ImportError:
    print("Error: ai_provider_orchestrator.py not found. Please ensure it's in the same directory.")
    sys.exit(1)


@dataclass
class ZedContext:
    """Context information from Zed editor."""
    file_path: Optional[str] = None
    selection: Optional[str] = None
    cursor_line: Optional[int] = None
    cursor_column: Optional[int] = None
    language: Optional[str] = None
    project_root: Optional[str] = None


class ZedAIIntegration:
    """Zed Editor integration for AI Provider Orchestrator."""
    
    def __init__(self, config_file: Optional[str] = None):
        self.orchestrator = AIProviderOrchestrator(config_file)
        self.context = ZedContext()
        self.logger = logging.getLogger("zed_ai_integration")
        self._setup_logging()
        self.session_file = Path.home() / ".zed_ai_sessions.json"
        self._load_session_state()
    
    def _setup_logging(self):
        """Setup logging configuration."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    def _load_session_state(self):
        """Load persistent session state."""
        if self.session_file.exists():
            try:
                with open(self.session_file, 'r') as f:
                    self.active_sessions = json.load(f)
                self.logger.info(f"Loaded {len(self.active_sessions)} persistent sessions")
            except Exception as e:
                self.logger.error(f"Failed to load session state: {e}")
                self.active_sessions = {}
        else:
            self.active_sessions = {}
    
    def _save_session_state(self):
        """Save session state to disk."""
        try:
            with open(self.session_file, 'w') as f:
                json.dump(self.active_sessions, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save session state: {e}")
    
    def parse_zed_context(self, args) -> ZedContext:
        """Parse context from Zed command arguments."""
        context = ZedContext()
        
        if hasattr(args, 'file') and args.file:
            context.file_path = args.file
            context.language = self._detect_language(args.file)
        
        if hasattr(args, 'selection') and args.selection:
            context.selection = args.selection
        
        if hasattr(args, 'cursor_line') and args.cursor_line:
            context.cursor_line = args.cursor_line
        
        if hasattr(args, 'cursor_column') and args.cursor_column:
            context.cursor_column = args.cursor_column
        
        if hasattr(args, 'project_root') and args.project_root:
            context.project_root = args.project_root
        
        return context
    
    def _detect_language(self, file_path: str) -> Optional[str]:
        """Detect programming language from file extension."""
        ext = Path(file_path).suffix.lower()
        language_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.jsx': 'react',
            '.tsx': 'react-typescript',
            '.java': 'java',
            '.cpp': 'cpp',
            '.c': 'c',
            '.cs': 'csharp',
            '.go': 'go',
            '.rs': 'rust',
            '.php': 'php',
            '.rb': 'ruby',
            '.swift': 'swift',
            '.kt': 'kotlin',
            '.scala': 'scala',
            '.html': 'html',
            '.css': 'css',
            '.scss': 'scss',
            '.sass': 'sass',
            '.json': 'json',
            '.yaml': 'yaml',
            '.yml': 'yaml',
            '.xml': 'xml',
            '.md': 'markdown',
            '.sql': 'sql',
            '.sh': 'bash',
            '.zsh': 'zsh',
            '.fish': 'fish',
        }
        return language_map.get(ext)
    
    def _create_context_prompt(self, context: ZedContext) -> str:
        """Create a context-aware prompt for the AI."""
        prompt_parts = []
        
        if context.file_path:
            prompt_parts.append(f"File: {context.file_path}")
        
        if context.language:
            prompt_parts.append(f"Language: {context.language}")
        
        if context.selection:
            prompt_parts.append(f"Selected code:\n```\n{context.selection}\n```")
        elif context.file_path:
            # Read file content if no selection
            try:
                with open(context.file_path, 'r') as f:
                    content = f.read()
                prompt_parts.append(f"File content:\n```\n{content}\n```")
            except Exception as e:
                self.logger.error(f"Failed to read file: {e}")
        
        if context.cursor_line is not None:
            prompt_parts.append(f"Cursor at line {context.cursor_line}")
        
        return "\n".join(prompt_parts)
    
    async def start_quick_session(self, provider_name: str, context: ZedContext) -> str:
        """Start a quick session with context."""
        try:
            session_id = await self.orchestrator.start_session(provider_name)
            
            # Store session with context
            self.active_sessions[session_id] = {
                "provider": provider_name,
                "context": {
                    "file_path": context.file_path,
                    "language": context.language,
                    "project_root": context.project_root
                },
                "created_at": asyncio.get_event_loop().time()
            }
            
            self._save_session_state()
            
            # Send initial context if available
            if context.file_path or context.selection:
                context_prompt = self._create_context_prompt(context)
                await self.orchestrator.send_message(session_id, 
                    f"I'm working on this code. Please understand the context:\n\n{context_prompt}")
            
            return session_id
            
        except Exception as e:
            self.logger.error(f"Failed to start quick session: {e}")
            raise
    
    async def explain_code(self, provider_name: str, context: ZedContext) -> str:
        """Explain the current code or selection."""
        if not context.selection and not context.file_path:
            raise ValueError("No code selected or file available for explanation")
        
        session_id = await self.start_quick_session(provider_name, context)
        
        prompt = "Please explain this code:"
        if context.selection:
            prompt += f"\n\n```\n{context.selection}\n```"
        else:
            prompt += f"\n\nFile: {context.file_path}"
        
        if context.language:
            prompt += f"\n\nLanguage: {context.language}"
        
        response = await self.orchestrator.send_message(session_id, prompt)
        
        # Clean up session
        await self.orchestrator.stop_session(session_id)
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
            self._save_session_state()
        
        return response
    
    async def improve_code(self, provider_name: str, context: ZedContext) -> str:
        """Suggest improvements for the current code."""
        if not context.selection and not context.file_path:
            raise ValueError("No code selected or file available for improvement")
        
        session_id = await self.start_quick_session(provider_name, context)
        
        prompt = "Please suggest improvements for this code:"
        if context.selection:
            prompt += f"\n\n```\n{context.selection}\n```"
        else:
            prompt += f"\n\nFile: {context.file_path}"
        
        if context.language:
            prompt += f"\n\nLanguage: {context.language}"
        
        prompt += "\n\nFocus on:\n- Code quality and readability\n- Performance optimizations\n- Best practices\n- Bug fixes\n- Modern language features"
        
        response = await self.orchestrator.send_message(session_id, prompt)
        
        # Clean up session
        await self.orchestrator.stop_session(session_id)
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
            self._save_session_state()
        
        return response
    
    async def generate_code(self, provider_name: str, instruction: str, context: ZedContext) -> str:
        """Generate code based on instruction and context."""
        session_id = await self.start_quick_session(provider_name, context)
        
        prompt = f"Generate code for: {instruction}"
        
        if context.language:
            prompt += f"\n\nLanguage: {context.language}"
        
        if context.file_path:
            prompt += f"\n\nFile context: {context.file_path}"
        
        if context.selection:
            prompt += f"\n\nRelated code:\n```\n{context.selection}\n```"
        
        prompt += "\n\nPlease provide:\n1. The generated code\n2. A brief explanation\n3. Any dependencies or setup requirements"
        
        response = await self.orchestrator.send_message(session_id, prompt)
        
        # Clean up session
        await self.orchestrator.stop_session(session_id)
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
            self._save_session_state()
        
        return response
    
    async def fix_code(self, provider_name: str, error_message: str, context: ZedContext) -> str:
        """Fix code issues based on error message."""
        if not context.selection and not context.file_path:
            raise ValueError("No code selected or file available for fixing")
        
        session_id = await self.start_quick_session(provider_name, context)
        
        prompt = f"Please fix this code issue:\n\nError: {error_message}"
        
        if context.selection:
            prompt += f"\n\nCode with error:\n```\n{context.selection}\n```"
        else:
            prompt += f"\n\nFile with error: {context.file_path}"
        
        if context.language:
            prompt += f"\n\nLanguage: {context.language}"
        
        prompt += "\n\nPlease provide:\n1. The fixed code\n2. Explanation of what was wrong\n3. How to prevent similar issues"
        
        response = await self.orchestrator.send_message(session_id, prompt)
        
        # Clean up session
        await self.orchestrator.stop_session(session_id)
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
            self._save_session_state()
        
        return response
    
    async def chat_with_context(self, provider_name: str, message: str, context: ZedContext) -> str:
        """Start a chat session with file context."""
        session_id = await self.start_quick_session(provider_name, context)
        
        # Store session for continued conversation
        self.active_sessions[session_id]["chat_mode"] = True
        self._save_session_state()
        
        response = await self.orchestrator.send_message(session_id, message)
        
        return response
    
    async def continue_chat(self, session_id: str, message: str) -> str:
        """Continue an existing chat session."""
        if session_id not in self.active_sessions:
            raise ValueError(f"Session not found: {session_id}")
        
        response = await self.orchestrator.send_message(session_id, message)
        return response
    
    def list_active_sessions(self) -> List[Dict[str, Any]]:
        """List active Zed AI sessions."""
        sessions = []
        for session_id, session_data in self.active_sessions.items():
            # Get full session info from orchestrator
            orchestrator_session = self.orchestrator.sessions.get(session_id)
            if orchestrator_session:
                sessions.append({
                    "session_id": session_id,
                    "provider": session_data["provider"],
                    "context": session_data["context"],
                    "chat_mode": session_data.get("chat_mode", False),
                    "status": orchestrator_session.status.value,
                    "created_at": session_data["created_at"]
                })
        return sessions
    
    async def stop_zed_session(self, session_id: str) -> bool:
        """Stop a Zed AI session."""
        success = await self.orchestrator.stop_session(session_id)
        
        if success and session_id in self.active_sessions:
            del self.active_sessions[session_id]
            self._save_session_state()
        
        return success


# Command-line interface for Zed integration
async def main():
    """Main CLI interface for Zed integration."""
    parser = argparse.ArgumentParser(description="Zed AI Integration")
    parser.add_argument("--config", help="Configuration file path")
    
    # Context arguments
    parser.add_argument("--file", help="Current file path")
    parser.add_argument("--selection", help="Selected text")
    parser.add_argument("--cursor-line", type=int, help="Cursor line number")
    parser.add_argument("--cursor-column", type=int, help="Cursor column number")
    parser.add_argument("--project-root", help="Project root directory")
    
    # Action arguments
    parser.add_argument("--explain", metavar="PROVIDER", help="Explain code with provider")
    parser.add_argument("--improve", metavar="PROVIDER", help="Improve code with provider")
    parser.add_argument("--generate", metavar=("PROVIDER", "INSTRUCTION"), nargs=2,
                       help="Generate code with provider and instruction")
    parser.add_argument("--fix", metavar=("PROVIDER", "ERROR"), nargs=2,
                       help="Fix code with provider and error message")
    parser.add_argument("--chat", metavar=("PROVIDER", "MESSAGE"), nargs=2,
                       help="Start chat with provider and message")
    parser.add_argument("--continue-chat", metavar=("SESSION_ID", "MESSAGE"), nargs=2,
                       help="Continue chat session")
    parser.add_argument("--list-sessions", action="store_true", help="List active sessions")
    parser.add_argument("--stop-session", metavar="SESSION_ID", help="Stop session")
    
    args = parser.parse_args()
    
    integration = ZedAIIntegration(args.config)
    context = integration.parse_zed_context(args)
    
    try:
        if args.explain:
            response = await integration.explain_code(args.explain, context)
            print(response)
        
        elif args.improve:
            response = await integration.improve_code(args.improve, context)
            print(response)
        
        elif args.generate:
            provider, instruction = args.generate
            response = await integration.generate_code(provider, instruction, context)
            print(response)
        
        elif args.fix:
            provider, error_message = args.fix
            response = await integration.fix_code(provider, error_message, context)
            print(response)
        
        elif args.chat:
            provider, message = args.chat
            response = await integration.chat_with_context(provider, message, context)
            print(response)
        
        elif args.continue_chat:
            session_id, message = args.continue_chat
            response = await integration.continue_chat(session_id, message)
            print(response)
        
        elif args.list_sessions:
            sessions = integration.list_active_sessions()
            print("Active Zed AI Sessions:")
            for session in sessions:
                print(f"  {session['session_id']}")
                print(f"    Provider: {session['provider']}")
                print(f"    Context: {session['context']}")
                print(f"    Chat Mode: {session['chat_mode']}")
                print(f"    Status: {session['status']}")
                print()
        
        elif args.stop_session:
            success = await integration.stop_zed_session(args.stop_session)
            print(f"{'Stopped' if success else 'Failed to stop'} session: {args.stop_session}")
        
        else:
            parser.print_help()
    
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())