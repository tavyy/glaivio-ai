from langchain_core.tools import tool as _langchain_tool


def skill(fn=None, *, name=None, description=None):
    """
    Decorator that turns a plain Python function into a Glaivio skill.

    Usage:
        @skill
        def book_appointment(name: str, date: str) -> str:
            \"\"\"Book an appointment.\"\"\"
            ...

        @skill(name="book", description="Book a slot")
        def book_appointment(name: str, date: str) -> str:
            ...
    """
    def decorator(f):
        kwargs = {}
        if name:
            kwargs["name"] = name
        if description:
            kwargs["description"] = description
        return _langchain_tool(f, **kwargs) if not kwargs else _langchain_tool(**kwargs)(f)

    if fn is not None:
        # called as @skill without arguments
        return decorator(fn)

    # called as @skill(...) with arguments
    return decorator
