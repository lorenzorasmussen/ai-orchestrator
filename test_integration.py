#!/usr/bin/env python3
"""
Integration Test Suite for AI Provider Orchestrator

Comprehensive testing framework to validate integration with all specified AI providers:
- Gemini CLI
- Ollama
- GitHub Copilot
- Qwen-code (via OpenAI-compatible API)
- Z.ai (via OpenAI-compatible API)

Test Categories:
- Provider availability checks
- Session management
- Message sending and receiving
- Error handling
- Performance benchmarks
- Configuration validation

Author: OpenCode Research Assistant
License: MIT
"""

import asyncio
import json
import os
import sys
import time
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional
import logging
from dataclasses import dataclass
import tempfile
import subprocess

# Add orchestrator to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from ai_provider_orchestrator import (
        AIProviderOrchestrator, 
        AISession, 
        ProviderConfig, 
        ProviderType,
        SessionStatus
    )
except ImportError:
    print("Error: ai_provider_orchestrator.py not found. Please ensure it's in the same directory.")
    sys.exit(1)


@dataclass
class TestResult:
    """Test result data structure."""
    provider_name: str
    test_name: str
    passed: bool
    duration: float
    error_message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class AIProviderIntegrationTests:
    """Integration test suite for AI providers."""
    
    def __init__(self):
        self.orchestrator = AIProviderOrchestrator("test_ai_providers.json")
        self.test_results: List[TestResult] = []
        self.logger = logging.getLogger("ai_integration_tests")
        self._setup_logging()
        self._create_test_config()
    
    def _setup_logging(self):
        """Setup logging for tests."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    def _create_test_config(self):
        """Create test configuration for all providers."""
        test_configs = [
            {
                "name": "test-gemini",
                "provider_type": "gemini-cli",
                "command": "echo",  # Mock command for testing
                "model": "gemini-pro",
                "max_tokens": 100,
                "temperature": 0.7,
                "timeout": 5,
                "env_vars": {},
                "additional_args": []
            },
            {
                "name": "test-ollama",
                "provider_type": "ollama",
                "api_endpoint": "http://localhost:11434",
                "model": "llama2",
                "max_tokens": 100,
                "temperature": 0.7,
                "timeout": 5,
                "env_vars": {},
                "additional_args": []
            },
            {
                "name": "test-copilot",
                "provider_type": "github-copilot",
                "command": "echo",  # Mock command for testing
                "model": None,
                "max_tokens": 100,
                "temperature": None,
                "timeout": 5,
                "env_vars": {},
                "additional_args": ["explain"]
            },
            {
                "name": "test-qwen",
                "provider_type": "openai-compatible",
                "api_endpoint": "http://localhost:8000/v1",
                "api_key": "test-key",
                "model": "qwen-coder",
                "max_tokens": 100,
                "temperature": 0.7,
                "timeout": 5,
                "env_vars": {},
                "additional_args": []
            },
            {
                "name": "test-zai",
                "provider_type": "openai-compatible",
                "api_endpoint": "https://api.z.ai/v1",
                "api_key": "test-key",
                "model": "zai-coder",
                "max_tokens": 100,
                "temperature": 0.7,
                "timeout": 5,
                "env_vars": {},
                "additional_args": []
            }
        ]
        
        try:
            with open("test_ai_providers.json", 'w') as f:
                json.dump(test_configs, f, indent=2)
            self.logger.info("Created test configuration file")
        except Exception as e:
            self.logger.error(f"Failed to create test config: {e}")
    
    def _record_result(self, result: TestResult):
        """Record a test result."""
        self.test_results.append(result)
        
        status = "✅ PASS" if result.passed else "❌ FAIL"
        self.logger.info(f"{status} {result.provider_name} - {result.test_name} ({result.duration:.3f}s)")
        
        if result.error_message:
            self.logger.error(f"    Error: {result.error_message}")
    
    async def test_provider_availability(self) -> List[TestResult]:
        """Test provider availability."""
        self.logger.info("Testing provider availability...")
        results = []
        
        for provider_name in self.orchestrator.list_providers():
            start_time = time.time()
            try:
                provider = self.orchestrator.get_provider(provider_name)
                if provider:
                    is_available = provider.is_available()
                    duration = time.time() - start_time
                    
                    result = TestResult(
                        provider_name=provider_name,
                        test_name="availability",
                        passed=is_available,
                        duration=duration,
                        details={"available": is_available}
                    )
                    results.append(result)
                else:
                    duration = time.time() - start_time
                    result = TestResult(
                        provider_name=provider_name,
                        test_name="availability",
                        passed=False,
                        duration=duration,
                        error_message="Provider not found"
                    )
                    results.append(result)
                    
            except Exception as e:
                duration = time.time() - start_time
                result = TestResult(
                    provider_name=provider_name,
                    test_name="availability",
                    passed=False,
                    duration=duration,
                    error_message=str(e)
                )
                results.append(result)
        
        return results
    
    async def test_session_creation(self) -> List[TestResult]:
        """Test session creation for available providers."""
        self.logger.info("Testing session creation...")
        results = []
        
        for provider_name in self.orchestrator.list_providers():
            provider = self.orchestrator.get_provider(provider_name)
            if not provider or not provider.is_available():
                continue
            
            start_time = time.time()
            try:
                session = await provider.start_session()
                duration = time.time() - start_time
                
                # Check if session was created successfully
                success = (session and 
                           hasattr(session, 'session_id') and 
                           session.session_id and
                           session.status == SessionStatus.ACTIVE)
                
                result = TestResult(
                    provider_name=provider_name,
                    test_name="session_creation",
                    passed=success,
                    duration=duration,
                    details={
                        "session_id": session.session_id if session else None,
                        "status": session.status.value if session else None
                    }
                )
                results.append(result)
                
                # Clean up session
                if session:
                    await provider.stop_session(session)
                    
            except Exception as e:
                duration = time.time() - start_time
                result = TestResult(
                    provider_name=provider_name,
                    test_name="session_creation",
                    passed=False,
                    duration=duration,
                    error_message=str(e)
                )
                results.append(result)
        
        return results
    
    async def test_message_sending(self) -> List[TestResult]:
        """Test message sending for providers that support it."""
        self.logger.info("Testing message sending...")
        results = []
        
        test_message = "Hello! This is a test message. Please respond with 'Test successful'."
        
        for provider_name in self.orchestrator.list_providers():
            provider = self.orchestrator.get_provider(provider_name)
            if not provider or not provider.is_available():
                continue
            
            start_time = time.time()
            try:
                # Create session
                session = await provider.start_session()
                if not session or session.status != SessionStatus.ACTIVE:
                    continue
                
                # Send message
                response = await provider.send_message(session, test_message)
                duration = time.time() - start_time
                
                # Check if we got a response
                success = (response is not None and 
                          len(response.strip()) > 0)
                
                result = TestResult(
                    provider_name=provider_name,
                    test_name="message_sending",
                    passed=success,
                    duration=duration,
                    details={
                        "response_length": len(response) if response else 0,
                        "response_preview": (response[:100] + "...") if response and len(response) > 100 else response
                    }
                )
                results.append(result)
                
                # Clean up session
                await provider.stop_session(session)
                
            except Exception as e:
                duration = time.time() - start_time
                result = TestResult(
                    provider_name=provider_name,
                    test_name="message_sending",
                    passed=False,
                    duration=duration,
                    error_message=str(e)
                )
                results.append(result)
        
        return results
    
    async def test_error_handling(self) -> List[TestResult]:
        """Test error handling for providers."""
        self.logger.info("Testing error handling...")
        results = []
        
        for provider_name in self.orchestrator.list_providers():
            provider = self.orchestrator.get_provider(provider_name)
            if not provider:
                continue
            
            start_time = time.time()
            try:
                # Test 1: Try to send message without session
                try:
                    fake_session = AISession(
                        session_id="fake-session",
                        provider_config=provider.config,
                        status=SessionStatus.ACTIVE
                    )
                    await provider.send_message(fake_session, "test")
                    error_handled = False
                except Exception:
                    error_handled = True
                
                # Test 2: Try to stop non-existent session
                try:
                    await provider.stop_session(fake_session)
                    stop_error_handled = False
                except Exception:
                    stop_error_handled = True
                
                duration = time.time() - start_time
                success = error_handled and stop_error_handled
                
                result = TestResult(
                    provider_name=provider_name,
                    test_name="error_handling",
                    passed=success,
                    duration=duration,
                    details={
                        "message_error_handled": error_handled,
                        "stop_error_handled": stop_error_handled
                    }
                )
                results.append(result)
                
            except Exception as e:
                duration = time.time() - start_time
                result = TestResult(
                    provider_name=provider_name,
                    test_name="error_handling",
                    passed=False,
                    duration=duration,
                    error_message=str(e)
                )
                results.append(result)
        
        return results
    
    async def test_configuration_validation(self) -> List[TestResult]:
        """Test configuration validation."""
        self.logger.info("Testing configuration validation...")
        results = []
        
        # Test valid configurations
        valid_configs = [
            {
                "name": "valid-gemini",
                "provider_type": "gemini-cli",
                "command": "echo",
                "model": "gemini-pro"
            },
            {
                "name": "valid-ollama",
                "provider_type": "ollama",
                "api_endpoint": "http://localhost:11434",
                "model": "llama2"
            }
        ]
        
        for config_data in valid_configs:
            start_time = time.time()
            try:
                config = ProviderConfig(**config_data)
                provider = self.orchestrator._create_provider(config)
                duration = time.time() - start_time
                
                result = TestResult(
                    provider_name=config_data["name"],
                    test_name="config_validation",
                    passed=provider is not None,
                    duration=duration,
                    details={"config_valid": True}
                )
                results.append(result)
                
            except Exception as e:
                duration = time.time() - start_time
                result = TestResult(
                    provider_name=config_data["name"],
                    test_name="config_validation",
                    passed=False,
                    duration=duration,
                    error_message=str(e)
                )
                results.append(result)
        
        # Test invalid configurations
        invalid_configs = [
            {
                "name": "invalid-type",
                "provider_type": "invalid-type",
                "command": "echo"
            },
            {
                "name": "missing-required",
                "provider_type": "gemini-cli"
                # Missing required fields
            }
        ]
        
        for config_data in invalid_configs:
            start_time = time.time()
            try:
                config = ProviderConfig(**config_data)
                provider = self.orchestrator._create_provider(config)
                duration = time.time() - start_time
                
                result = TestResult(
                    provider_name=config_data["name"],
                    test_name="config_validation",
                    passed=False,  # Should fail for invalid configs
                    duration=duration,
                    details={"config_valid": False, "error": "Should have failed"}
                )
                results.append(result)
                
            except Exception:
                # Expected to fail
                duration = time.time() - start_time
                result = TestResult(
                    provider_name=config_data["name"],
                    test_name="config_validation",
                    passed=True,  # Correctly rejected invalid config
                    duration=duration,
                    details={"config_valid": False, "correctly_rejected": True}
                )
                results.append(result)
        
        return results
    
    async def test_performance_benchmarks(self) -> List[TestResult]:
        """Test performance benchmarks."""
        self.logger.info("Testing performance benchmarks...")
        results = []
        
        for provider_name in self.orchestrator.list_providers():
            provider = self.orchestrator.get_provider(provider_name)
            if not provider or not provider.is_available():
                continue
            
            # Test session creation time
            start_time = time.time()
            try:
                session = await provider.start_session()
                creation_time = time.time() - start_time
                
                if session and session.status == SessionStatus.ACTIVE:
                    # Test message response time
                    msg_start = time.time()
                    try:
                        await provider.send_message(session, "Performance test message")
                        response_time = time.time() - msg_start
                        
                        result = TestResult(
                            provider_name=provider_name,
                            test_name="performance_benchmark",
                            passed=True,
                            duration=creation_time + response_time,
                            details={
                                "session_creation_time": creation_time,
                                "message_response_time": response_time,
                                "total_time": creation_time + response_time
                            }
                        )
                    except Exception:
                        response_time = float('inf')
                        result = TestResult(
                            provider_name=provider_name,
                            test_name="performance_benchmark",
                            passed=False,
                            duration=creation_time,
                            details={
                                "session_creation_time": creation_time,
                                "message_response_time": response_time,
                                "error": "Message sending failed"
                            }
                        )
                    
                    await provider.stop_session(session)
                else:
                    result = TestResult(
                        provider_name=provider_name,
                        test_name="performance_benchmark",
                        passed=False,
                        duration=creation_time,
                        error_message="Session creation failed"
                    )
                
                results.append(result)
                
            except Exception as e:
                duration = time.time() - start_time
                result = TestResult(
                    provider_name=provider_name,
                    test_name="performance_benchmark",
                    passed=False,
                    duration=duration,
                    error_message=str(e)
                )
                results.append(result)
        
        return results
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all integration tests."""
        self.logger.info("🚀 Starting AI Provider Integration Tests")
        self.logger.info("=" * 50)
        
        # Run all test categories
        test_categories = [
            ("Provider Availability", self.test_provider_availability),
            ("Session Creation", self.test_session_creation),
            ("Message Sending", self.test_message_sending),
            ("Error Handling", self.test_error_handling),
            ("Configuration Validation", self.test_configuration_validation),
            ("Performance Benchmarks", self.test_performance_benchmarks)
        ]
        
        for category_name, test_func in test_categories:
            self.logger.info(f"\n📋 Running {category_name} Tests...")
            results = await test_func()
            for result in results:
                self._record_result(result)
        
        # Generate summary
        return self._generate_summary()
    
    def _generate_summary(self) -> Dict[str, Any]:
        """Generate test summary report."""
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r.passed)
        failed_tests = total_tests - passed_tests
        
        # Group by provider
        provider_results = {}
        for result in self.test_results:
            if result.provider_name not in provider_results:
                provider_results[result.provider_name] = []
            provider_results[result.provider_name].append(result)
        
        # Group by test type
        test_type_results = {}
        for result in self.test_results:
            if result.test_name not in test_type_results:
                test_type_results[result.test_name] = []
            test_type_results[result.test_name].append(result)
        
        # Performance stats
        durations = [r.duration for r in self.test_results if r.passed]
        avg_duration = sum(durations) / len(durations) if durations else 0
        max_duration = max(durations) if durations else 0
        min_duration = min(durations) if durations else 0
        
        return {
            "summary": {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": failed_tests,
                "success_rate": (passed_tests / total_tests * 100) if total_tests > 0 else 0
            },
            "performance": {
                "average_duration": avg_duration,
                "min_duration": min_duration,
                "max_duration": max_duration
            },
            "by_provider": provider_results,
            "by_test_type": test_type_results,
            "all_results": self.test_results
        }
    
    def print_summary(self, summary: Dict[str, Any]):
        """Print formatted test summary."""
        print("\n" + "=" * 60)
        print("🧪 AI Provider Integration Test Results")
        print("=" * 60)
        
        # Overall summary
        summary_data = summary["summary"]
        print(f"\n📊 Overall Results:")
        print(f"   Total Tests: {summary_data['total_tests']}")
        print(f"   Passed: {summary_data['passed_tests']} ✅")
        print(f"   Failed: {summary_data['failed_tests']} ❌")
        print(f"   Success Rate: {summary_data['success_rate']:.1f}%")
        
        # Performance summary
        perf_data = summary["performance"]
        print(f"\n⚡ Performance Summary:")
        print(f"   Average Duration: {perf_data['average_duration']:.3f}s")
        print(f"   Min Duration: {perf_data['min_duration']:.3f}s")
        print(f"   Max Duration: {perf_data['max_duration']:.3f}s")
        
        # Provider breakdown
        print(f"\n🤖 Provider Breakdown:")
        for provider_name, results in summary["by_provider"].items():
            passed = sum(1 for r in results if r.passed)
            total = len(results)
            status = "✅" if passed == total else "⚠️" if passed > 0 else "❌"
            print(f"   {status} {provider_name}: {passed}/{total} tests passed")
            
            # Show failed tests for this provider
            failed = [r for r in results if not r.passed]
            for failed_test in failed:
                print(f"      ❌ {failed_test.test_name}: {failed_test.error_message}")
        
        # Test type breakdown
        print(f"\n📋 Test Type Breakdown:")
        for test_name, results in summary["by_test_type"].items():
            passed = sum(1 for r in results if r.passed)
            total = len(results)
            status = "✅" if passed == total else "⚠️" if passed > 0 else "❌"
            print(f"   {status} {test_name.replace('_', ' ').title()}: {passed}/{total} tests passed")
        
        # Recommendations
        print(f"\n💡 Recommendations:")
        if summary_data['success_rate'] < 80:
            print("   ⚠️  Low success rate. Check provider configurations and dependencies.")
        
        failed_providers = [name for name, results in summary["by_provider"].items() 
                          if all(not r.passed for r in results)]
        if failed_providers:
            print(f"   ❌ Failed providers: {', '.join(failed_providers)}")
            print("   💡 Install and configure these providers to improve results.")
        
        slow_providers = [name for name, results in summary["by_provider"].items()
                        if any(r.duration > 5.0 for r in results if r.passed)]
        if slow_providers:
            print(f"   ⏱️  Slow providers: {', '.join(slow_providers)}")
            print("   💡 Consider optimizing timeouts or checking network connectivity.")
        
        print("\n" + "=" * 60)
    
    def cleanup(self):
        """Clean up test artifacts."""
        try:
            if os.path.exists("test_ai_providers.json"):
                os.remove("test_ai_providers.json")
                self.logger.info("Cleaned up test configuration file")
        except Exception as e:
            self.logger.error(f"Failed to cleanup: {e}")


async def main():
    """Main test runner."""
    import argparse
    
    parser = argparse.ArgumentParser(description="AI Provider Integration Tests")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--category", choices=[
        "availability", "session_creation", "message_sending", 
        "error_handling", "config_validation", "performance"
    ], help="Run specific test category")
    parser.add_argument("--provider", help="Run tests for specific provider only")
    parser.add_argument("--output", help="Save results to JSON file")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Run tests
    test_suite = AIProviderIntegrationTests()
    
    try:
        if args.category:
            # Run specific category
            category_map = {
                "availability": test_suite.test_provider_availability,
                "session_creation": test_suite.test_session_creation,
                "message_sending": test_suite.test_message_sending,
                "error_handling": test_suite.test_error_handling,
                "config_validation": test_suite.test_configuration_validation,
                "performance": test_suite.test_performance_benchmarks
            }
            
            results = await category_map[args.category]()
            for result in results:
                test_suite._record_result(result)
            
            summary = test_suite._generate_summary()
        else:
            # Run all tests
            summary = await test_suite.run_all_tests()
        
        # Print summary
        test_suite.print_summary(summary)
        
        # Save results if requested
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(summary, f, indent=2)
            print(f"\n💾 Results saved to: {args.output}")
        
    except KeyboardInterrupt:
        print("\n⚠️  Tests interrupted by user")
    except Exception as e:
        print(f"\n❌ Test execution failed: {e}")
    finally:
        test_suite.cleanup()


if __name__ == "__main__":
    asyncio.run(main())