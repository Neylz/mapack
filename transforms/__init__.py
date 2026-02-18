from .registry import registry


def load_builtin_transforms() -> None:
    # import side-effects for registration
    from . import conditional  # noqa: F401
    from . import copy  # noqa: F401
    from . import git_ops  # noqa: F401
    from . import log  # noqa: F401
    from . import mc_feature  # noqa: F401


__all__ = ["registry", "load_builtin_transforms"]
