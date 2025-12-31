from domain.transaction import Transaction

class VoiceService:
    def __init__(self, speech_engine, extractor):
        self.speech_engine = speech_engine
        self.extractor = extractor

    def process_voice_command(self):
        # 1. Listen
        text = self.speech_engine.listen()
        # 2. Extract (AI or Regex)
        data = self.extractor.extract(text)
        
        # 3. Return a nice Object
        return Transaction(
            customer_name=data.get("customer_name", "Unknown"),
            amount=data.get("amount", 0),
            item=data.get("item", ""),
            t_type=data.get("type", "Nagat"),
            date=data.get("date")
        )