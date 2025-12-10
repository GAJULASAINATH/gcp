```
├── LICENSE
├── Makefile
├── README.md
├── __init__.py
├── alembic
│   ├── env.py
│   ├── script.py.mako
│   └── versions
├── alembic.ini
├── app
│   ├── __init__.py
│   ├── api
│   │   ├── __init__.py
│   │   ├── endpoints
│   │   │   └── whatsapp.py
│   │   ├── middleware
│   │   │   ├── __init__.py
│   │   │   ├── auth.py
│   │   │   ├── logging.py
│   │   │   └── rate_limit.py
│   │   └── v1
│   │       ├── __init__.py
│   │       ├── health.py
│   │       └── webhooks.py
│   ├── config.py
│   ├── core
│   │   ├── __init__.py
│   │   ├── agent_resolver.py
│   │   ├── intent_classifier.py
│   │   ├── memory_manager.py
│   │   ├── persistence.py
│   │   ├── response_formatter.py
│   │   ├── session_manager.py
│   │   └── state.py
│   ├── db
│   │   ├── __init__.py
│   │   ├── base_class.py
│   │   ├── models.py
│   │   ├── repositories
│   │   │   ├── __init__.py
│   │   │   ├── agent_repository.py
│   │   │   ├── appointment_repository.py
│   │   │   ├── conversation_repository.py
│   │   │   ├── property_repository.py
│   │   │   └── prospect_repository.py
│   │   └── session.py
│   ├── dependencies.py
│   ├── graphs
│   │   ├── __init__.py
│   │   ├── master_graph.py
│   │   └── nodes
│   │       ├── __init__.py
│   │       ├── appointment_manager.py
│   │       ├── capability_check.py
│   │       ├── clear_memory.py
│   │       ├── decision.py
│   │       ├── display_results.py
│   │       ├── extractor.py
│   │       ├── generator.py
│   │       ├── human_handoff.py
│   │       ├── intelligent_chat.py
│   │       ├── property_graph.py
│   │       ├── router.py
│   │       └── search_tool.py
│   ├── main.py
│   ├── schemas
│   │   ├── __init__.py
│   │   ├── agent.py
│   │   ├── appointment.py
│   │   ├── conversation.py
│   │   ├── eunms.py
│   │   ├── property_search.py
│   │   ├── session.py
│   │   └── webhook.py
│   ├── services
│   │   ├── __init__.py
│   │   ├── calendar_service.py
│   │   ├── conversation_service.py
│   │   ├── n8n_client.py
│   │   ├── openai_service.py
│   │   ├── query_builder.py
│   │   ├── redis_service.py
│   │   ├── vector_store_service.py
│   │   ├── whatsapp_client.py
│   │   └── whatsapp_service.py
│   ├── tools
│   │   ├── __init__.py
│   │   ├── knowledge_base.py
│   │   └── property_search.py
│   └── utils
│       ├── __init__.py
│       ├── cache.py
│       ├── formatters.py
│       ├── logger.py
│       ├── retry.py
│       └── validators.py
├── docker
│   ├── Dockerfile
│   ├── docker-compose.prod.yml
│   └── docker-compose.yml
├── pyproject.toml
├── requirements.txt
├── structure.md
├── test2.py
└── tests
    ├── __init__.py
    ├── conftest.py
    ├── integration
    │   ├── test_database.py
    │   └── test_webhook_flow.py
    └── unit
        ├── agents
        │   ├── test_appointment.py
        │   └── test_property_search.py
        ├── test_router_agent.py
        └── test_session_manager.py
```