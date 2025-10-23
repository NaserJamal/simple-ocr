import requests

response = requests.post(
    "https://your-model-endpoint.com/model-id/v1/embeddings",
    headers={"Authorization": "Bearer api-key-here-keep-bearer-prefix"},
    json={"model": "text-embedding-3-small", "input": "test"}
)

print(response.json())
