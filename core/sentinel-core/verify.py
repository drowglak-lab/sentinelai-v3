import sentinel_core
import time

# 1. Adding a policy for writing to the database
sentinel_core.add_policy("rule_db_protection", "db_write", 10)
print("✅ Policy 'db_write' added to Rust Store")

# 2. Testing a secure request
start = time.perf_counter_ns()
res_safe = sentinel_core.fast_evaluate("db_write", 0.3)
end = time.perf_counter_ns()

print(f"\n[SAFE REQUEST]")
print(f"Decision: {res_safe.decision}")  # Must be Allow
print(f"Reason: {res_safe.reason}")
print(f"Python-measured Latency: {(end - start)/1000:.2f} microseconds")

# 3. Testing a dangerous request (risk > 0.8)
res_block = sentinel_core.fast_evaluate("db_write", 0.95)

print(f"\n[DANGEROUS REQUEST]")
print(f"Decision: {res_block.decision}")  # Must be Deny
print(f"Reason: {res_block.reason}")
