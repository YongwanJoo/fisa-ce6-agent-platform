from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct

client = QdrantClient(host="localhost", port=6333)

# 벡터 데이터 삽입
client.upsert(
    collection_name="test_collection",
    points=[
        PointStruct(id=1, vector=[0.1, 0.2, 0.3, 0.4], payload={"text": "안녕하세요"}),
        PointStruct(id=2, vector=[0.9, 0.8, 0.7, 0.6], payload={"text": "반갑습니다"}),
    ]
)

# 유사 벡터 검색
results = client.search(
    collection_name="test_collection",
    query_vector=[0.1, 0.2, 0.3, 0.4],
    limit=2
)

for r in results:
    print(f"id={r.id} score={r.score:.4f} text={r.payload['text']}")