from datetime import datetime

class Transaction:
    def __init__(self, customer_name, amount, item, t_type, date=None):
        self.customer_name = customer_name
        self.amount = int(amount)
        self.item = item
        self.type = t_type
        # If date is not provided, use current time
        self.date = date if date else datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def to_dict(self):
        return {
            "customer_name": self.customer_name,
            "amount": self.amount,
            "item": self.item,
            "type": self.type,
            "date": self.date
        }