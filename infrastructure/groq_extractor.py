from groq import Groq
from datetime import datetime
import json
import re

class GroqExtractor:
    def __init__(self, api_key):
        self.client = Groq(api_key=api_key)

    def extract(self, text):
        try:
            return self._extract_with_ai(text)
        except Exception as e:
            print(f"AI Failed ({e}), switching to Regex fallback...")
            return self._extract_with_regex(text)

    def _extract_with_ai(self, text):
        prompt = f"""
        Extract JSON ONLY:
        Fields:
        - customer_name
        - item
        - amount (numeric only)
        - type (Udhar / Paid / Nagat)
        
        Rules:
        - "Paid" if words like 'chukaya', 'wapas', 'diya' exist.
        - "Udhar" if 'udhar' exists.
        
        Text: "{text}"
        """
        response = self.client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        raw = response.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.replace("```json", "").replace("```", "").strip()
        
        data = json.loads(raw)
        data["date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return data

    def _extract_with_regex(self, text):
        # This is your original 'extract_info' logic
        t = text.lower()
        words = t.split()
        
        name = ""
        if "ने" in words:
            ne_index = words.index("ने")
            name = " ".join(words[:ne_index])
        name = " ".join(w.capitalize() for w in name.split())

        amount_match = re.search(r"\b(\d{1,5})\b", t)
        amount = int(amount_match.group(1)) if amount_match else 0

        item = ""
        t_type = "Nagat"

        if any(x in t for x in ["वापस", "दिया", "दीया", "दिए"]):
            t_type = "Paid"
            item = "उधार चुकाया"
        elif any(x in t for x in ["उधार", "उधर", "udhar"]):
            t_type = "Udhar"
            item_match = re.search(r"का\s+(.*?)\s+(उधार|उधर)", t)
            if item_match: item = item_match.group(1).strip()
        else:
            item_match = re.search(r"का\s+(.*?)\s+(लिया)", t)
            if item_match: item = item_match.group(1).strip()

        return {
            "customer_name": name,
            "amount": amount,
            "item": item,
            "type": t_type,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }