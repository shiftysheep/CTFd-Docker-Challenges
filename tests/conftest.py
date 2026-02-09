"""Test configuration and shared fixtures.

CTFd stub injection happens at module scope (before test collection)
so that api/api.py can be imported in test_api_helpers.py.
"""
import sys
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# CTFd Stub Injection (module-scope, before any test imports)
# ---------------------------------------------------------------------------
from tests.stubs import ctfd_stubs

# Map every CTFd submodule that plugin code imports
_stub_modules = {
    "CTFd": MagicMock(),
    "CTFd.api": MagicMock(),
    "CTFd.models": ctfd_stubs,
    "CTFd.forms": ctfd_stubs,
    "CTFd.forms.fields": ctfd_stubs,
    "CTFd.plugins": MagicMock(),
    "CTFd.plugins.challenges": ctfd_stubs,
    "CTFd.plugins.flags": ctfd_stubs,
    "CTFd.utils": MagicMock(),
    "CTFd.utils.config": ctfd_stubs,
    "CTFd.utils.dates": ctfd_stubs,
    "CTFd.utils.decorators": ctfd_stubs,
    "CTFd.utils.uploads": ctfd_stubs,
    "CTFd.utils.user": ctfd_stubs,
}

for mod_name, mod in _stub_modules.items():
    sys.modules.setdefault(mod_name, mod)

# Add additional attributes needed by CTFd imports
_ctfd_api = sys.modules["CTFd.api"]
_ctfd_api.CTFd_API_v1 = MagicMock()

# Add Teams and Users models to CTFd.models
sys.modules["CTFd.models"].Teams = type("Teams", (), {})
sys.modules["CTFd.models"].Users = type("Users", (), {})

# Add CHALLENGE_CLASSES to CTFd.plugins.challenges
sys.modules["CTFd.plugins.challenges"].CHALLENGE_CLASSES = {}

# Add register_plugin_assets_directory to CTFd.plugins
sys.modules["CTFd.plugins"].register_plugin_assets_directory = MagicMock()

# Also need flask_restx for api.py -- stub it if not installed
if "flask_restx" not in sys.modules:
    _flask_restx = MagicMock()

    # Create a Namespace mock that returns an object with .route() decorator
    def _create_namespace_mock(*args, **kwargs):
        namespace = MagicMock()
        # Make .route() return a pass-through decorator
        namespace.route = MagicMock(side_effect=lambda *a, **kw: lambda f: f)
        return namespace

    _flask_restx.Namespace = _create_namespace_mock
    _flask_restx.Resource = type("Resource", (), {})
    sys.modules["flask_restx"] = _flask_restx

# Need wtforms for models.py
if "wtforms" not in sys.modules:
    _wtforms = MagicMock()
    sys.modules["wtforms"] = _wtforms

# Need sqlalchemy for __init__.py
if "sqlalchemy" not in sys.modules:
    _sqlalchemy = MagicMock()
    sys.modules["sqlalchemy"] = _sqlalchemy
if "sqlalchemy.exc" not in sys.modules:
    _sqlalchemy_exc = MagicMock()
    _sqlalchemy_exc.InternalError = type("InternalError", (Exception,), {})
    sys.modules["sqlalchemy.exc"] = _sqlalchemy_exc

# Need flask for __init__.py
if "flask" not in sys.modules:
    _flask = MagicMock()
    _flask.Blueprint = MagicMock
    _flask.render_template = MagicMock()
    _flask.request = MagicMock()
    sys.modules["flask"] = _flask


# ---------------------------------------------------------------------------
# Shared Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_docker_config():
    """Mock DockerConfig with standard HTTP settings."""
    config = MagicMock()
    config.hostname = "localhost:2375"
    config.tls_enabled = False
    config.ca_cert = None
    config.client_cert = None
    config.client_key = None
    config.repositories = None
    return config


@pytest.fixture
def mock_docker_config_tls():
    """Mock DockerConfig with TLS enabled."""
    config = MagicMock()
    config.hostname = "localhost:2376"
    config.tls_enabled = True
    config.ca_cert = "/path/to/ca.pem"
    config.client_cert = "/path/to/cert.pem"
    config.client_key = "/path/to/key.pem"
    config.repositories = None
    return config


@pytest.fixture
def sample_container_ports_json():
    """Sample Docker API /containers/json response with port mappings."""
    return [
        {
            "Id": "abc123",
            "Names": ["/test_container"],
            "Ports": [
                {"PrivatePort": 80, "PublicPort": 30001, "Type": "tcp"},
                {"PrivatePort": 443, "PublicPort": 30002, "Type": "tcp"},
            ],
        },
        {
            "Id": "def456",
            "Names": ["/another_container"],
            "Ports": [
                {"PrivatePort": 8080, "PublicPort": 30003, "Type": "tcp"},
            ],
        },
        {
            "Id": "ghi789",
            "Names": ["/no_ports_container"],
            "Ports": [],
        },
    ]


@pytest.fixture
def sample_service_ports_json():
    """Sample Docker API /services response with port mappings."""
    return [
        {
            "ID": "svc_abc",
            "Spec": {"Name": "test_service"},
            "Endpoint": {
                "Spec": {
                    "Ports": [
                        {"PublishedPort": 30010, "TargetPort": 80, "Protocol": "tcp"},
                        {"PublishedPort": 30011, "TargetPort": 443, "Protocol": "tcp"},
                    ]
                }
            },
        },
        {
            "ID": "svc_def",
            "Spec": {"Name": "another_service"},
            "Endpoint": {
                "Spec": {
                    "Ports": [
                        {"PublishedPort": 30012, "TargetPort": 8080, "Protocol": "tcp"},
                    ]
                }
            },
        },
        {
            "ID": "svc_no_endpoint",
            "Spec": {"Name": "no_endpoint_service"},
            "Endpoint": {},
        },
    ]
