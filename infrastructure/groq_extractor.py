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
        Extract JSON ONLY from this transaction text.

        Fields:
        - customer_name: the person's name
        - item: the full item description INCLUDING quantity if mentioned (e.g. "1 kilo chawal", "2 litre tel", "chawal")
        - amount: the MONETARY value in rupees ONLY — a number that represents money/price/rupees.
                  If no monetary amount is mentioned (only quantity like "1 kilo", "2 litre"), set amount to 0.
                  IMPORTANT: quantity numbers (kilo, litre, kg, gram) are NOT monetary amounts.
        - type: one of Udhar / Paid / Nagat
          Rules for type:
          - "Paid"  → customer paid back money (keywords: chukaya, wapas, diya)
          - "Udhar" → credit/debt transaction (keyword: udhar)
          - "Nagat" → normal purchase, neither of above

        Examples:
        - "Ram ne 1 kilo chawal udhar liya" → item: "1 kilo chawal", amount: 0, type: Udhar
        - "Ram ne 500 ka chawal liya"       → item: "chawal", amount: 500, type: Nagat
        - "Ram ne 2 litre tel 80 rupay mein liya" → item: "2 litre tel", amount: 80, type: Nagat
        - "Shyam ne 200 wapas diya"         → item: "udhar chukaya", amount: 200, type: Paid

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
        t = text.lower()
        words = t.split()

        name = ""
        if "ने" in words:
            ne_index = words.index("ने")
            name = " ".join(words[:ne_index])
        name = " ".join(w.capitalize() for w in name.split())

        # Only match amount if preceded by currency context (ka, rupay, rs, ₹)
        # Ignore standalone numbers that are likely quantities
        amount = 0
        currency_match = re.search(r"(\d+)\s*(ka|rupay|rs|₹|rupe)", t)
        if currency_match:
            amount = int(currency_match.group(1))

        # Extract item WITH quantity if present (e.g. "1 kilo chawal", "2 litre tel")
        item = ""
        quantity_match = re.search(r"(\d+\s*(?:kilo|kg|gram|litre|liter|litr|packet|pav)?\s*\w+)", t)

        t_type = "Nagat"

        if any(x in t for x in ["वापस", "दिया", "दीया", "दिए", "wapas", "chukaya"]):
            t_type = "Paid"
            item = "उधार चुकाया"
        elif any(x in t for x in ["उधार", "उधर", "udhar"]):
            t_type = "Udhar"
            # Try to capture quantity + item together
            item_match = re.search(r"(\d+\s*(?:kilo|kg|gram|litre|liter|packet)?\s*\w+)\s+(?:उधार|उधर|udhar)", t)
            if item_match:
                item = item_match.group(1).strip()
            else:
                item_match = re.search(r"का\s+(.*?)\s+(?:उधार|उधर)", t)
                if item_match:
                    item = item_match.group(1).strip()
        else:
            item_match = re.search(r"का\s+(.*?)\s+(?:लिया|liya)", t)
            if item_match:
                item = item_match.group(1).strip()

        return {
            "customer_name": name,
            "amount": amount,
            "item": item,
            "type": t_type,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
