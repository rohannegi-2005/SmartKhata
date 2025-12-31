import firebase_admin
from firebase_admin import credentials, db

class FirebaseRepository:
    def __init__(self, cert_path, db_url):
        if not firebase_admin._apps:
            cred = credentials.Certificate(cert_path)
            firebase_admin.initialize_app(cred, {'databaseURL': db_url})
        self.ref = db.reference("transactions")

    def save(self, transaction):
        self.ref.push(transaction.to_dict())

    def get_all(self):
        """Returns all data as a dictionary or None"""
        return self.ref.get()