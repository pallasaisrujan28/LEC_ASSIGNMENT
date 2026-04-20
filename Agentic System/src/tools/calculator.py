"""Calculator tool — sympy (no API key required)."""

from langchain_core.tools import tool


@tool
def calculator(expression: str) -> str:
    """Evaluate a mathematical expression and return the result.

    Supports arithmetic, algebra, trig, logarithms, etc.
    Examples: "2 + 3 * 4", "sqrt(144)", "sin(pi/2)", "log(100, 10)", "15% of 8000000"
    """
    import sympy

    expression = expression.replace("%", "/100*").replace(" of ", " * ")

    try:
        result = sympy.sympify(expression, evaluate=True)
        return str(float(result))
    except (sympy.SympifyError, TypeError, ValueError) as e:
        return f"Error: Could not evaluate '{expression}' — {e}"
