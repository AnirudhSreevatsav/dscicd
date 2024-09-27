from pymongo import MongoClient
from app.constants.config import MONGODB_URI, DATABASE_NAME


class MongoDB:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MongoDB, cls).__new__(cls)
            cls._instance._init_connection(MONGODB_URI, DATABASE_NAME)
        return cls._instance

    def _init_connection(self, uri, db_name):
        self.client = MongoClient(uri)
        self.db = self.client[db_name]

    def get_collection(self, collection_name):
        return self.db[collection_name]

    def insert_one(self, collection_name, data):
        return self.get_collection(collection_name).insert_one(data).inserted_id

    def find_one(self, collection_name, query, projection=None):
        return self.get_collection(collection_name).find_one(query, projection)

    def find(self, collection_name, query, projection=None):
        return list(self.get_collection(collection_name).find(query, projection))

    def update_one(
        self, collection_name, query, update_data, upsert=False
    ):
        collection = self.get_collection(collection_name)
        return collection.update_one(
            query, update_data, upsert=upsert
        )

    def delete_one(self, collection_name, query):
        return self.get_collection(collection_name).delete_one(query)
    
    def aggregate(self, collection_name, pipeline):
        collection = self.db[collection_name]
        return list(collection.aggregate(pipeline))


mongo_util = MongoDB()
