from mcp.server import MCPServer


mcp = MCPServer("AgentForge")


@mcp.tool()
def employee_directory(name: str) -> str:
    """Look up an employee in the AgentForge employee directory."""

    employees = {
        "alice": {
            "name": "Alice Murphy",
            "department": "Engineering",
            "role": "AI Engineer",
        },
        "bob": {
            "name": "Bob Kelly",
            "department": "Finance",
            "role": "Financial Analyst",
        },
        "carol": {
            "name": "Carol Byrne",
            "department": "Human Resources",
            "role": "HR Manager",
        },
    }

    employee = employees.get(name.lower())

    if employee is None:
        return f"No employee found with the name {name}."

    return (
        f"Name: {employee['name']}\n"
        f"Department: {employee['department']}\n"
        f"Role: {employee['role']}"
    )


if __name__ == "__main__":
    mcp.run()
