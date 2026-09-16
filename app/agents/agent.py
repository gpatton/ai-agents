import json

from dotenv import load_dotenv
from openai import OpenAI

from app.tools.calculator import calculator


load_dotenv()

client = OpenAI()

tools = [
    {
        "type": "function",
        "name": "calculator",
        "description": "Perform basic arithmetic calculations.",
        "parameters": {
            "type": "object",
            "properties": {
                "a": {
                    "type": "number",
                    "description": "The first number.",
                },
                "b": {
                    "type": "number",
                    "description": "The second number.",
                },
                "operation": {
                    "type": "string",
                    "enum": [
                        "add",
                        "subtract",
                        "multiply",
                        "divide",
                    ],
                },
            },
            "required": ["a", "b", "operation"],
            "additionalProperties": False,
        },
        "strict": True,
    }
]


def run_agent(user_message: str) -> str:

    response = client.responses.create(
        model="gpt-5.4-mini",
        input=user_message,
        tools=tools,
    )

    # Look through the model's output for tool calls.
    for item in response.output:

        if item.type == "function_call" and item.name == "calculator":

            arguments = json.loads(item.arguments)

            print(f"Agent decided to call calculator: {arguments}")

            result = calculator(
                a=arguments["a"],
                b=arguments["b"],
                operation=arguments["operation"],
            )

            # Give the tool result back to the model.
            response = client.responses.create(
                model="gpt-5.4-mini",
                previous_response_id=response.id,
                input=[
                    {
                        "type": "function_call_output",
                        "call_id": item.call_id,
                        "output": str(result),
                    }
                ],
                tools=tools,
            )

            return response.output_text

    return response.output_text
