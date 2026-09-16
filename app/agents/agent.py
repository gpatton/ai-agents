import json

from dotenv import load_dotenv
from openai import OpenAI

from app.tools.calculator import calculator
from app.tools.datetime_tool import get_current_datetime

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
    },
    {
        "type": "function",
        "name": "get_current_datetime",
        "description": "Get the current date and time in a timezone.",
        "parameters": {
            "type": "object",
            "properties": {
                "timezone": {
                    "type": "string",
                    "description": (
                        "IANA timezone such as Europe/Dublin, "
                        "America/New_York or Asia/Tokyo."
                    ),
                }
            },
            "required": ["timezone"],
            "additionalProperties": False,
        },
        "strict": True,
    },
]

def run_agent(user_message: str) -> str:
    response = client.responses.create(
        model="gpt-5.4-mini",
        input=user_message,
        tools=tools,
    )

    while True:
        tool_calls = [
            item
            for item in response.output
            if item.type == "function_call"
        ]

        # No tool calls means the model has finished.
        if not tool_calls:
            return response.output_text

        tool_outputs = []

        for item in tool_calls:
            arguments = json.loads(item.arguments)

            print(
                f"Agent decided to call {item.name}: "
                f"{arguments}"
            )

            if item.name == "calculator":
                result = calculator(
                    a=arguments["a"],
                    b=arguments["b"],
                    operation=arguments["operation"],
                )

            elif item.name == "get_current_datetime":
                result = get_current_datetime(
                    timezone=arguments["timezone"]
                )

            else:
                result = f"Unknown tool: {item.name}"

            tool_outputs.append(
                {
                    "type": "function_call_output",
                    "call_id": item.call_id,
                    "output": str(result),
                }
            )

        response = client.responses.create(
            model="gpt-5.4-mini",
            previous_response_id=response.id,
            input=tool_outputs,
            tools=tools,
        ) 
