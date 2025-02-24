from airflow.plugins_manager import AirflowPlugin
from flask_appbuilder import BaseView as AppBuilderBaseView, expose
from flask import Blueprint


bp = Blueprint(
    "wingman",
    __name__,
    template_folder="templates",
    static_folder="static",
    static_url_path="/static/wingman",
)


class WingmanView(AppBuilderBaseView):
    route_base = "/wingman"
    default_view = "chat"

    AVAILABLE_MODELS = {
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

    @expose("/")
    def chat(self):
        """
        Chat interface for Airflow Wingman.
        """
        return self.render_template(
            "wingman_chat.html", title="Airflow Wingman", models=self.AVAILABLE_MODELS
        )


# Create AppBuilder View
v_appbuilder_view = WingmanView()
v_appbuilder_package = {
    "name": "Wingman",
    "category": "AI",
    "view": v_appbuilder_view,
}


# Create Plugin
class WingmanPlugin(AirflowPlugin):
    name = "wingman"
    flask_blueprints = [bp]
    appbuilder_views = [v_appbuilder_package]
