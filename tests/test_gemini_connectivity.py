import unittest
import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ariadne.core.ai import ai

class TestGeminiConnection(unittest.TestCase):
    def test_simple_generation(self):
        """Check if we can talk to Gemini"""
        print("Testing Gemini Connection...")
        try:
            # We bypass the complex graph extraction and just ask for a specialized Hello
            response = ai.client.models.generate_content(
                model="gemini-2.0-flash-exp",
                contents="Say 'Hello Ariadne' and nothing else."
            )
            print(f"Gemini Replied: {response.text}")
            self.assertIn("Ariadne", response.text)
        except Exception as e:
            self.fail(f"Gemini Connection Failed: {e}")

if __name__ == '__main__':
    unittest.main()
