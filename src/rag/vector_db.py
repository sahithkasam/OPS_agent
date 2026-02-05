import chromadb
import json
import uuid

class KnowledgeBase:
    def __init__(self):
        # Using a simple in-memory client for demo portability, or persistent local directory
        self.client = chromadb.PersistentClient(path="./data/chroma_db")
        self.collection = self.client.get_or_create_collection(name="incidents")
        self.is_populated = False

    def populate(self, json_path):
        """
        Loads incidents from JSON and stores them in Chroma.
        """
        if self.collection.count() > 0:
            print("Vector DB already populated.")
            self.is_populated = True
            return

        with open(json_path, 'r') as f:
            data = json.load(f)

        ids = []
        documents = []
        metadatas = []

        for item in data:
            ids.append(item['id'])
            # Create a rich text representation for embedding
            doc_text = f"Title: {item['summary']}. Symptoms: {item['logs_signature']}. Cause: {item['root_cause']}. Fix: {item['resolution']}."
            documents.append(doc_text)
            metadatas.append(item)

        self.collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas
        )
        self.is_populated = True
        print(f"Populated Vector DB with {len(documents)} accumulated incidents.")

    def search(self, query_text, n_results=2):
        """
        Returns relevant past incidents based on query (current symptoms).
        """
        results = self.collection.query(
            query_texts=[query_text],
            n_results=n_results
        )
        return results
