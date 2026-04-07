import os
import anthropic
from typing import List, Dict, Any, Optional

class ClaudeFinalizer:
    """
    Skill for final human-like polish and data validation using Claude.
    Used for the definitive finish and detailed lead information.
    """
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("CLAUDE_API_KEY")
        if not self.api_key:
            self.enabled = False
            self.client = None
        else:
            self.enabled = True
            self.client = anthropic.AsyncAnthropic(api_key=self.api_key)

    async def finalize_list(self, refined_leads: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Polish and finalize lead lists.
        """
        if not self.enabled:
            return {"success": False, "error": "CLAUDE_API_KEY missing", "provider": "claude"}
        prompt = f"""
Review the following list of business leads.
1.  Verify the structure and format.
2.  Clean up any formatting inconsistencies.
3.  Ensure the data follows professional standards.

LEADS:
{refined_leads}

Return the final polished list.
"""
        try:
            response = await self.client.messages.create(
                model="claude-3-5-sonnet-20240620",
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt}]
            )
            return {"success": True, "final_data": response.content[0].text, "provider": "claude"}
        except Exception as e:
            return {"success": False, "error": str(e), "provider": "claude"}
