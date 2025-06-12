import requests
import json

BASE_URL = "http://localhost:8002/api/v1"

def create_collection(name):
    """Creates a new collection."""
    url = f"{BASE_URL}/collections"
    headers = {"Content-Type": "application/json"}
    data = {"collection_name": name}
    response = requests.post(url, headers=headers, data=json.dumps(data))
    print(f"Create '{name}': {response.status_code} {response.text}")

def list_collections():
    """Lists all collections."""
    url = f"{BASE_URL}/collections"
    response = requests.get(url)
    print(f"List collections: {response.status_code} {response.json()}")

def delete_collection(name):
    """Deletes a collection."""
    url = f"{BASE_URL}/collections/{name}"
    response = requests.delete(url)
    print(f"Delete '{name}': {response.status_code} {response.text}")

if __name__ == "__main__":
    print("--- Testing API ---")
    
    # 1. Start with a clean slate by listing collections
    print("\nInitial state:")
    list_collections()
    
    # 2. Create the new collection
    print("\nCreating 'refactor_test'...")
    create_collection("refactor_test")
    
    # 3. List to verify creation
    print("\nState after creation:")
    list_collections()

    # 4. Delete the collection
    print("\nDeleting 'refactor_test'...")
    delete_collection("refactor_test")

    # 5. List to verify deletion
    print("\nFinal state:")
    list_collections() 