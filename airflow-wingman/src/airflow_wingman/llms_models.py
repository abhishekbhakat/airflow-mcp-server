MODELS = {
        "anthropic": {
            "name": "Anthropic",
            "endpoint": "https://api.anthropic.com/v1/messages",
            "models": [
                {
                    "id": "claude-3.5-sonnet",
                    "name": "Claude 3.5 Sonnet",
                    "default": True,
                    "context_window": 200000,
                    "description": "Input $3/M tokens, Output $15/M tokens",
                },
                {
                    "id": "claude-3.5-haiku",
                    "name": "Claude 3.5 Haiku",
                    "default": False,
                    "context_window": 200000,
                    "description": "Input $0.80/M tokens, Output $4/M tokens",
                },
            ],
        },
        "openrouter": {
            "name": "OpenRouter",
            "endpoint": "https://openrouter.ai/api/v1/chat/completions",
            "models": [
                {
                    "id": "anthropic/claude-3.5-sonnet",
                    "name": "Claude 3.5 Sonnet",
                    "default": False,
                    "context_window": 200000,
                    "description": "Input $3/M tokens, Output $15/M tokens",
                },
                {
                    "id": "anthropic/claude-3.5-haiku",
                    "name": "Claude 3.5 Haiku",
                    "default": False,
                    "context_window": 200000,
                    "description": "Input $0.80/M tokens, Output $4/M tokens",
                },
            ],
        },
    }