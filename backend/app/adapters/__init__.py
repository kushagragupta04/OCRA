from typing import Optional
from app.adapters.jira_base import JiraAdapter
from app.adapters.jira_mock_sandbox import JiraMockSandboxAdapter
from app.adapters.jira_cloud import JiraCloudAdapter
from app.adapters.jira_adf import JiraADFBuilder
from app.config import settings

# Global singleton instance for the sandbox so state is preserved across endpoints in demo/dev mode
_sandbox_instance = JiraMockSandboxAdapter()


def get_jira_adapter(force_mock: Optional[bool] = None) -> JiraAdapter:
    use_mock = settings.USE_MOCK_JIRA if force_mock is None else force_mock
    if use_mock:
        return _sandbox_instance
    return JiraCloudAdapter()


def get_sandbox_adapter() -> JiraMockSandboxAdapter:
    return _sandbox_instance


__all__ = [
    "JiraAdapter",
    "JiraMockSandboxAdapter",
    "JiraCloudAdapter",
    "JiraADFBuilder",
    "get_jira_adapter",
    "get_sandbox_adapter",
]
