import os
import requests
import time

class GitHubEmbedder:
    def __init__(self):
        self.token = os.environ.get("GITHUB_TOKEN")
        self.endpoint = "https://models.inference.ai.azure.com/embeddings" # Check current endpoint

    def embed(self, texts):
        if not texts: return []
        
        try:
            response = requests.post(
                self.endpoint,
                headers={"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"},
                json={"input": texts, "model": "text-embedding-3-small"}
            )
            if response.status_code == 200:
                data = response.json()
                # Ensure sorted by index
                sorted_data = sorted(data['data'], key=lambda x: x['index'])
                return [d['embedding'] for d in sorted_data]
            else:
                print(f"Embedding API Error: {response.status_code}")
                return [[] for _ in texts] # Return empty vectors on fail
        except Exception as e:
            print(f"Embed Exception: {e}")
            return [[] for _ in texts]