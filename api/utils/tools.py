from typing import Dict, Any, List, Union, Tuple
import json
import re
from openai import OpenAI

class ToolCalls:
    @staticmethod
    def create_model_instruction(messages: List[Dict[str, str]], tools: List[Dict[str, Any]], strict: bool = False) -> List[Dict[str, str]]:
        """Creates a system message instructing the model to generate fake tool calls in JSON, including full tool details."""

        tool_descriptions = []
        for tool in tools:
            if tool['type'] == 'function':
                function_data = tool.get('function')
                if not function_data:
                    continue
                
                tool_description = f"- {function_data['name']}: {function_data['description']}\n"
                if function_data.get('parameters'):
                    params_json = json.dumps(function_data['parameters'], indent=2)
                    tool_description += f"  Parameters:\n{params_json}\n"


                tool_descriptions.append(tool_description)

        formatted_tool_descriptions = "\n".join(tool_descriptions)


        content = f"""You have access to the following tools:
    {formatted_tool_descriptions}

    The 'strict' mode is {"enabled" if strict else "disabled"}. 

    When generating tool calls, follow these instructions:
    - If the user's request requires using a tool, respond with a JSON object describing the tool call.
    - Enclose the JSON object within markdown code blocks with the language set to "json".
    - Ensure the JSON is valid and does not contain trailing commas.
    - Use double quotes for keys and string values.
    - Include all parameters required by the tool.
    - Do not use tools if they're not strictly required.

    Example:
    ```json
    {{
    "tool_calls": [
        {{
        "name": "tool_name",
        "arguments": {{ "arg1": "value1", "arg2": "value2" }}
        }}
    ]
    }}
    If the user's request can be answered without using tools, respond normally with your answer. Remember, you must answer to one of the tools (unless theres nothing to be used in the tools). If you dont have access to information, such as weather, just take a guess. You must answer to the tools.
    """

        return messages + [{"role": "system", "content": content}]


    @staticmethod
    def convert_model_response(model_response_content: str) -> Tuple[bool, Union[List[Dict[str, Any]], str]]:
        """
        Converts a model's response containing a fake tool call.
        Returns a tuple: (tool_call_extracted: bool, tool_calls or content: List[Dict] | str).
        """
        tool_calls = ToolCalls.extract_tool_calls_from_text(model_response_content)
        if tool_calls:
            return True, tool_calls
        else:
            return False, model_response_content


    @staticmethod
    def extract_tool_calls_from_text(text: str) -> List[Dict[str, Any]]:
        """Extracts tool call information from text content with enhanced JSON parsing."""
        tool_calls = []
        json_matches = re.finditer(r"```(?:json)?\s*({.*?})\s*```", text, re.DOTALL | re.IGNORECASE)
        for match in json_matches:
            json_str = match.group(1)
            json_str = ToolCalls.fix_broken_json(json_str)
            try:
                tool_call_data = json.loads(json_str)
                if isinstance(tool_call_data, dict) and "tool_calls" in tool_call_data and isinstance(tool_call_data["tool_calls"], list):
                    for tc_data in tool_call_data["tool_calls"]:
                        if isinstance(tc_data, dict) and "name" in tc_data and "arguments" in tc_data:
                            tool_calls.append({
                                "type": "function",
                                "function": {
                                    "name": tc_data["name"],
                                    "arguments": json.dumps(tc_data["arguments"])
                                }
                            })
            except json.JSONDecodeError:
                pass
        return tool_calls

    @staticmethod
    def fix_broken_json(json_string: str) -> str:
        """Attempts to fix common JSON errors."""
        json_string = re.sub(r',\s*}', '}', json_string)
        json_string = re.sub(r',\s*]', ']', json_string)
        return json_string

    @staticmethod
    def extract_json_safely(text: str) -> Union[Dict[str, Any], None]:
        """Helper function to safely extract JSON from a string with more methods."""
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        match = re.search(r"```(?:json)?\s*({.*?})\s*```", text, re.DOTALL | re.IGNORECASE)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        return None