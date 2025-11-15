#!/usr/bin/env python3
"""
Web-based Unified Interface for AI Provider Orchestrator

A Flask-based web interface for managing multiple AI provider sessions,
providing a user-friendly GUI for session management, chat interactions,
and provider configuration.

Features:
- Session management dashboard
- Real-time chat interface
- Provider configuration
- Session history and analytics
- Multi-provider comparison
- File upload and context sharing

Author: OpenCode Research Assistant
License: MIT
"""

import asyncio
import json
import os
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from flask import Flask, render_template, request, jsonify, session, send_file
    from flask_socketio import SocketIO, emit
    import websockets
except ImportError:
    print("Error: Flask and Flask-SocketIO are required. Install with: pip install flask flask-socketio")
    sys.exit(1)

# Add orchestrator to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from ai_provider_orchestrator import AIProviderOrchestrator, AISession
except ImportError:
    print("Error: ai_provider_orchestrator.py not found. Please ensure it's in the same directory.")
    sys.exit(1)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
socketio = SocketIO(app, cors_allowed_origins="*")

# Global orchestrator instance
orchestrator = AIProviderOrchestrator()
active_web_sessions = {}


class WebSession:
    """Web session management."""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.ai_sessions = {}
        self.current_provider = None
        self.created_at = time.time()
        self.last_activity = time.time()


def get_web_session() -> WebSession:
    """Get or create web session."""
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
        active_web_sessions[session['session_id']] = WebSession(session['session_id'])
    
    return active_web_sessions[session['session_id']]


@app.route('/')
def index():
    """Main dashboard page."""
    return render_template('index.html')


@app.route('/api/providers')
def get_providers():
    """Get available providers."""
    providers = orchestrator.list_providers()
    provider_info = {}
    
    for provider_name in providers:
        provider = orchestrator.get_provider(provider_name)
        provider_info[provider_name] = {
            'name': provider_name,
            'type': provider.config.provider_type.value,
            'available': provider.is_available(),
            'model': provider.config.model,
            'endpoint': provider.config.api_endpoint,
            'command': provider.config.command
        }
    
    return jsonify(provider_info)


@app.route('/api/sessions')
def get_sessions():
    """Get active sessions."""
    web_session = get_web_session()
    sessions = []
    
    # Get orchestrator sessions
    orchestrator_sessions = orchestrator.list_sessions()
    for session_data in orchestrator_sessions:
        session_id = session_data['session_id']
        sessions.append({
            **session_data,
            'is_web_session': session_id in web_session.ai_sessions
        })
    
    return jsonify({
        'sessions': sessions,
        'web_session_id': web_session.session_id,
        'current_provider': web_session.current_provider
    })


@app.route('/api/start_session', methods=['POST'])
def start_session():
    """Start a new AI session."""
    data = request.json
    provider_name = data.get('provider')
    
    if not provider_name:
        return jsonify({'error': 'Provider name is required'}), 400
    
    try:
        # Run async operation in thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        session_id = loop.run_until_complete(orchestrator.start_session(provider_name))
        loop.close()
        
        # Update web session
        web_session = get_web_session()
        web_session.ai_sessions[session_id] = provider_name
        web_session.current_provider = provider_name
        web_session.last_activity = time.time()
        
        return jsonify({
            'session_id': session_id,
            'provider': provider_name,
            'status': 'started'
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/stop_session', methods=['POST'])
def stop_session():
    """Stop an AI session."""
    data = request.json
    session_id = data.get('session_id')
    
    if not session_id:
        return jsonify({'error': 'Session ID is required'}), 400
    
    try:
        # Run async operation in thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        success = loop.run_until_complete(orchestrator.stop_session(session_id))
        loop.close()
        
        # Update web session
        web_session = get_web_session()
        if session_id in web_session.ai_sessions:
            del web_session.ai_sessions[session_id]
        
        return jsonify({'success': success})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/send_message', methods=['POST'])
def send_message():
    """Send a message to an AI session."""
    data = request.json
    session_id = data.get('session_id')
    message = data.get('message')
    
    if not session_id or not message:
        return jsonify({'error': 'Session ID and message are required'}), 400
    
    try:
        # Run async operation in thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        response = loop.run_until_complete(orchestrator.send_message(session_id, message))
        loop.close()
        
        # Update web session activity
        web_session = get_web_session()
        web_session.last_activity = time.time()
        
        return jsonify({
            'response': response,
            'timestamp': time.time()
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/session_history/<session_id>')
def get_session_history(session_id):
    """Get conversation history for a session."""
    try:
        history = orchestrator.get_session_history(session_id)
        return jsonify({'history': history})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/config')
def get_config():
    """Get current configuration."""
    try:
        with open('ai_providers.json', 'r') as f:
            config = json.load(f)
        return jsonify(config)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/config', methods=['POST'])
def update_config():
    """Update configuration."""
    data = request.json
    
    try:
        with open('ai_providers.json', 'w') as f:
            json.dump(data, f, indent=2)
        
        # Reload providers
        orchestrator._load_providers()
        
        return jsonify({'success': True})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/compare', methods=['POST'])
def compare_providers():
    """Compare responses from multiple providers."""
    data = request.json
    message = data.get('message')
    providers = data.get('providers', [])
    
    if not message or not providers:
        return jsonify({'error': 'Message and providers are required'}), 400
    
    results = {}
    
    async def get_provider_response(provider_name):
        try:
            session_id = await orchestrator.start_session(provider_name)
            response = await orchestrator.send_message(session_id, message)
            await orchestrator.stop_session(session_id)
            return provider_name, response
        except Exception as e:
            return provider_name, f"Error: {str(e)}"
    
    # Run comparisons concurrently
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    tasks = [get_provider_response(provider) for provider in providers]
    responses = loop.run_until_complete(asyncio.gather(*tasks))
    loop.close()
    
    for provider_name, response in responses:
        results[provider_name] = {
            'response': response,
            'timestamp': time.time()
        }
    
    return jsonify(results)


@socketio.on('connect')
def handle_connect():
    """Handle WebSocket connection."""
    print(f"Client connected: {request.sid}")
    emit('status', {'message': 'Connected to AI Orchestrator'})


@socketio.on('disconnect')
def handle_disconnect():
    """Handle WebSocket disconnection."""
    print(f"Client disconnected: {request.sid}")


@socketio.on('start_session')
def handle_start_session(data):
    """Handle session start via WebSocket."""
    provider_name = data.get('provider')
    
    async def start_and_notify():
        try:
            session_id = await orchestrator.start_session(provider_name)
            emit('session_started', {
                'session_id': session_id,
                'provider': provider_name
            })
        except Exception as e:
            emit('error', {'message': str(e)})
    
    # Run in thread
    thread = threading.Thread(target=lambda: asyncio.run(start_and_notify()))
    thread.start()


@socketio.on('send_message')
def handle_send_message(data):
    """Handle message sending via WebSocket."""
    session_id = data.get('session_id')
    message = data.get('message')
    
    async def send_and_respond():
        try:
            response = await orchestrator.send_message(session_id, message)
            emit('message_response', {
                'session_id': session_id,
                'response': response,
                'timestamp': time.time()
            })
        except Exception as e:
            emit('error', {'message': str(e)})
    
    # Run in thread
    thread = threading.Thread(target=lambda: asyncio.run(send_and_respond()))
    thread.start()


# HTML Templates (embedded for simplicity)
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Provider Orchestrator</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f5f5;
            color: #333;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        
        .header {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        
        .header h1 {
            color: #2c3e50;
            margin-bottom: 10px;
        }
        
        .main-content {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }
        
        .panel {
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            padding: 20px;
        }
        
        .panel h2 {
            color: #2c3e50;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 2px solid #3498db;
        }
        
        .provider-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }
        
        .provider-card {
            border: 2px solid #ecf0f1;
            border-radius: 6px;
            padding: 15px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        
        .provider-card:hover {
            border-color: #3498db;
            transform: translateY(-2px);
        }
        
        .provider-card.available {
            border-color: #27ae60;
            background: #f8fff8;
        }
        
        .provider-card.unavailable {
            border-color: #e74c3c;
            background: #fff8f8;
            opacity: 0.7;
        }
        
        .provider-name {
            font-weight: bold;
            margin-bottom: 5px;
        }
        
        .provider-type {
            font-size: 0.9em;
            color: #7f8c8d;
            margin-bottom: 5px;
        }
        
        .provider-status {
            font-size: 0.8em;
            padding: 2px 8px;
            border-radius: 12px;
            display: inline-block;
        }
        
        .provider-status.available {
            background: #27ae60;
            color: white;
        }
        
        .provider-status.unavailable {
            background: #e74c3c;
            color: white;
        }
        
        .session-list {
            max-height: 300px;
            overflow-y: auto;
        }
        
        .session-item {
            border: 1px solid #ecf0f1;
            border-radius: 4px;
            padding: 10px;
            margin-bottom: 10px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .session-info {
            flex: 1;
        }
        
        .session-actions {
            display: flex;
            gap: 5px;
        }
        
        .btn {
            padding: 8px 16px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.9em;
            transition: background-color 0.3s ease;
        }
        
        .btn-primary {
            background: #3498db;
            color: white;
        }
        
        .btn-primary:hover {
            background: #2980b9;
        }
        
        .btn-danger {
            background: #e74c3c;
            color: white;
        }
        
        .btn-danger:hover {
            background: #c0392b;
        }
        
        .btn-success {
            background: #27ae60;
            color: white;
        }
        
        .btn-success:hover {
            background: #229954;
        }
        
        .chat-container {
            display: flex;
            flex-direction: column;
            height: 500px;
        }
        
        .chat-messages {
            flex: 1;
            overflow-y: auto;
            border: 1px solid #ecf0f1;
            border-radius: 4px;
            padding: 15px;
            margin-bottom: 15px;
            background: #fafafa;
        }
        
        .message {
            margin-bottom: 15px;
            padding: 10px;
            border-radius: 8px;
        }
        
        .message.user {
            background: #3498db;
            color: white;
            margin-left: 20%;
        }
        
        .message.assistant {
            background: #ecf0f1;
            margin-right: 20%;
        }
        
        .message-content {
            margin-bottom: 5px;
        }
        
        .message-time {
            font-size: 0.8em;
            opacity: 0.7;
        }
        
        .chat-input {
            display: flex;
            gap: 10px;
        }
        
        .chat-input input {
            flex: 1;
            padding: 10px;
            border: 1px solid #ecf0f1;
            border-radius: 4px;
            font-size: 1em;
        }
        
        .status-indicator {
            display: inline-block;
            width: 8px;
            height: 8px;
            border-radius: 50%;
            margin-right: 5px;
        }
        
        .status-indicator.active {
            background: #27ae60;
        }
        
        .status-indicator.inactive {
            background: #95a5a6;
        }
        
        .status-indicator.error {
            background: #e74c3c;
        }
        
        .comparison-container {
            margin-top: 20px;
        }
        
        .comparison-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 15px;
        }
        
        .comparison-item {
            border: 1px solid #ecf0f1;
            border-radius: 6px;
            padding: 15px;
        }
        
        .comparison-provider {
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 10px;
        }
        
        .comparison-response {
            background: #f8f9fa;
            padding: 10px;
            border-radius: 4px;
            font-family: monospace;
            white-space: pre-wrap;
            max-height: 200px;
            overflow-y: auto;
        }
        
        .loading {
            text-align: center;
            padding: 20px;
            color: #7f8c8d;
        }
        
        .error {
            background: #fff5f5;
            border: 1px solid #fed7d7;
            color: #c53030;
            padding: 10px;
            border-radius: 4px;
            margin-bottom: 15px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 AI Provider Orchestrator</h1>
            <p>Manage multiple AI provider sessions from a unified interface</p>
        </div>
        
        <div class="main-content">
            <!-- Providers Panel -->
            <div class="panel">
                <h2>Available Providers</h2>
                <div id="providers-grid" class="provider-grid">
                    <!-- Providers will be loaded here -->
                </div>
                
                <div style="margin-top: 20px;">
                    <button class="btn btn-primary" onclick="refreshProviders()">Refresh Providers</button>
                    <button class="btn btn-success" onclick="showComparison()">Compare Providers</button>
                </div>
            </div>
            
            <!-- Sessions Panel -->
            <div class="panel">
                <h2>Active Sessions</h2>
                <div id="sessions-list" class="session-list">
                    <!-- Sessions will be loaded here -->
                </div>
                
                <div style="margin-top: 15px;">
                    <button class="btn btn-primary" onclick="refreshSessions()">Refresh Sessions</button>
                    <button class="btn btn-danger" onclick="stopAllSessions()">Stop All</button>
                </div>
            </div>
        </div>
        
        <!-- Chat Interface -->
        <div class="panel" style="margin-top: 20px;">
            <h2>Chat Interface</h2>
            <div class="chat-container">
                <div id="chat-messages" class="chat-messages">
                    <div class="loading">Select a session to start chatting...</div>
                </div>
                <div class="chat-input">
                    <input type="text" id="message-input" placeholder="Type your message here..." disabled>
                    <button class="btn btn-primary" id="send-button" onclick="sendMessage()" disabled>Send</button>
                </div>
            </div>
        </div>
        
        <!-- Comparison Interface -->
        <div id="comparison-panel" class="panel" style="margin-top: 20px; display: none;">
            <h2>Provider Comparison</h2>
            <div style="margin-bottom: 15px;">
                <textarea id="comparison-message" placeholder="Enter message to compare across providers..." 
                          style="width: 100%; height: 80px; padding: 10px; border: 1px solid #ecf0f1; border-radius: 4px;"></textarea>
                <div style="margin-top: 10px;">
                    <button class="btn btn-primary" onclick="compareProviders()">Compare</button>
                    <button class="btn btn-danger" onclick="hideComparison()">Close</button>
                </div>
            </div>
            <div id="comparison-results" class="comparison-grid">
                <!-- Comparison results will be shown here -->
            </div>
        </div>
    </div>
    
    <script>
        const socket = io();
        let currentSessionId = null;
        
        // Socket event handlers
        socket.on('connect', () => {
            console.log('Connected to server');
            loadProviders();
            loadSessions();
        });
        
        socket.on('session_started', (data) => {
            console.log('Session started:', data);
            loadSessions();
        });
        
        socket.on('message_response', (data) => {
            console.log('Message response:', data);
            addMessage('assistant', data.response, data.timestamp);
        });
        
        socket.on('error', (data) => {
            console.error('Socket error:', data);
            showError(data.message);
        });
        
        // Load providers
        async function loadProviders() {
            try {
                const response = await fetch('/api/providers');
                const providers = await response.json();
                
                const grid = document.getElementById('providers-grid');
                grid.innerHTML = '';
                
                for (const [name, info] of Object.entries(providers)) {
                    const card = document.createElement('div');
                    card.className = `provider-card ${info.available ? 'available' : 'unavailable'}`;
                    card.onclick = () => startSession(name);
                    
                    card.innerHTML = `
                        <div class="provider-name">${name}</div>
                        <div class="provider-type">${info.type}</div>
                        <div class="provider-status ${info.available ? 'available' : 'unavailable'}">
                            ${info.available ? 'Available' : 'Unavailable'}
                        </div>
                    `;
                    
                    grid.appendChild(card);
                }
            } catch (error) {
                console.error('Failed to load providers:', error);
                showError('Failed to load providers');
            }
        }
        
        // Load sessions
        async function loadSessions() {
            try {
                const response = await fetch('/api/sessions');
                const data = await response.json();
                
                const list = document.getElementById('sessions-list');
                list.innerHTML = '';
                
                if (data.sessions.length === 0) {
                    list.innerHTML = '<div class="loading">No active sessions</div>';
                    return;
                }
                
                data.sessions.forEach(session => {
                    const item = document.createElement('div');
                    item.className = 'session-item';
                    
                    const statusClass = session.status === 'active' ? 'active' : 
                                      session.status === 'error' ? 'error' : 'inactive';
                    
                    item.innerHTML = `
                        <div class="session-info">
                            <span class="status-indicator ${statusClass}"></span>
                            <strong>${session.session_id.substring(0, 8)}...</strong>
                            <br>
                            <small>${session.provider} - ${session.status}</small>
                        </div>
                        <div class="session-actions">
                            <button class="btn btn-primary" onclick="selectSession('${session.session_id}')">Chat</button>
                            <button class="btn btn-danger" onclick="stopSession('${session.session_id}')">Stop</button>
                        </div>
                    `;
                    
                    list.appendChild(item);
                });
            } catch (error) {
                console.error('Failed to load sessions:', error);
                showError('Failed to load sessions');
            }
        }
        
        // Start session
        async function startSession(providerName) {
            try {
                const response = await fetch('/api/start_session', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({provider: providerName})
                });
                
                if (response.ok) {
                    const data = await response.json();
                    socket.emit('start_session', {provider: providerName});
                } else {
                    const error = await response.json();
                    showError(error.error);
                }
            } catch (error) {
                console.error('Failed to start session:', error);
                showError('Failed to start session');
            }
        }
        
        // Stop session
        async function stopSession(sessionId) {
            try {
                const response = await fetch('/api/stop_session', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({session_id: sessionId})
                });
                
                if (response.ok) {
                    if (currentSessionId === sessionId) {
                        currentSessionId = null;
                        document.getElementById('message-input').disabled = true;
                        document.getElementById('send-button').disabled = true;
                        document.getElementById('chat-messages').innerHTML = '<div class="loading">Select a session to start chatting...</div>';
                    }
                    loadSessions();
                } else {
                    const error = await response.json();
                    showError(error.error);
                }
            } catch (error) {
                console.error('Failed to stop session:', error);
                showError('Failed to stop session');
            }
        }
        
        // Stop all sessions
        async function stopAllSessions() {
            if (!confirm('Are you sure you want to stop all sessions?')) {
                return;
            }
            
            try {
                const response = await fetch('/api/sessions');
                const data = await response.json();
                
                for (const session of data.sessions) {
                    await stopSession(session.session_id);
                }
            } catch (error) {
                console.error('Failed to stop all sessions:', error);
                showError('Failed to stop all sessions');
            }
        }
        
        // Select session for chat
        function selectSession(sessionId) {
            currentSessionId = sessionId;
            document.getElementById('message-input').disabled = false;
            document.getElementById('send-button').disabled = false;
            document.getElementById('message-input').focus();
            
            // Load session history
            loadSessionHistory(sessionId);
        }
        
        // Load session history
        async function loadSessionHistory(sessionId) {
            try {
                const response = await fetch(`/api/session_history/${sessionId}`);
                const data = await response.json();
                
                const messagesDiv = document.getElementById('chat-messages');
                messagesDiv.innerHTML = '';
                
                data.history.forEach(entry => {
                    addMessage(entry.role, entry.content, entry.timestamp);
                });
            } catch (error) {
                console.error('Failed to load session history:', error);
            }
        }
        
        // Send message
        async function sendMessage() {
            const input = document.getElementById('message-input');
            const message = input.value.trim();
            
            if (!message || !currentSessionId) {
                return;
            }
            
            addMessage('user', message, Date.now());
            input.value = '';
            
            try {
                const response = await fetch('/api/send_message', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        session_id: currentSessionId,
                        message: message
                    })
                });
                
                if (!response.ok) {
                    const error = await response.json();
                    showError(error.error);
                }
            } catch (error) {
                console.error('Failed to send message:', error);
                showError('Failed to send message');
            }
        }
        
        // Add message to chat
        function addMessage(role, content, timestamp) {
            const messagesDiv = document.getElementById('chat-messages');
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${role}`;
            
            const time = new Date(timestamp).toLocaleTimeString();
            messageDiv.innerHTML = `
                <div class="message-content">${content}</div>
                <div class="message-time">${time}</div>
            `;
            
            messagesDiv.appendChild(messageDiv);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }
        
        // Compare providers
        async function compareProviders() {
            const message = document.getElementById('comparison-message').value.trim();
            if (!message) {
                showError('Please enter a message to compare');
                return;
            }
            
            try {
                const response = await fetch('/api/compare', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        message: message,
                        providers: ['gemini', 'ollama', 'copilot', 'qwen']
                    })
                });
                
                const data = await response.json();
                
                const resultsDiv = document.getElementById('comparison-results');
                resultsDiv.innerHTML = '';
                
                for (const [provider, result] of Object.entries(data)) {
                    const item = document.createElement('div');
                    item.className = 'comparison-item';
                    item.innerHTML = `
                        <div class="comparison-provider">${provider}</div>
                        <div class="comparison-response">${result.response}</div>
                    `;
                    resultsDiv.appendChild(item);
                }
            } catch (error) {
                console.error('Failed to compare providers:', error);
                showError('Failed to compare providers');
            }
        }
        
        // UI helpers
        function refreshProviders() {
            loadProviders();
        }
        
        function refreshSessions() {
            loadSessions();
        }
        
        function showComparison() {
            document.getElementById('comparison-panel').style.display = 'block';
        }
        
        function hideComparison() {
            document.getElementById('comparison-panel').style.display = 'none';
        }
        
        function showError(message) {
            const errorDiv = document.createElement('div');
            errorDiv.className = 'error';
            errorDiv.textContent = message;
            document.body.insertBefore(errorDiv, document.body.firstChild);
            
            setTimeout(() => {
                errorDiv.remove();
            }, 5000);
        }
        
        // Enter key to send message
        document.getElementById('message-input').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                sendMessage();
            }
        });
        
        // Initial load
        loadProviders();
        loadSessions();
    </script>
</body>
</html>
"""

@app.route('/templates/<path:filename>')
def serve_template(filename):
    """Serve template files."""
    return HTML_TEMPLATE


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description="AI Provider Orchestrator Web Interface")
    parser.add_argument('--host', default='127.0.0.1', help='Host to bind to')
    parser.add_argument('--port', type=int, default=5000, help='Port to bind to')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    
    args = parser.parse_args()
    
    print(f"🚀 Starting AI Provider Orchestrator Web Interface")
    print(f"📍 URL: http://{args.host}:{args.port}")
    print(f"🔧 Debug mode: {'enabled' if args.debug else 'disabled'}")
    print()
    
    socketio.run(app, host=args.host, port=args.port, debug=args.debug)