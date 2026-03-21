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

    # ── LLM path ──────────────────────────────────────────────────────────────

    def _extract_with_ai(self, text):
        prompt = f"""
        Extract JSON ONLY from this transaction text.

        Fields:
        - customer_name: the person's name
        - item: the item name ONLY — no amounts, no prices, no "ka/का" prefix.
                Include physical quantity if mentioned (e.g. "1 kilo chawal", "2 litre tel").
                NEVER include the rupee amount in item. "500 का चावल" → item is "चावल", NOT "500 का चावल".
        - amount: the MONETARY value in rupees ONLY.
                  Patterns like "500 का", "200 ka", "₹300" are amounts.
                  Physical quantities (1 kilo, 2 litre, 3 kg) are NOT amounts — set amount to 0 in that case.
        - type: one of Udhar / Paid / Nagat
          - "Paid"  → customer paid back (keywords: chukaya, wapas, diya, वापस, चुकाया)
          - "Udhar" → credit transaction (keywords: udhar, उधार, उधर)
          - "Nagat" → normal purchase

        Examples (read carefully):
        - "राम 500 का चावल उधार लिया"            → item: "चावल",          amount: 500, type: Udhar
        - "Ram ne 500 ka chawal liya"             → item: "chawal",        amount: 500, type: Nagat
        - "Ram ne 1 kilo chawal udhar liya"       → item: "1 kilo chawal", amount: 0,   type: Udhar
        - "Ram ne 2 litre tel 80 rupay mein liya" → item: "2 litre tel",   amount: 80,  type: Nagat
        - "Shyam ne 200 wapas diya"               → item: "उधार चुकाया",  amount: 200, type: Paid

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

        # Safety net: strip any "NUMBER का/ka/ke" the LLM snuck into item
        # NOTE: \b works for ASCII (ka/ke/ki). Devanagari का is matched without \b.
        item = data.get("item", "")
        item = re.sub(r"^\d+\s*(का|ka\b|ke\b|ki\b|की|के)\s*", "", item, flags=re.IGNORECASE).strip()
        data["item"] = item

        return data

    # ── helpers ───────────────────────────────────────────────────────────────

    def _extract_name(self, text):
        """Extract customer name — handles Hindi 'ने' and English 'ne'."""
        words = text.split()
        if "ने" in words:
            idx = words.index("ने")
            name = " ".join(words[:idx])
            return " ".join(w.capitalize() for w in name.split())
        m = re.search(r"^(.+?)\s+ne\s+", text, re.IGNORECASE)
        if m:
            return m.group(1).strip().title()
        return ""

    def _extract_amount(self, text):
        """
        Extract monetary amount only.
        Hindi का (Devanagari) uses no word boundary — \\b doesn't apply to non-ASCII.
        English ka uses \\b to avoid matching inside 'kachori', 'kal', etc.
        """
        t = text.lower()
        m = re.search(r"(\d+)\s*का", t)                              # Hindi: "500 का"
        if m: return int(m.group(1))
        m = re.search(r"(\d+)\s*(?:ka\b|rupay|rupee|rs\.?|₹)", t)   # English
        if m: return int(m.group(1))
        m = re.search(r"(?:₹|rs\.?)\s*(\d+)", t)                    # prefix form
        if m: return int(m.group(1))
        return 0

    def _clean_item(self, raw):
        """Strip 'NUMBER का/ka' prefix from item string."""
        return re.sub(r"^\d+\s*(का|ka\b|ke\b|ki\b|की|के)\s*", "", raw, flags=re.IGNORECASE).strip()

    # ── regex fallback ────────────────────────────────────────────────────────

    def _extract_with_regex(self, text):
        t      = text.lower()
        name   = self._extract_name(text)
        amount = self._extract_amount(text)
        item   = ""
        t_type = "Nagat"

        # ── Paid ─────────────────────────────────────────────────────────────
        if any(x in t for x in ["वापस", "chukaya", "चुकाया", "wapas"]):
            t_type = "Paid"
            item   = "उधार चुकाया"
            if amount == 0:                          # "राम ने 500 चुकाया" — no ka/का
                m = re.search(r"(\d+)", t)
                if m: amount = int(m.group(1))

        # ── Udhar ────────────────────────────────────────────────────────────
        elif any(x in t for x in ["उधार", "उधर", "udhar"]):
            t_type = "Udhar"

            # Case A: physical quantity — "1 kilo chawal udhar"
            qty_m = re.search(
                r"(\d+\s*(?:kilo|kg|gram|litre|liter|litr|packet|pav)\s+\w+)"
                r"\s+(?:उधार|उधर|udhar)", t
            )
            if qty_m:
                item = qty_m.group(1).strip()

            # Case B: monetary — "500 का/ka ITEM udhar"
            else:
                mon_m = re.search(r"\d+\s*(?:का|ka)\s+(.+?)\s+(?:उधार|उधर|udhar)", t)
                if mon_m:
                    item = mon_m.group(1).strip()
                else:
                    # Plain: last word before udhar keyword
                    plain_m = re.search(r"(\w+)\s+(?:उधार|उधर|udhar)", t)
                    if plain_m:
                        item = self._clean_item(plain_m.group(1).strip())

        # ── Nagat ─────────────────────────────────────────────────────────────
        else:
            # Case A: qty WITH price — "2 litre tel 80 rupay liya"
            qty_price_m = re.search(
                r"(\d+\s*(?:kilo|kg|gram|litre|liter|litr|packet|pav)\s+\w+)"
                r"\s+\d+\s*(?:rupay|rupee|rs|₹)", t
            )
            if qty_price_m:
                item = qty_price_m.group(1).strip()

            # Case B: qty WITHOUT price — "2 kilo chawal liya"
            else:
                qty_m = re.search(
                    r"(\d+\s*(?:kilo|kg|gram|litre|liter|litr|packet|pav)\s+\w+)"
                    r"\s+(?:लिया|liya)", t
                )
                if qty_m:
                    item = qty_m.group(1).strip()
                else:
                    # Case C: monetary — "500 ka ITEM liya"
                    mon_m = re.search(r"\d+\s*(?:का|ka)\s+(.+?)\s+(?:लिया|liya)", t)
                    if mon_m:
                        item = mon_m.group(1).strip()
                    else:
                        # Plain: last word before liya
                        plain_m = re.search(r"(\w+)\s+(?:लिया|liya)", t)
                        if plain_m:
                            item = self._clean_item(plain_m.group(1).strip())

            item = self._clean_item(item)

        return {
            "customer_name": name,
            "amount":        amount,
            "item":          item,
            "type":          t_type,
            "date":          datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
