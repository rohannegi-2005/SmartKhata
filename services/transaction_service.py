import unicodedata
import pandas as pd
from domain.transaction import Transaction

class TransactionService:
    def __init__(self, repository):
        self.repository = repository

    def save_transaction(self, transaction):
        self.repository.save(transaction)

    def get_ledger_for_customer(self, search_name):
        """Logic to search customer and calculate totals"""
        all_data = self.repository.get_all()
        if not all_data:
            return None

        # Normalize search string
        search_norm = unicodedata.normalize('NFC', search_name.strip()).lower()
        
        stats = {
            'udhar_records': [],
            'paid_records': [],
            'udhar_total': 0,
            'paid_total': 0,
            'net_balance': 0
        }

        for key, record in all_data.items():
            # Handle different naming conventions in your DB
            raw_name = record.get('customer_name') or record.get('name', '')
            rec_norm = unicodedata.normalize('NFC', raw_name.strip()).lower()

            if rec_norm == search_norm:
                amount = int(record.get('amount', 0))
                t_type = record.get('type')

                if t_type == 'Udhar':
                    stats['udhar_records'].append(record)
                    stats['udhar_total'] += amount
                elif t_type == 'Paid':
                    stats['paid_records'].append(record)
                    stats['paid_total'] += amount

        stats['net_balance'] = stats['udhar_total'] - stats['paid_total']
        return stats

    def get_analytics_dataframe(self):
        """Prepares data for Plotly charts"""
        all_data = self.repository.get_all()
        if not all_data:
            return pd.DataFrame()
            
        df = pd.DataFrame(all_data.values())
        
        # Cleanup Data
        if "amount" in df.columns:
            df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0).astype(int)
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
        # Normalize name column
        if "customer_name" not in df.columns and "name" in df.columns:
            df["customer_name"] = df["name"]
            
        return df