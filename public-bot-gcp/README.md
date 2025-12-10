# PropPanda WhatsApp Bot

A multi-tenant WhatsApp chatbot for real estate agents, built with FastAPI and LangGraph. The bot handles property searches, intelligent chat, and appointment scheduling through a stateful conversation flow.

## 🏗️ Project Structure

```
app/
├── api/                 # API endpoints and webhook handlers
├── core/                # Core application logic and state management
├── graphs/              # LangGraph workflow definitions
│   └── nodes/           # Individual node implementations
├── models/              # Database models
├── schemas/             # Pydantic models for request/response validation
├── services/            # External service integrations
├── tools/               # Custom tools and utilities
└── utils/               # Helper functions and utilities

tests/                   # Test files
scripts/                 # Utility scripts
```

## 🔄 Core Workflow

1. **Message Reception**
   - WhatsApp messages are received via webhook at `/api/v1/webhook`
   - Messages are processed asynchronously to handle high volume

2. **Conversation Routing**
   - Each message is processed by the `router_node` which classifies the intent
   - Supported intents:
     - `PROPERTY_SEARCH`: Handle property search queries
     - `SWITCH_SEARCH`: Change property type/category
     - `CLARIFICATION`: Handle ambiguous queries
     - `INTELLIGENT_CHAT`: General conversation and knowledge base queries

3. **Property Search Flow**
   - Extracts search parameters (budget, location, etc.)
   - Validates and enriches search criteria
   - Queries the property database
   - Formats and returns property listings
   - Handles pagination and follow-up questions

4. **Intelligent Chat**
   - Processes general inquiries using OpenAI's language model
   - Provides responses based on knowledge base
   - Maintains conversation context

## 🛠️ Key Components

### Router Node (`app/graphs/nodes/router.py`)
- Classifies incoming messages into specific intents
- Handles conversation state and context
- Routes to appropriate processing nodes

### Property Graph (`app/graphs/nodes/property_graph.py`)
- Manages property search workflow
- Handles search parameter extraction and validation
- Executes database queries
- Formats property listings

### Intelligent Chat (`app/graphs/nodes/intelligent_chat.py`)
- Handles general conversation
- Integrates with knowledge base
- Maintains chat history and context

## 🚀 Getting Started

### Prerequisites
- Python 3.9+
- PostgreSQL database
- Redis (for caching and session management)
- WhatsApp Business API access
- OpenAI API key

### Installation
1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set up environment variables (copy `.env.example` to `.env` and fill in values)
4. Run database migrations:
   ```bash
   alembic upgrade head
   ```
5. Start the application:
   ```bash
   uvicorn app.main:app --reload
   ```

## 📝 Environment Variables

```env
# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/proppanda

# OpenAI
OPENAI_API_KEY=your_openai_key

# WhatsApp
WHATSAPP_ACCESS_TOKEN=your_whatsapp_token
WHATSAPP_VERIFY_TOKEN=your_webhook_verify_token

# Redis
REDIS_URL=redis://localhost:6379/0

# Other
ENVIRONMENT=development
```

## 🧪 Testing

Run tests with pytest:
```bash
pytest tests/
```

## 📚 Documentation

- API documentation available at `/docs` when running locally
- Swagger UI at `/docs`
- ReDoc at `/redoc`

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.