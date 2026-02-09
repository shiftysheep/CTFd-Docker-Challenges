"""Minimal CTFd stubs for testing api.py and model imports."""
from unittest.mock import MagicMock


# --- Flask-SQLAlchemy db stub ---
class _Query:
    """Stub query object that supports chaining."""
    def filter_by(self, **kwargs):
        return self
    def filter(self, *args):
        return self
    def first(self):
        return None
    def first_or_404(self):
        return None
    def all(self):
        return []
    def delete(self):
        pass
    def yield_per(self, n):
        return iter([])


class _ModelMeta(type):
    """Metaclass that adds a query attribute to model classes."""
    def __new__(mcs, name, bases, namespace):
        cls = super().__new__(mcs, name, bases, namespace)
        cls.query = _Query()
        return cls


class _Column:
    """Stub for db.Column."""
    def __init__(self, *args, **kwargs):
        pass
    def __le__(self, other):
        return True
    def __ge__(self, other):
        return True


class _DB:
    """Stub for Flask-SQLAlchemy db object."""
    Model = _ModelMeta("Model", (), {})
    Column = _Column
    Integer = "Integer"
    String = lambda self=None, *a, **kw: "String"
    Boolean = "Boolean"
    Text = "Text"
    ForeignKey = lambda self=None, *a, **kw: None
    session = MagicMock()


db = _DB()


# --- CTFd Models ---
class Challenges(metaclass=_ModelMeta):
    """Stub for CTFd.models.Challenges base class."""
    id = None
    name = None
    type = None


class Teams(metaclass=_ModelMeta):
    """Stub for CTFd.models.Teams."""
    id = None
    name = None


class Users(metaclass=_ModelMeta):
    """Stub for CTFd.models.Users."""
    id = None
    name = None


class ChallengeFiles:
    query = _Query()


class Fails:
    query = _Query()


class Flags:
    query = _Query()


class Hints:
    query = _Query()


class Solves:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class Tags:
    query = _Query()


# --- CTFd API ---
CTFd_API_v1 = MagicMock()


# --- CTFd Plugins ---
CHALLENGE_CLASSES = {}


def register_plugin_assets_directory(*args, **kwargs):
    """Stub for CTFd.plugins.register_plugin_assets_directory."""
    pass


# --- CTFd Plugins ---
class BaseChallenge:
    """Stub for CTFd.plugins.challenges.BaseChallenge."""
    pass


class ChallengeResponse:
    """Stub for CTFd.plugins.challenges.ChallengeResponse."""
    def __init__(self, status="", message=""):
        self.status = status
        self.message = message


def get_flag_class(flag_type):
    return MagicMock()


# --- CTFd Forms ---
class BaseForm:
    """Stub for CTFd.forms.BaseForm."""
    pass


class SubmitField:
    def __init__(self, *args, **kwargs):
        pass


# --- CTFd Utils ---
def admins_only(f):
    """Identity decorator stub."""
    return f


def authed_only(f):
    """Identity decorator stub."""
    return f


def is_teams_mode():
    return False


def unix_time(dt):
    return 0


def get_current_team():
    return MagicMock()


def get_current_user():
    return MagicMock()


def get_ip(req=None, *args, **kwargs):
    return "127.0.0.1"


def delete_file(file_id):
    pass
