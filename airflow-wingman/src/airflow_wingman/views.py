"""Views for Airflow Wingman plugin."""

from flask import Response, request, stream_with_context
from flask.json import jsonify
from flask_appbuilder import BaseView as AppBuilderBaseView, expose

from airflow_wingman.llm_client import LLMClient
from airflow_wingman.llms_models import MODELS
from airflow_wingman.notes import INTERFACE_MESSAGES
from airflow_wingman.prompt_engineering import prepare_messages


class WingmanView(AppBuilderBaseView):
    """View for Airflow Wingman plugin."""

    route_base = "/wingman"
    default_view = "chat"

    @expose("/")
    def chat(self):
        """Render chat interface."""
        providers = {provider: info["name"] for provider, info in MODELS.items()}
        return self.render_template("wingman_chat.html", title="Airflow Wingman", models=MODELS, providers=providers, interface_messages=INTERFACE_MESSAGES)

    @expose("/chat", methods=["POST"])
    def chat_completion(self):
        """Handle chat completion requests."""
        try:
            data = self._validate_chat_request(request.get_json())

            # Create a new client for this request
            client = LLMClient(data["api_key"])

            if data["stream"]:
                return self._handle_streaming_response(client, data)
            else:
                return self._handle_regular_response(client, data)

        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    def _validate_chat_request(self, data: dict) -> dict:
        """Validate chat request data."""
        if not data:
            raise ValueError("No data provided")

        required_fields = ["provider", "model", "messages", "api_key"]
        missing = [f for f in required_fields if not data.get(f)]
        if missing:
            raise ValueError(f"Missing required fields: {', '.join(missing)}")

        # Prepare messages with system instruction while maintaining history
        messages = data["messages"]
        messages = prepare_messages(messages)

        return {
            "provider": data["provider"],
            "model": data["model"],
            "messages": messages,
            "api_key": data["api_key"],
            "stream": data.get("stream", False),
            "temperature": data.get("temperature", 0.7),
            "max_tokens": data.get("max_tokens"),
        }

    def _handle_streaming_response(self, client: LLMClient, data: dict) -> Response:
        """Handle streaming response."""

        def generate():
            for chunk in client.chat_completion(messages=data["messages"], model=data["model"], provider=data["provider"], temperature=data["temperature"], max_tokens=data["max_tokens"], stream=True):
                yield f"data: {chunk}\n\n"

        response = Response(stream_with_context(generate()), mimetype="text/event-stream")
        response.headers["Content-Type"] = "text/event-stream"
        response.headers["Cache-Control"] = "no-cache"
        response.headers["Connection"] = "keep-alive"
        return response

    def _handle_regular_response(self, client: LLMClient, data: dict) -> Response:
        """Handle regular response."""
        response = client.chat_completion(messages=data["messages"], model=data["model"], provider=data["provider"], temperature=data["temperature"], max_tokens=data["max_tokens"], stream=False)
        return jsonify(response)
