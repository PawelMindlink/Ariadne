# Strategy: Ariadne AI Agent 🧠

## 1. Inversion Thinking (What to AVOID) ⛔
To ensure this system is cheap, easy, and effective, we must avoid these "Anti-Patterns":
*   **❌ Avoid "Black Box" SaaS**: Do not upload your entire database to a third-party "Chat with CSV" tool. 
    *   *Why*: Privacy risk, monthly fees, and they might delete your history.
    *   *Instead*: Keep data **local** (SQLite). Send only *snippets* to the AI.
*   **❌ Avoid Generic RAG**: Do not index every single JSON number into a vector database immediately. 
    *   *Why*: Over-engineering. Your data is structured (Time-Series). SQL is better than Vector Search for "How many steps did I take in July?".
    *   *Instead*: Use **Text-to-SQL**. The Agent writes SQL to get the exact data.
*   **❌ Avoid Statelessness**: Do not build a script that forgets context.
    *   *Why*: You want it to "know you".
    *   *Instead*: Maintain a `conversation_history` table in your DB.

## 2. Recommended Approach: "Ariadne: Local Brain, Cloud Genius" ✨
*   **Interface**: Streamlit Chat (built into your existing app).
*   **Brain (LLM)**: **Gemini API**. It's cost-effective (free tier available) and has a massive context window (perfect for analyzing months of health logs).
*   **Mechanism**:
    1.  **You Ask**: "How does my sleep affect my recovery?"
    2.  **Agent Thinks**: "I need sleep scores and recovery data."
    3.  **Tool Use**: Agent queries your local SQLite DB.
    4.  **Analysis**: Agent reads the numbers and explains the pattern to you using Gemini.
    
## 3. Data Structure & Sources
*   **The Conflict**: You have "Steps" from Garmin and "Steps" from Google Fit.
*   **The Fix**: Our DB schema (`source_id`) already handles this.
*   **Agent's Job**: The Agent must be taught: *"If the user asks for Steps, prefer Garmin (Source 1) because it has a Trust Score of 9, vs Google (Source 2) with 7."*

## 4. Next Steps
1.  **Get API Key**: You will need a Gemini API Key (free).
2.  **Build `agent.py`**: A new Streamlit page for the chat interaction.
