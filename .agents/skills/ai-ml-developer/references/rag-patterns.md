# RAG Implementation Patterns

Comprehensive guide to Retrieval-Augmented Generation (RAG) architectures for production LLM applications.

## Architecture Overview

```
Documents → Chunking → Embedding → Vector Store
                                        ↓
User Query → Query Processing → Retrieval → Reranking → LLM → Response
```

## Vector Databases

| Database | Type | Best For |
|:---------|:-----|:---------|
| **Pinecone** | Managed | Scalable production, fast queries |
| **Weaviate** | Open-source | Hybrid search, GraphQL API |
| **Qdrant** | Open-source | Filtering, high performance |
| **Chroma** | Open-source | Prototyping, local development |
| **Milvus** | Open-source | Large scale, on-premise |
| **pgvector** | PostgreSQL | Existing Postgres infrastructure |

## Embedding Models

| Model | Dimensions | Best For |
|:------|:-----------|:---------|
| text-embedding-3-large | 1536 | General purpose, high quality |
| text-embedding-3-small | 512 | Cost-sensitive applications |
| BGE-large-en-v1.5 | 1024 | Open-source, high quality |
| e5-large-v2 | 1024 | Multilingual support |
| all-MiniLM-L6-v2 | 384 | Fast, lightweight |

## Chunking Strategies

### Recursive Character Splitting
```python
from langchain.text_splitters import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
    separators=["\n\n", "\n", " ", ""]
)
```

### Semantic Chunking
```python
from langchain.text_splitters import SemanticChunker

splitter = SemanticChunker(
    embeddings=OpenAIEmbeddings(),
    breakpoint_threshold_type="percentile"
)
```

### Document-Structure Aware
- Split by headers for Markdown/HTML
- Preserve code blocks together
- Keep tables as single chunks

## Retrieval Patterns

### 1. Hybrid Search (Dense + Sparse)
```python
from langchain.retrievers import EnsembleRetriever, BM25Retriever

bm25_retriever = BM25Retriever.from_documents(chunks)
dense_retriever = vectorstore.as_retriever()

hybrid = EnsembleRetriever(
    retrievers=[bm25_retriever, dense_retriever],
    weights=[0.3, 0.7]
)
```

### 2. Multi-Query Retrieval
Generate multiple query variations to improve recall:
```python
from langchain.retrievers.multi_query import MultiQueryRetriever

retriever = MultiQueryRetriever.from_llm(
    retriever=vectorstore.as_retriever(),
    llm=ChatOpenAI()
)
```

### 3. Parent Document Retriever
Retrieve small chunks, return larger parent documents:
```python
from langchain.retrievers import ParentDocumentRetriever

retriever = ParentDocumentRetriever(
    vectorstore=vectorstore,
    docstore=InMemoryStore(),
    child_splitter=RecursiveCharacterTextSplitter(chunk_size=400),
    parent_splitter=RecursiveCharacterTextSplitter(chunk_size=2000)
)
```

### 4. Contextual Compression
Extract only relevant parts of retrieved documents:
```python
from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors import LLMChainExtractor

compression_retriever = ContextualCompressionRetriever(
    base_compressor=LLMChainExtractor.from_llm(llm),
    base_retriever=vectorstore.as_retriever()
)
```

## Reranking

### Cross-Encoder Reranking
```python
from sentence_transformers import CrossEncoder

reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
candidates = vectorstore.similarity_search(query, k=20)
pairs = [[query, doc.page_content] for doc in candidates]
scores = reranker.predict(pairs)
reranked = sorted(zip(candidates, scores), key=lambda x: x[1], reverse=True)[:5]
```

### Cohere Rerank API
```python
import cohere

co = cohere.Client(api_key)
results = co.rerank(
    query=query,
    documents=[doc.page_content for doc in candidates],
    top_n=5,
    model="rerank-english-v3.0"
)
```

## Advanced Patterns

### HyDE (Hypothetical Document Embeddings)
Generate hypothetical answer, use its embedding for retrieval:
```python
hypothetical_doc = llm.generate(f"Write a passage that answers: {query}")
results = vectorstore.similarity_search_by_vector(
    embed(hypothetical_doc)
)
```

### RAG-Fusion
Multiple queries + reciprocal rank fusion:
```python
queries = generate_query_variations(original_query)
all_results = [retrieve(q) for q in queries]
fused = reciprocal_rank_fusion(all_results)
```

### Self-RAG
Iteratively retrieve and verify:
1. Generate initial answer
2. Check if grounded in retrieved docs
3. If not, retrieve more context
4. Repeat until grounded

## Evaluation Metrics

| Metric | Description |
|:-------|:------------|
| **MRR** | Mean Reciprocal Rank of first relevant doc |
| **NDCG@K** | Normalized Discounted Cumulative Gain |
| **Precision@K** | Relevant docs in top K |
| **Recall@K** | Coverage of all relevant docs |
| **Groundedness** | Answer supported by retrieved context |

## Best Practices

1. **Chunk Size**: 500-1000 tokens for most use cases
2. **Overlap**: 10-20% to preserve context at boundaries
3. **Metadata**: Include source, page, timestamp for filtering
4. **Hybrid Search**: Combine semantic + keyword for best results
5. **Reranking**: Always rerank top-k for higher precision
6. **Citations**: Return source documents for transparency
7. **Monitoring**: Track retrieval quality in production
