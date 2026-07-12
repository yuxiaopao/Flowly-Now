"""
Comprehensive Agent Module Test Suite
Tests Agent CRUD, Chat with Ollama, Tools, Execution, Stream Chat, and Conversations.
"""
import requests
import json
import time
import sys
from datetime import datetime

BASE_URL = "http://localhost:8000/api/v1"
FRONTEND_URL = "http://localhost:5200"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{'=' * 70}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.RESET}")
    print(f"{'=' * 70}")

def print_test(name, passed, detail=""):
    icon = f"{Colors.GREEN}PASS{Colors.RESET}" if passed else f"{Colors.RED}FAIL{Colors.RESET}"
    print(f"  [{icon}] {name}")
    if detail:
        print(f"         {detail}")

class AgentTestSuite:
    def __init__(self):
        self.token = None
        self.refresh_token = None
        self.user_id = None
        self.agent_id = None
        self.conversation_id = None
        self.test_results = []
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})

    def _get_token_from_response(self, data: dict) -> tuple:
        """Extract tokens from wrapped API response format."""
        if "access" in data:
            return data.get("access"), data.get("refresh")
        if "data" in data and isinstance(data["data"], dict):
            return data["data"].get("access"), data["data"].get("refresh")
        return None, None

    def _get_data(self, response: requests.Response) -> dict:
        """Extract data from wrapped API response or plain response."""
        try:
            data = response.json()
        except:
            return {}
        if isinstance(data, dict):
            if "data" in data:
                return data["data"]
            if "results" in data:
                return data
            return data
        return data

    def _get_id(self, response: requests.Response) -> str:
        """Extract ID from wrapped API response."""
        data = self._get_data(response)
        return data.get("id") if isinstance(data, dict) else None

    def log_result(self, name, passed, detail=""):
        self.test_results.append({"name": name, "passed": passed, "detail": detail})
        print_test(name, passed, detail)
        return passed

    # =====================================================================
    # WORKFLOW 1: Authentication
    # =====================================================================
    def test_auth_login(self):
        print_header("WORKFLOW 1: Authentication")
        passed = True

        # Try logging in with existing users first
        login_success = False
        for username, password in [
            ("TestUser789", "TestUser123!"),
            ("testuser01", "TestUser123!"),
            ("sucker", "TestUser123!"),
        ]:
            r = self.session.post(f"{BASE_URL}/auth/login/", json={
                "username": username,
                "password": password
            })
            if r.status_code == 200:
                data = r.json()
                self.token, self.refresh_token = self._get_token_from_response(data)
                if self.token:
                    self.session.headers.update({"Authorization": f"Bearer {self.token}"})
                    self.log_result("Login with existing credentials", True,
                                  f"Logged in as {username}, Token (first 30 chars: {self.token[:30]}...)")
                    login_success = True
                    break
                else:
                    self.log_result("Login with existing credentials", False, f"Status 200 but no token in response: {str(data)[:200]}")
            else:
                pass  # Try next user

        if not login_success:
            # Register a new test user
            print(f"\n  {Colors.YELLOW}No existing user found. Registering new test user...{Colors.RESET}")
            reg_r = self.session.post(f"{BASE_URL}/auth/register/", json={
                "username": f"agenttest_{int(time.time())}",
                "email": f"agenttest_{int(time.time())}@test.com",
                "password": "TestPass123!",
                "password_confirm": "TestPass123!",
            })
            if reg_r.status_code == 201:
                data = reg_r.json()
                self.token, self.refresh_token = self._get_token_from_response(data)
                if self.token:
                    self.session.headers.update({"Authorization": f"Bearer {self.token}"})
                    self.log_result("Register and login test user", True,
                                  f"Token (first 30 chars: {self.token[:30]}...)")
                    login_success = True
                else:
                    self.log_result("Register and login test user", False,
                                  f"Status 201 but no token: {str(data)[:200]}")
            else:
                self.log_result("Login/Register", False,
                              f"Status {reg_r.status_code}: {reg_r.text[:300]}")
                passed = False

        # Test with invalid credentials
        no_auth_session = requests.Session()
        no_auth_session.headers.update({"Content-Type": "application/json"})
        r2 = no_auth_session.post(f"{BASE_URL}/auth/login/", json={
            "username": "admin",
            "password": "wrongpassword"
        })
        self.log_result("Reject invalid credentials", r2.status_code == 400 or r2.status_code == 401,
                       f"Status {r2.status_code} (expected 400/401)")

        return passed

    # =====================================================================
    # WORKFLOW 2: Agent CRUD Operations
    # =====================================================================
    def test_agent_crud(self):
        print_header("WORKFLOW 2: Agent CRUD Operations")
        passed = True

        # CREATE - Test 1: Create agent with all fields
        r = self.session.post(f"{BASE_URL}/agents/", json={
            "name": "Ollama Test Agent",
            "description": "Test agent powered by Ollama qwen2.5-coder",
            "agent_type": "conversational",
            "system_prompt": "You are a helpful AI coding assistant powered by Ollama. You have access to tools.",
            "model": "qwen2.5-coder:7b",
            "temperature": 0.7,
            "max_tokens": 2000,
            "tools": ["calculator", "search", "weather"],
            "skills": ["coding", "research"],
            "memory_enabled": True,
            "context_window": 10,
        })
        if r.status_code in [200, 201]:
            data = self._get_data(r)
            self.agent_id = data.get("id") if isinstance(data, dict) else None
            self.log_result("Create agent with full fields", True,
                          f"Agent ID: {self.agent_id}")
        else:
            self.log_result("Create agent with full fields", False, f"Status {r.status_code}: {r.text[:300]}")
            passed = False

        # CREATE - Test 2: Create minimal agent
        r2 = self.session.post(f"{BASE_URL}/agents/", json={
            "name": "Minimal Agent",
            "agent_type": "task"
        })
        self.log_result("Create agent with minimal fields", r2.status_code in [200, 201],
                       f"Status {r2.status_code}")

        # READ - Test 3: List agents
        r3 = self.session.get(f"{BASE_URL}/agents/")
        if r3.status_code == 200:
            data = self._get_data(r3)
            count = len(data.get("results", [])) if isinstance(data, dict) else len(data) if isinstance(data, list) else 0
            self.log_result("List agents", True, f"Found {count} agents")
        else:
            self.log_result("List agents", False, f"Status {r3.status_code}")
            passed = False

        # READ - Test 4: Get single agent
        if self.agent_id:
            r4 = self.session.get(f"{BASE_URL}/agents/{self.agent_id}/")
            if r4.status_code == 200:
                data = self._get_data(r4)
                self.log_result("Get single agent", True,
                              f"Name: {data.get('name') if isinstance(data, dict) else 'N/A'}, Model: {data.get('model') if isinstance(data, dict) else 'N/A'}")
            else:
                self.log_result("Get single agent", False, f"Status {r4.status_code}")
                passed = False

        # UPDATE - Test 5: Update agent
        if self.agent_id:
            r5 = self.session.patch(f"{BASE_URL}/agents/{self.agent_id}/", json={
                "description": "Updated description via API test",
                "temperature": 0.5,
            })
            self.log_result("Update agent (PATCH)", r5.status_code == 200,
                           f"Status {r5.status_code}")

        # UPDATE - Test 6: Duplicate agent
        if self.agent_id:
            r6 = self.session.post(f"{BASE_URL}/agents/{self.agent_id}/duplicate/")
            if r6.status_code in [200, 201]:
                dup_data = self._get_data(r6)
                self.log_result("Duplicate agent", True, f"Duplicated as: {dup_data.get('name') if isinstance(dup_data, dict) else 'N/A'}")
            else:
                self.log_result("Duplicate agent", False, f"Status {r6.status_code}: {r6.text[:100]}")

        # DELETE - Test 7: Delete agent
        if self.agent_id:
            r7 = self.session.delete(f"{BASE_URL}/agents/{self.agent_id}/")
            self.log_result("Delete agent", r7.status_code == 204,
                           f"Status {r7.status_code}")

        return passed

    # =====================================================================
    # WORKFLOW 3: Agent Chat with Ollama
    # =====================================================================
    def test_agent_chat(self):
        print_header("WORKFLOW 3: Agent Chat with Ollama (GPU)")
        passed = True

        # Create a fresh agent for chat testing
        r = self.session.post(f"{BASE_URL}/agents/", json={
            "name": "Chat Test Agent",
            "agent_type": "conversational",
            "system_prompt": "You are a helpful assistant. Keep responses brief.",
            "model": "qwen2.5-coder:7b",
            "temperature": 0.7,
            "max_tokens": 500,
            "tools": ["calculator"],
        })
        if r.status_code not in [200, 201]:
            self.log_result("Create chat agent", False, f"Status {r.status_code}: {r.text[:200]}")
            return False

        agent_data = self._get_data(r)
        chat_agent_id = agent_data.get("id") if isinstance(agent_data, dict) else None
        self.log_result("Create chat agent", True, f"Agent ID: {chat_agent_id}")

        # Test 1: Simple chat (no tools)
        print(f"\n  {Colors.YELLOW}Testing Ollama LLM response... (may take a few seconds){Colors.RESET}")
        r2 = self.session.post(f"{BASE_URL}/agents/{chat_agent_id}/chat/", json={
            "message": "Say hello in exactly 5 words."
        }, timeout=150)
        if r2.status_code == 200:
            data = self._get_data(r2)
            response = data.get("response", "") if isinstance(data, dict) else ""
            self.log_result("Simple chat with Ollama", True,
                          f"Response: {response[:100]}...")
        else:
            self.log_result("Simple chat with Ollama", False,
                           f"Status {r2.status_code}: {r2.text[:200]}")
            passed = False

        # Test 2: Multi-turn conversation
        r3 = self.session.post(f"{BASE_URL}/agents/{chat_agent_id}/chat/", json={
            "message": "What is 15 + 27?"
        }, timeout=150)
        if r3.status_code == 200:
            data = self._get_data(r3)
            response = data.get("response", "") if isinstance(data, dict) else ""
            self.log_result("Multi-turn conversation", True,
                          f"Response: {response[:100]}...")
        else:
            self.log_result("Multi-turn conversation", False,
                           f"Status {r3.status_code}: {r3.text[:200]}")
            passed = False

        # Test 3: Stream chat
        try:
            r4 = self.session.post(f"{BASE_URL}/agents/{chat_agent_id}/stream_chat/", json={
                "message": "Count from 1 to 3."
            }, stream=True, timeout=150)
            if r4.status_code == 200:
                chunks = []
                for line in r4.iter_lines():
                    if line:
                        line = line.decode('utf-8')
                        if line.startswith("data: "):
                            try:
                                data = json.loads(line[6:])
                                if data.get("type") == "content":
                                    chunks.append(data.get("content", ""))
                                elif data.get("type") == "done":
                                    break
                            except json.JSONDecodeError:
                                pass
                full_response = "".join(chunks)
                self.log_result("Stream chat (SSE)", True,
                              f"Received {len(chunks)} chunks, response: {full_response[:80]}...")
            else:
                self.log_result("Stream chat (SSE)", False,
                               f"Status {r4.status_code}: {r4.text[:200]}")
                passed = False
        except Exception as e:
            self.log_result("Stream chat (SSE)", False, f"Exception: {str(e)}")
            passed = False

        # Test 4: Chat with tools
        r5 = self.session.post(f"{BASE_URL}/agents/{chat_agent_id}/chat/", json={
            "message": "Calculate: sqrt(144) + 10"
        }, timeout=150)
        if r5.status_code == 200:
            data = self._get_data(r5)
            tool_calls = data.get("tool_calls", []) if isinstance(data, dict) else []
            response = data.get("response", "") if isinstance(data, dict) else ""
            self.log_result("Chat with calculator tool", True,
                          f"Response: {response[:100]}..., Tool calls: {len(tool_calls)}")
        else:
            self.log_result("Chat with calculator tool", False,
                           f"Status {r5.status_code}: {r5.text[:200]}")
            passed = False

        # Test 5: Empty message rejection
        r6 = self.session.post(f"{BASE_URL}/agents/{chat_agent_id}/chat/", json={
            "message": ""
        })
        self.log_result("Reject empty message", r6.status_code == 400,
                       f"Status {r6.status_code} (expected 400)")

        # Cleanup
        self.session.delete(f"{BASE_URL}/agents/{chat_agent_id}/")

        return passed

    # =====================================================================
    # WORKFLOW 4: Agent Tools and Skills
    # =====================================================================
    def test_agent_tools(self):
        print_header("WORKFLOW 4: Agent Tools and Skills")
        passed = True

        # Create agent with tools
        r = self.session.post(f"{BASE_URL}/agents/", json={
            "name": "Tools Test Agent",
            "agent_type": "task",
            "tools": ["calculator", "search"],
        })
        if r.status_code not in [200, 201]:
            self.log_result("Create tools test agent", False, f"Status {r.status_code}")
            return False
        agent_data = self._get_data(r)
        tool_agent_id = agent_data.get("id") if isinstance(agent_data, dict) else None
        self.log_result("Create agent with tools", True, f"Agent ID: {tool_agent_id}")

        # Test 1: Get available tools
        r2 = self.session.get(f"{BASE_URL}/agents/tools/available/")
        if r2.status_code == 200:
            tools = self._get_data(r2)
            tool_names = [t.get("name") for t in tools] if isinstance(tools, list) else []
            self.log_result("List available tools", True,
                          f"Tools: {', '.join(tool_names)}")
        else:
            self.log_result("List available tools", False, f"Status {r2.status_code}")
            passed = False

        # Test 2: Get agent tools
        r3 = self.session.get(f"{BASE_URL}/agents/{tool_agent_id}/tools/")
        if r3.status_code == 200:
            data = self._get_data(r3)
            self.log_result("Get agent tools", True,
                          f"Available: {data.get('available_tools')}, "
                          f"Agent tools: {data.get('agent_tools')}")
        else:
            self.log_result("Get agent tools", False, f"Status {r3.status_code}")
            passed = False

        # Test 3: Update agent tools
        r4 = self.session.post(f"{BASE_URL}/agents/{tool_agent_id}/tools/", json={
            "tools": ["calculator", "weather", "datetime"]
        })
        if r4.status_code == 200:
            data = self._get_data(r4)
            self.log_result("Update agent tools", True,
                          f"New tools: {data.get('tools')}")
        else:
            self.log_result("Update agent tools", False, f"Status {r4.status_code}")
            passed = False

        # Test 4: Remove tool
        r5 = self.session.delete(f"{BASE_URL}/agents/{tool_agent_id}/tools_remove/", json={
            "tool": "weather"
        })
        if r5.status_code == 200:
            data = self._get_data(r5)
            self.log_result("Remove tool from agent", True,
                          f"Remaining: {data.get('tools')}")
        else:
            self.log_result("Remove tool from agent", False, f"Status {r5.status_code}")
            passed = False

        # Test 5: Get agent skills
        r6 = self.session.get(f"{BASE_URL}/agents/{tool_agent_id}/skills/")
        if r6.status_code == 200:
            data = self._get_data(r6)
            self.log_result("Get agent skills", True, f"Skills: {data.get('skills')}")
        else:
            self.log_result("Get agent skills", False, f"Status {r6.status_code}")
            passed = False

        # Test 6: Update agent skills
        r7 = self.session.patch(f"{BASE_URL}/agents/{tool_agent_id}/update_skills/", json={
            "skills": ["coding", "research", "data_analysis"]
        })
        if r7.status_code == 200:
            data = self._get_data(r7)
            self.log_result("Update agent skills", True,
                          f"New skills: {data.get('skills')}")
        else:
            self.log_result("Update agent skills", False, f"Status {r7.status_code}")
            passed = False

        # Test 7: Reset memory
        r8 = self.session.post(f"{BASE_URL}/agents/{tool_agent_id}/reset_memory/")
        self.log_result("Reset agent memory", r8.status_code == 200,
                       f"Status {r8.status_code}")

        # Cleanup
        self.session.delete(f"{BASE_URL}/agents/{tool_agent_id}/")

        return passed

    # =====================================================================
    # WORKFLOW 5: Agent Conversations
    # =====================================================================
    def test_agent_conversations(self):
        print_header("WORKFLOW 5: Agent Conversations")
        passed = True

        # Create agent
        r = self.session.post(f"{BASE_URL}/agents/", json={
            "name": "Conversation Test Agent",
            "agent_type": "conversational",
            "model": "qwen2.5-coder:7b",
            "memory_enabled": True,
        })
        if r.status_code not in [200, 201]:
            self.log_result("Create conversation agent", False, f"Status {r.status_code}")
            return False
        conv_agent_id = self._get_id(r)
        self.log_result("Create conversation agent", True, f"Agent ID: {conv_agent_id}")

        # Test 1: Create conversation via chat
        r2 = self.session.post(f"{BASE_URL}/agents/{conv_agent_id}/chat/", json={
            "message": "Hello, remember my name is TestUser."
        }, timeout=150)
        if r2.status_code == 200:
            data = self._get_data(r2)
            self.conversation_id = data.get("conversation_id") if isinstance(data, dict) else None
            self.log_result("Create conversation via chat", True,
                          f"Conversation ID: {self.conversation_id}")
        else:
            self.log_result("Create conversation via chat", False,
                           f"Status {r2.status_code}: {r2.text[:200]}")
            passed = False

        # Test 2: Continue conversation with existing ID
        if self.conversation_id:
            r3 = self.session.post(f"{BASE_URL}/agents/{conv_agent_id}/chat/", json={
                "message": "What is my name?",
                "conversation_id": self.conversation_id
            }, timeout=150)
            if r3.status_code == 200:
                data = self._get_data(r3)
                resp = data.get("response", "") if isinstance(data, dict) else ""
                self.log_result("Continue conversation", True,
                              f"Response: {resp[:80]}...")
            else:
                self.log_result("Continue conversation", False,
                               f"Status {r3.status_code}")
                passed = False

        # Test 3: List conversations (nested under agents router)
        r4 = self.session.get(f"{BASE_URL}/agents/conversations/?agent_id={conv_agent_id}")
        if r4.status_code == 200:
            data = self._get_data(r4)
            count = len(data.get("results", [])) if isinstance(data, dict) else len(data) if isinstance(data, list) else 0
            self.log_result("List conversations", True, f"Found {count} conversations")
        else:
            self.log_result("List conversations", False,
                           f"Status {r4.status_code}: {r4.text[:200]}")

        # Test 4: Get conversation messages
        if self.conversation_id:
            r5 = self.session.get(f"{BASE_URL}/agents/conversations/{self.conversation_id}/messages/")
            if r5.status_code == 200:
                data = self._get_data(r5)
                self.log_result("Get conversation messages", True,
                              f"Message count: {data.get('message_count') if isinstance(data, dict) else 'N/A'}")
            else:
                self.log_result("Get conversation messages", False,
                               f"Status {r5.status_code}")
                passed = False

        # Test 5: Add message manually
        if self.conversation_id:
            r6 = self.session.post(f"{BASE_URL}/agents/conversations/{self.conversation_id}/add_message/", json={
                "role": "user",
                "content": "Manual test message"
            })
            self.log_result("Add message to conversation", r6.status_code == 200,
                           f"Status {r6.status_code}")

        # Cleanup
        self.session.delete(f"{BASE_URL}/agents/{conv_agent_id}/")

        return passed

    # =====================================================================
    # WORKFLOW 6: Agent Execution & Debug
    # =====================================================================
    def test_agent_execution(self):
        print_header("WORKFLOW 6: Agent Execution & Debug")
        passed = True

        # Create agent
        r = self.session.post(f"{BASE_URL}/agents/", json={
            "name": "Execution Test Agent",
            "agent_type": "task",
            "model": "qwen2.5-coder:7b",
            "system_prompt": "You are a task execution agent.",
        })
        if r.status_code not in [200, 201]:
            self.log_result("Create execution agent", False, f"Status {r.status_code}")
            return False
        exec_agent_id = self._get_id(r)
        self.log_result("Create execution agent", True, f"Agent ID: {exec_agent_id}")

        # Test 1: Debug agent
        print(f"\n  {Colors.YELLOW}Testing debug execution... (may take a few seconds){Colors.RESET}")
        r2 = self.session.post(f"{BASE_URL}/agents/{exec_agent_id}/debug/", json={
            "message": "What is the capital of France?",
            "context": {"test": True}
        }, timeout=150)
        if r2.status_code == 200:
            data = self._get_data(r2)
            self.log_result("Debug agent execution", True,
                          f"Response: {data.get('response', '')[:80] if isinstance(data, dict) else 'N/A'}..., "
                          f"Execution ID: {data.get('execution_id') if isinstance(data, dict) else 'N/A'}")
        else:
            self.log_result("Debug agent execution", False,
                           f"Status {r2.status_code}: {r2.text[:200]}")
            passed = False

        # Test 2: Get debug history
        r3 = self.session.get(f"{BASE_URL}/agents/{exec_agent_id}/debug_history/")
        if r3.status_code == 200:
            data = self._get_data(r3)
            count = len(data) if isinstance(data, list) else 0
            self.log_result("Get debug history", True, f"Found {count} executions")
        else:
            self.log_result("Get debug history", False, f"Status {r3.status_code}")
            passed = False

        # Test 3: Get executions (nested under agents router)
        r4 = self.session.get(f"{BASE_URL}/agents/executions/")
        if r4.status_code == 200:
            data = self._get_data(r4)
            count = len(data.get("results", [])) if isinstance(data, dict) else len(data) if isinstance(data, list) else 0
            self.log_result("List agent executions", True, f"Found {count} executions")
        else:
            self.log_result("List agent executions", False, f"Status {r4.status_code}: {r4.text[:200]}")
            passed = False

        # Test 4: Clear debug history
        r5 = self.session.delete(f"{BASE_URL}/agents/{exec_agent_id}/debug_history/")
        self.log_result("Clear debug history", r5.status_code == 200,
                       f"Status {r5.status_code}")

        # Cleanup
        self.session.delete(f"{BASE_URL}/agents/{exec_agent_id}/")

        return passed

    # =====================================================================
    # WORKFLOW 7: Edge Cases and Error Handling
    # =====================================================================
    def test_edge_cases(self):
        print_header("WORKFLOW 7: Edge Cases and Error Handling")
        passed = True

        # Test 1: Get agent with invalid UUID
        r = self.session.get(f"{BASE_URL}/agents/invalid-uuid/")
        self.log_result("Reject invalid UUID", r.status_code == 404,
                       f"Status {r.status_code} (expected 404)")

        # Test 2: Chat with non-existent agent
        r2 = self.session.post(f"{BASE_URL}/agents/00000000-0000-0000-0000-000000000000/chat/", json={
            "message": "test"
        })
        self.log_result("Reject chat with non-existent agent", r2.status_code == 404,
                       f"Status {r2.status_code} (expected 404)")

        # Test 3: Create agent with invalid type
        r3 = self.session.post(f"{BASE_URL}/agents/", json={
            "name": "Bad Type Agent",
            "agent_type": "invalid_type"
        })
        self.log_result("Reject invalid agent type", r3.status_code in [400, 422],
                       f"Status {r3.status_code} (expected 400/422)")

        # Test 4: Unauthenticated request
        no_auth_session = requests.Session()
        no_auth_session.headers.update({"Content-Type": "application/json"})
        r4 = no_auth_session.get(f"{BASE_URL}/agents/")
        self.log_result("Require authentication", r4.status_code == 401,
                       f"Status {r4.status_code} (expected 401)")

        # Test 5: Invalid conversation
        r5 = self.session.post(f"{BASE_URL}/agents/", json={
            "name": "Conv Edge Agent",
            "agent_type": "conversational"
        })
        if r5.status_code in [200, 201]:
            edge_agent_id = r5.json().get("id")
            r6 = self.session.post(f"{BASE_URL}/agents/{edge_agent_id}/chat/", json={
                "message": "test",
                "conversation_id": "00000000-0000-0000-0000-000000000000"
            }, timeout=30)
            self.log_result("Handle invalid conversation gracefully", r6.status_code in [200, 201, 404],
                           f"Status {r6.status_code}")
            self.session.delete(f"{BASE_URL}/agents/{edge_agent_id}/")

        return passed

    # =====================================================================
    # Print Summary
    # =====================================================================
    def print_summary(self):
        print_header("TEST SUMMARY")
        total = len(self.test_results)
        passed = sum(1 for r in self.test_results if r["passed"])
        failed = total - passed

        print(f"\n  Total Tests: {total}")
        print(f"  {Colors.GREEN}Passed: {passed}{Colors.RESET}")
        print(f"  {Colors.RED}Failed: {failed}{Colors.RESET}")
        print(f"  Success Rate: {passed/total*100:.1f}%")

        if failed > 0:
            print(f"\n  {Colors.RED}Failed Tests:{Colors.RESET}")
            for r in self.test_results:
                if not r["passed"]:
                    print(f"    - {r['name']}: {r['detail']}")

        return failed == 0

    def run_all(self):
        print(f"\n{Colors.BOLD}{'#' * 70}")
        print(f"#  Flowly Agent Module - Comprehensive Test Suite")
        print(f"#  Backend: {BASE_URL}")
        print(f"#  Frontend: {FRONTEND_URL}")
        print(f"#  Ollama: http://localhost:11434")
        print(f"#  Model: qwen2.5-coder:7b (GPU)")
        print(f"{'#' * 70}{Colors.RESET}")

        # Check backend health
        try:
            r = self.session.get(f"{BASE_URL.replace('/api/v1', '')}/health/", timeout=5)
            print(f"\n  Backend health: {r.status_code}")
        except:
            print(f"\n  {Colors.RED}WARNING: Backend may not be running at {BASE_URL}{Colors.RESET}")

        # Check Ollama
        try:
            r = requests.get("http://localhost:11434/api/tags", timeout=5)
            if r.status_code == 200:
                models = r.json().get("models", [])
                model_names = [m.get("name") for m in models]
                print(f"  Ollama models: {', '.join(model_names)}")
        except:
            print(f"  {Colors.YELLOW}WARNING: Ollama not reachable at localhost:11434{Colors.RESET}")

        self.test_auth_login()
        self.test_agent_crud()
        self.test_agent_chat()
        self.test_agent_tools()
        self.test_agent_conversations()
        self.test_agent_execution()
        self.test_edge_cases()

        all_passed = self.print_summary()
        return 0 if all_passed else 1


if __name__ == "__main__":
    suite = AgentTestSuite()
    sys.exit(suite.run_all())
