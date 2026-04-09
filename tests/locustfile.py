import json
from locust import FastHttpUser, task, between, events

class SentinelAILoadTest(FastHttpUser):
    """
    Simulates high-frequency requests from external systems to the AI Gateway.
    Using FastHttpUser for maximum throughput.
    """
    
    # Simulates network latency/think time between requests (10ms to 50ms)
    wait_time = between(0.01, 0.05)

    @task
    def test_agent_execution(self):
        """
        Simulates a complex AI agent request requiring both Shield (PII) 
        and Firewall (RBAC/ABAC) processing.
        """
        headers = {
            "Content-Type": "application/json",
            "x-agent-token": "valid_secret_token"  # Must match our mock dependency
        }
        
        # A realistic payload representing a wealth management intent
        payload = {
            "prompt": "Please transfer $4000 to my saving account and summarize my recent crypto expenses. My card is 1234-5678-9012-3456.",
            "tool_calls": [
                {
                    "name": "transfer_funds",
                    "arguments": {
                        "amount": 4000.0,
                        "target_account": "SAVINGS_001"
                    }
                },
                {
                    "name": "read_balance",
                    "arguments": {}
                }
            ]
        }

        # Catch response allows us to mark requests as failed based on custom logic, not just HTTP 500s
        with self.client.post(
            "/v1/agent/execute", 
            data=json.dumps(payload), 
            headers=headers, 
            catch_response=True,
            timeout=2.0 # Hard timeout - if it takes >2s, it's a failure in High-Frequency Trading
        ) as response:
            
            if response.status_code == 200:
                response.success()
            elif response.status_code == 403:
                # We expect 403 if the firewall blocks it, so technically the system worked
                response.success()
            else:
                response.failure(f"Failed with status {response.status_code}: {response.text}")
