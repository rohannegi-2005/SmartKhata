import firebase_admin
from firebase_admin import credentials, db

class FirebaseRepository:
    def __init__(self, creds, db_url):
        if not firebase_admin._apps:
            # On Streamlit Cloud: creds is a dict from st.secrets
            # Locally: creds is a string file path to the JSON key
            if isinstance(creds, dict):
                cred = credentials.Certificate(creds)
            else:
                cred = credentials.Certificate(creds)
            firebase_admin.initialize_app(cred, {"databaseURL": db_url})
        self.ref = db.reference("transactions")

    def save(self, transaction):
        self.ref.push(transaction.to_dict())

    def get_all(self):
        return self.ref.get()
