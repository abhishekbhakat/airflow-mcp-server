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

    @expose("/")
    def chat(self):
        """
        Chat interface for Airflow Wingman.
        """
        return self.render_template(
            "wingman_chat.html",
            title="Airflow Wingman"
        )


# Create AppBuilder View
v_appbuilder_view = WingmanView()
v_appbuilder_package = {
    "name": "Airflow Wingman",
    "category": "AI",
    "view": v_appbuilder_view,
}


# Create Plugin
class WingmanPlugin(AirflowPlugin):
    name = "wingman"
    flask_blueprints = [bp]
    appbuilder_views = [v_appbuilder_package]
