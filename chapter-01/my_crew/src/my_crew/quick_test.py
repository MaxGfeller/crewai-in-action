from openai import OpenAI
import json

client = OpenAI(api_key="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")

tools = [{
    "type": "function",
    "name": "get_report",
    "description": "Get the financial report for a given year.",
    "parameters": {
        "type": "object",
        "properties": {
            "year": {"type": "number"},
        },
        "required": ["year"],
        "additionalProperties": False
    },
    "strict": True
}]

input_messages = [
	{
		"role": "user",
		"content": "How much revenue did we make in 2024?"
	}
]

response = client.responses.create(
    model="gpt-5",
    input=input_messages,
    tools=tools,
)

print([item.model_dump_json() for item in response.output])