INTERFACE_MESSAGES = {
    "model_recommendation": {"title": "Note", "content": "For best results with function/tool calling capabilities, we recommend using models like Claude-3.5 Sonnet or GPT-4."},
    "security_note": {
        "title": "Security",
        "content": "For your security, API keys are required for each session and are never stored. If you refresh the page or close the browser, you'll need to enter your API key again.",
    },
    "context_window": {
        "title": "Context Window",
        "content": "Each model has a maximum context window size that determines how much text it can process. "
        "For long conversations or large code snippets, consider using models with larger context windows like Claude-3 Opus (200K tokens) or GPT-4 Turbo (128K tokens). "
        "For better results try to keep the context size as low as possible. Try using new chats instead of reusing the same chat.",
    },
}
