import os
import json
import re
from dotenv import load_dotenv
from groq import Groq

tools = [
    "install_package",
    "remove_package", 
    "search_package",
    "diagnostic",
    "service_control",    # start/stop/restart services (nginx, ssh, etc.)
    "system_info",        # cpu, ram, disk, uptime
    "process_manage",     # kill, list processes
    "log_inspect",        # check logs for errors
    "network_diagnose",   # ping, dns, interface issues
    "file_permission",    # chmod, chown issues
    "none"
]

def extract_json(text):
    """Extract JSON block from model output safely"""
    match = re.search(r"{.*}", text, re.DOTALL)
    if not match:
        raise ValueError("No JSON found in response")
    return match.group(0)

def resultFormatting(output):
        """Parse JSON safely"""
        cleaned = extract_json(output)
        return json.loads(cleaned)

def main():
    load_dotenv()
  
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("No API key found")
        return

    client = Groq(api_key=api_key)

    def groq_agent(user_prompt):
        system_prompt = f"""
                            You are a Linux system management agent. Analyze the user's request and return ONLY a JSON object.

                            AVAILABLE ACTIONS:
                            {json.dumps(tools, indent=2)}

                            OUTPUT RULES:
                            - Output ONLY raw JSON, no markdown, no explanation
                            - Always include "action" field
                            - Include only fields relevant to the action
                            - If unsure or request is unrelated, use "none"

                            JSON SCHEMA BY ACTION:

                            install_package / remove_package / search_package:
                            {{"action": "install_package", "package": "brave-browser"}}

                            service_control:
                            {{"action": "service_control", "service": "nginx", "operation": "restart"}}

                            diagnostic / network_diagnose / system_info / log_inspect:
                            {{"action": "network_diagnose", "target": "internet"}}

                            process_manage:
                            {{"action": "process_manage", "operation": "kill", "process": "firefox"}}

                            file_permission:
                            {{"action": "file_permission", "path": "/etc/hosts", "operation": "inspect"}}

                            none:
                            {{"action": "none", "reason": "request not related to system management"}}

                            EXAMPLES:
                            User: "why is my internet not working" → {{"action": "network_diagnose", "target": "internet"}}
                            User: "install brave browser"          → {{"action": "install_package", "package": "brave-browser"}}
                            User: "nginx wont start"               → {{"action": "service_control", "service": "nginx", "operation": "status"}}
                            User: "my disk is full"                → {{"action": "system_info", "target": "disk"}}
                            User: "kill chrome"                    → {{"action": "process_manage", "operation": "kill", "process": "chrome"}}
                            """
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )

        raw_output = response.choices[0].message.content
        print("RAW OUTPUT:", raw_output)

        try:
            parsed = resultFormatting(raw_output)
            print("PARSED:", parsed)
        except Exception as e:
            print("Parsing failed:", e)

    user_input = input("What you want to ask: ")
    groq_agent(user_input)

if __name__ == '__main__':
    main()
