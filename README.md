# Layout Agent POC

A chat-based layout agent that transforms design JSON using natural language instructions. 

## Approach and Problem Solving
When tackling this problem of modifying a complex layout JSON via natural language, a naive approach would be passing the entire JSON to an LLM and asking for a completely rewritten JSON object in return. That approach is extremely fragile, highly prone to coordinate hallucinations, expensive (high token usage) and lacks auditability. 

To solve this reliably, I built an agentic loop. We provided the LLM with a discrete set of rigid tools (e.g., move_node, resize_node, change_aspect_ratio, set_node_style). The agent analyzes the natural language request, decides which specific tools to invoke, and our deterministic Python backend executes the mathematical changes. This ensures that complex state requirements—like keeping absolute pixel dimensions and normalized layout coordinates perfectly in sync—are handled accurately by backend logic, not guessed by the language model. The updated state is then streamed back to the client via Server-Sent Events (SSE) for real-time visibility.

## Why This Implementation is Comprehensive
This POC addresses all the core evaluation criteria outlined in the requirements document:
* Chat Interface: Features a fully functional UI with streaming text and real-time tool-call visibility.
* LLM Integration: Robustly powered by the Google GenAI SDK with structured tool schemas.
* Layout Reasoning: The agent understands semantic element roles (e.g., keeping a badge and its text together, moving headlines to the top) and modifies their properties systematically.
* JSON Transformation: Performs accurate, deterministic updates to the underlying data structure rather than string manipulation.
* Follow-up Instructions: Context and conversational history are maintained continuously via session IDs, allowing the user to refine the layout step-by-step.

## State Management: POC vs. Production (Redis)
Currently, session state (the working layout JSON and chat history) is stored in an in-memory Python dictionary. This was an intentional architectural choice for a rapid POC because it requires zero external dependencies, allowing reviewers to clone and run the application instantly.

However, to elevate this to a production-ready application, the in-memory dictionary must be replaced with a Redis cache. Implementing Redis would provide:
1. Process Scalability: In-memory state locks the application to a single server worker. Redis allows multiple Uvicorn/FastAPI worker processes to share and access the same session state simultaneously.
2. Persistence and Recovery: User sessions and layouts would survive application restarts or server crashes.
3. Memory Management: Redis allows for automatic Time-To-Live (TTL) expiration, ensuring abandoned layout sessions do not cause memory leaks over time.

## Setup Guide

### 1. Installation
Clone the repository and install the required dependencies:
```bash
pip install -r requirements.txt
```

### 2. Environment Variables
copy `.env.example` file in the root directory of the project and add your API key:
```env
GEMINI_API_KEY=your_api_key_here
```

### 3. Running the Server
Start the FastAPI server using Uvicorn. Ensure you are in the directory containing `main.py`:
```bash
uvicorn main:app --reload --port 8000
```

### 4. Access the Application
Open your web browser and navigate to `http://localhost:8000` to interact with the agent.