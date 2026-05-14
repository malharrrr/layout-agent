import json
import copy
from tools import TOOLS, execute_tool
from system_prompt import SYSTEM_PROMPT
from google import genai
from google.genai import types

client = genai.Client()

def _to_gemini_tools():
    declarations = []
    for t in TOOLS:
        declarations.append(types.FunctionDeclaration(
            name=t["name"],
            description=t["description"],
            parameters=t["input_schema"]
        ))
    return [types.Tool(function_declarations=declarations)]

GEMINI_TOOLS = _to_gemini_tools()

def run_agent(user_message: str, layout: dict, history: list):
    working_layout = copy.deepcopy(layout)
    contents = []

    for msg in history:
        role = "user" if msg["role"] == "user" else "model"
        contents.append(types.Content(role=role, parts=[types.Part(text=msg["content"])]))

    contents.append(types.Content(
        role="user",
        parts=[types.Part(text=f"{user_message}\n\n<current_layout>\n{json.dumps(working_layout, indent=2)}\n</current_layout>")]
    ))

    tool_calls_made = []
    final_text = ""

    while True:
        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                tools=GEMINI_TOOLS,
            )
        )

        candidate = response.candidates[0]
        parts = candidate.content.parts
        contents.append(types.Content(role="model", parts=parts))

        fn_calls = [p for p in parts if p.function_call is not None]

        if fn_calls:
            tool_response_parts = []
            for part in fn_calls:
                fc = part.function_call
                tool_input = dict(fc.args)
                result = execute_tool(fc.name, tool_input, working_layout)
                
                tool_calls_made.append({
                    "tool": fc.name,
                    "input": tool_input,
                    "result": result
                })
                
                yield {
                    "type": "tool_call",
                    "tool": fc.name,
                    "input": tool_input,
                    "result": result
                }
                
                tool_response_parts.append(types.Part(
                    function_response=types.FunctionResponse(
                        name=fc.name,
                        response={"result": result}
                    )
                ))

            contents.append(types.Content(role="user", parts=tool_response_parts))

        else:
            for part in parts:
                if part.text:
                    final_text = part.text
                    break

            new_history = list(history)
            new_history.append({"role": "user", "content": user_message})
            new_history.append({"role": "assistant", "content": final_text})

            yield {
                "type": "done",
                "text": final_text,
                "layout": working_layout,
                "tool_calls": tool_calls_made,
                "history": new_history
            }
            break