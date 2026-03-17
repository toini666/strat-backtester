__all__ = ["simulate"]


def __getattr__(name):
    if name == "simulate":
        from .simulator import simulate

        return simulate
    raise AttributeError(name)
