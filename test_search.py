from src.vectorstore.weaviate_search import similarity_search

DOC_VERSION = "TMEP Nov 2025"

query = "Likelihood of confusion between similar marks"

results = similarity_search(
    query=query,
    top_k=5,
    doc_version=DOC_VERSION,
    debug=True
)

print("\nRetrieved Sections:")
for r in results:
    print(f"{r['section_id']} → Similarity: {r['similarity']}")