import sys
import os
import sqlite3

# Add Apps to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '03_Apps'))
import agent

# Mock user query
query = "My Vitamin B12 levels are extremely high (over 1000). What could be the cause? Show me if I took any supplements."

print(f"🔹 USER: {query}")
print("-" * 50)

# Get response (Simulated)
# Note: agent.get_gemini_response writes to cache DB logic.
try:
    response = agent.get_gemini_response(query)
    print(f"🔸 AGENT (Diagnostician):\n{response}")
except Exception as e:
    print(f"❌ ERROR: {e}")

print("-" * 50)
print("✅ Verification Check:")
print("1. Did it ask clarifying questions? approx.")
print("2. Did it mention supplements? approx.")
