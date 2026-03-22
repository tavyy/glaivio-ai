from typing import Type, TypeVar
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


def extract(schema: Type[T], from_message: str, model: str = "claude-haiku-4-5-20251001") -> T:
    """
    Extract structured data from a natural language message.
    Returns a validated Pydantic model — no prompt writing required.

    Usage:
        from pydantic import BaseModel
        from glaivio import extract

        class BookingRequest(BaseModel):
            name: str
            date: str   # YYYY-MM-DD
            time: str   # HH:MM

        booking = extract(BookingRequest, from_message="I need Tuesday 10am, I'm John Smith")
        # → BookingRequest(name="John Smith", date="2026-03-25", time="10:00")
    """
    from langchain_anthropic import ChatAnthropic

    llm = ChatAnthropic(model=model, max_tokens=512)
    structured_llm = llm.with_structured_output(schema)

    fields = "\n".join(
        f"- {name}: {field.description or field.annotation}"
        for name, field in schema.model_fields.items()
    )

    prompt = f"""Extract the following fields from the message below.
Fields:
{fields}

Message: {from_message}"""

    return structured_llm.invoke(prompt)
