from langchain.tools import tool


def calculate(a: float, b: float, operation: str) -> float:
    """Perform a basic mathematical operation."""

    if operation == "add":
        return a + b

    if operation == "subtract":
        return a - b

    if operation == "multiply":
        return a * b

    if operation == "divide":
        if b == 0:
            raise ValueError("Cannot divide by zero.")
        return a / b

    raise ValueError(f"Unknown operation: {operation}")


@tool
def calculator(a: float, b: float, operation: str) -> float:
    """Perform a basic mathematical operation."""

    return calculate(a, b, operation)
