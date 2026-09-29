<p align="center">
  <img src="docs/images/keeper-logo.png" alt="Keeper Logo" width="500"/>
</p>

<h2 align="center">Keeper - AI-Powered Shared Memory for Saving and Retrieving Everyday Information</h2>

<p align="center">
  <strong>Gaia Eldad and Ori Weiss</strong>
</p>

### 1.1 Problem & Motivation

In everyday life, people constantly come across useful information they want to keep: recipes, receipts, links, recommendations, images, screenshots, and more. However, this information is often scattered across chats and messages, making it difficult to find later, especially when users do not remember the exact wording, date, or format. Our goal was to create a more natural way to build a digital memory using **WhatsApp as the main interface**, since it is already part of our everyday communication and requires no new interaction habits. Instead of manually adding titles, categories, tags, or organizing content, users can simply send text, a link, or an image, and the system processes and organizes it automatically. Search is based on meaning rather than exact keyword matching, allowing users to ask naturally, for example, *“Where is the recipe with mushrooms that we saved?”* or *“Show me the receipt from the restaurant.”* The system also supports **shared memory spaces**, allowing multiple users to contribute to and retrieve information from the same shared collection.

### 1.2 Project Goal & System Overview

The goal of the project is to build an intelligent shared-memory assistant that allows multiple users to save and retrieve different types of information with minimal effort. Users interact mainly through WhatsApp, where text, URLs, and images are processed into a shared memory that supports semantic search, direct retrieval of specific items, and RAG-based answers over the stored knowledge. A web dashboard provides an additional way to browse and view the shared memory.

## 2. System Specification

### 2.1 User Interaction Overview

- **Saving information** — Users send content through WhatsApp and receive a confirmation once it has been saved.
- **Retrieving information** — Users can request a specific item using a natural-language message.
- **Asking the memory** — Broader questions can be answered using relevant information already stored in the shared memory.
- **Shared interaction** — Multiple users can contribute to and retrieve information from the same memory space.
- **Browsing stored content** — The web dashboard provides an additional visual interface for exploring the saved information.

### 2.2 High-Level System Flow

The system supports two main interaction flows: saving new information and retrieving or asking questions over previously stored information.

```text
                         User
                          │
                       WhatsApp
                      /        \
                     /          \
              Save Content    Search / Ask
                   │               │
                   └───────┬───────┘
                           ▼
                     Shared Memory
                    /      |       \
                   ▼       ▼        ▼
        Confirmation   Saved Item   Web Dashboard
                          / Answer
                          
```

### 3.2 Technology Choices

- **Python + FastAPI** — Backend development, webhooks, and straightforward integration with AI and external services.
- **Supabase** — Combines PostgreSQL, `pgvector` semantic search, and image storage in one platform.
- **Gemini** — Used for intent classification, content enrichment, embeddings, image understanding, and RAG-based answer generation.
- **WhatsApp Cloud API** — Provides a familiar and natural interface for everyday user interaction.
- **HTML, CSS & JavaScript** — Used to build the web dashboard for browsing stored information.

### 3.3 WhatsApp Integration & Message Handling

The WhatsApp Cloud API serves as the main communication interface, with FastAPI handling incoming webhook events.

- **Message identification** — Each message is associated with the relevant user and active shared space.
- **Direct handling** — Commands and media types are detected and handled directly.
- **Intent classification** — Gemini distinguishes between SAVE and SEARCH requests, with rule-based heuristics as a fallback.
- **Routing** — The request is forwarded to the corresponding ingestion or retrieval pipeline.
- **Response** — The result is returned to the user through WhatsApp.

### 3.4 Information Ingestion & Storage

Each SAVE request follows a type-specific processing flow before being normalized into a common memory-item structure.

- **Text** — Enriched with a title, summary, category, and tags.
- **URLs** — The page is fetched and cleaned to extract its main content before enrichment.
- **Images** — Gemini Vision generates a description and extracts visible text.
- **Unified representation** — Content and generated metadata are combined into a common searchable representation.
- **Embedding & storage** — A 768-dimensional document embedding and the structured item data are stored in Supabase, while image binaries are stored in Supabase Storage.

#### Save Pipeline

<p align="center">
  <a href="docs/images/save-pipeline.png">
    <img src="docs/images/save-pipeline.png" alt="Keeper Save Pipeline" width="100%"/>
  </a>
</p>

### 3.5 Semantic Search, Retrieval & RAG

SEARCH requests pass through a semantic retrieval pipeline:

1. **Query embedding** — The query is converted into a 768-dimensional embedding.
2. **Vector comparison** — It is compared against stored document embeddings using vector similarity.
3. **Ranking & threshold** — Candidates are ranked by similarity score, and results below the minimum relevance threshold are rejected.
4. **Type-aware refinement** — Terms indicating a link or image can prioritize the corresponding content type.
5. **Response selection** — Specific-item requests use direct retrieval, while broader questions retrieve multiple relevant items and pass them to Gemini as context for a RAG-based answer.

#### Search & RAG Pipeline

<p align="center">
  <a href="docs/images/search-rag-pipeline.png">
    <img src="docs/images/search-rag-pipeline.png" alt="Keeper Search and RAG Pipeline" width="100%"/>
  </a>
</p>

### 3.6 Shared Spaces & Multi-User Memory

Shared memory is implemented through `app_users`, `spaces`, and `space_members`.

- Each user has an `active_space_id` and may belong to multiple spaces.
- SAVE and SEARCH operations are scoped to the active space, isolating retrieval to the relevant shared memory.
- `/join <invite_code>` creates the user's membership in a space and sets it as active.
- Multiple users within the same space can save and retrieve information from the same shared memory.

### 3.7 Web Dashboard

The Web Dashboard provides a structured view of the shared memory accumulated through WhatsApp.

- **Automatic organization** — Users submit only raw content, while the ingestion pipeline generates titles, categories, summaries, and tags automatically.
- **Shared data source** — The dashboard reads the processed items directly from Supabase, using the same stored memory as the WhatsApp interface.
- **Browsing & filtering** — Stored information can be browsed, searched, and filtered by category.
- **Item details** — Users can open individual items to view their stored content and generated metadata.

### 3.8 Engineering Decisions & Iterative Improvements

Testing exposed several failure cases that led to targeted implementation improvements:

- **Duplicate webhooks** — `source_message_id` is checked before processing, alongside a database uniqueness constraint, to prevent duplicate memory items.
- **Noisy URL content** — Non-content HTML elements are removed and the main page content is prioritized before generating embeddings.
- **Incorrect content type** — Type-aware retrieval was added after semantic similarity alone occasionally returned the correct topic but the wrong source type.
- **AI availability** — Gemini `429/503` failures led to rule-based intent fallbacks and basic URL metadata extraction, allowing core flows to continue even when AI enrichment is temporarily unavailable.

## 4. Demonstration

The following examples demonstrate the main user flows of the system through WhatsApp, including saving different content types, retrieving the original stored content, and asking broader questions using RAG.

<p align="center">
  <img src="docs/screenshots/text-save-and-rag.jpg" alt="Saving text and asking questions through WhatsApp" width="30%"/>
  <img src="docs/screenshots/image-retrieval-and-rag.jpg" alt="Image retrieval and RAG-based question" width="30%"/>
  <img src="docs/screenshots/receipt-image-query.jpg" alt="Querying information extracted from an image" width="30%"/>
</p>

<p align="center">
  <img src="docs/screenshots/url-save-and-retrieval.jpg" alt="Saving and retrieving a URL" width="30%"/>
  <img src="docs/screenshots/image-and-url-save.jpg" alt="Saving image and URL content" width="30%"/>
</p>

The system answers only from information stored in the shared memory. If no relevant information is found, it returns an appropriate response instead of inventing an answer.

<p align="center">
  <img src="docs/screenshots/failed-retrieval.jpg" alt="Failed retrieval for information not stored in memory" width="30%"/>
</p>


## 5. Conclusion

The project demonstrated how a simple messaging interface can be extended into a structured shared-memory system through careful separation between ingestion, storage, retrieval, and generation. One of the main engineering insights was that using a unified semantic representation made the system easier to extend across different content types, while combining deterministic logic with AI improved efficiency, reliability, and control over the retrieval flow. The iterative development process also showed the value of refining the architecture based on real failure cases rather than relying on a purely AI-driven solution.

Future work could expand shared-space management, improve retrieval and ranking, and support additional content types and richer context-aware interactions.