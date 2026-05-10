"""
Azure LLM Reasoner
-------------------
Uses Azure OpenAI to reason about build failures and suggest fixes.
Now language-agnostic: supports Node.js, Python, Go, Java, and more.
"""

import os
import json
import re
from dotenv import load_dotenv
from azure.identity import ClientSecretCredential
from openai import AzureOpenAI

load_dotenv()


class AzureReasoner:
    def __init__(self):
        # ---------- Azure AD Credentials ----------
        tenant_id = os.getenv("AZURE_TENANT_ID")
        client_id = os.getenv("AZURE_CLIENT_ID")
        client_secret = os.getenv("AZURE_CLIENT_SECRET")

        # ---------- Token ----------
        credential = ClientSecretCredential(
            tenant_id=tenant_id,
            client_id=client_id,
            client_secret=client_secret
        )

        token = credential.get_token(
            "https://cognitiveservices.azure.com/.default"
        )

        # ---------- Azure OpenAI Client ----------
        self.client = AzureOpenAI(
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
            azure_ad_token=token.token
        )

        self.deployment = os.getenv("AZURE_OPENAI_CHATGPT_DEPLOYMENT")

    # --------------------------------------------------
    # JSON Extraction
    # --------------------------------------------------
    def extract_json(self, text: str) -> dict:
        try:
            text = text.strip()

            # Remove markdown code fences
            text = re.sub(r"^```json", "", text)
            text = re.sub(r"^```", "", text)
            text = re.sub(r"```$", "", text)

            # Extract JSON block
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if not match:
                raise ValueError("No JSON found")

            return json.loads(match.group(0))

        except Exception:
            return {
                "error": "Invalid JSON from LLM",
                "raw_output": text
            }

    # --------------------------------------------------
    # Language-specific fix rules
    # --------------------------------------------------
    def _get_fix_rules(self, project_type: str) -> str:
        rules = {
            "nodejs": """
- If error_type is "missing_dependency", suggest: npm install <package>
- If error_type is "script_missing", suggest adding the script in package.json
- If error_type is "node_version_mismatch", suggest using a compatible Node version
- Prefer npm over yarn unless yarn.lock exists
""",
            "python": """
- If error_type is "missing_dependency", suggest: pip install <package>
- If error_type is "pip_install_error", check PyPI for correct package name
- If error_type is "python_version_error", suggest updating the Python version
- Prefer pip over conda unless environment.yml exists
""",
            "go": """
- If error_type is "missing_dependency", suggest: go get <package>
- If error_type is "go_build_error", analyze the specific compilation error
- Suggest go mod tidy if dependency graph is inconsistent
""",
            "java_maven": """
- If error_type is "missing_dependency", suggest adding the dependency to pom.xml
- If error_type is "compilation_error", analyze the Java compilation error
- Suggest mvn clean install for stale build issues
""",
            "java_gradle": """
- If error_type is "missing_dependency", suggest adding the dependency to build.gradle
- If error_type is "compilation_error", analyze the Java compilation error
- Suggest gradle clean build for stale build issues
""",
        }

        return rules.get(project_type, """
- Analyze the error and suggest the most appropriate fix
- Prefer minimal, safe, and deterministic fixes
""")

    # --------------------------------------------------
    # Prompt Builder
    # --------------------------------------------------
    def _format_past_fixes(self, past_fixes: list[dict]) -> str:
        """Format retrieved past fixes into a prompt-friendly block."""
        if not past_fixes:
            return ""

        lines = ["\n--- Similar Past Fixes (from RAG memory) ---"]
        for i, fix in enumerate(past_fixes, 1):
            lines.append(
                f"\nPast Fix #{i}:\n"
                f"  Error Type: {fix.get('error_type', 'N/A')}\n"
                f"  Error Message: {fix.get('error_message', 'N/A')}\n"
                f"  Project Type: {fix.get('project_type', 'N/A')}\n"
                f"  Action: {fix.get('fix_action', 'N/A')}\n"
                f"  Command: {fix.get('fix_command', 'N/A')}\n"
                f"  Explanation: {fix.get('fix_explanation', 'N/A')}\n"
                f"  Outcome: {fix.get('outcome', 'N/A')}"
            )
        lines.append("--- End Past Fixes ---\n")
        return "\n".join(lines)

    def build_prompt(self, analysis: dict, project_type: str = "nodejs",
                     past_fixes: list[dict] | None = None) -> list:
        fix_rules = self._get_fix_rules(project_type)
        rag_context = self._format_past_fixes(past_fixes or [])

        system_msg = (
            "You are a senior build engineer with expertise across multiple languages and build systems.\n"
            "Diagnose build failures precisely.\n"
            "Do NOT guess randomly.\n"
            "Prefer deterministic fixes.\n"
            "If similar past fixes are provided, use them as strong evidence for your recommendation.\n"
            "Always respond in STRICT JSON only.\n"
        )

        return [
            {"role": "system", "content": system_msg},
            {
                "role": "user",
                "content": f"""
Analyze this build failure:

Project Type: {project_type}
Error Type: {analysis.get("error_type")}
Message: {analysis.get("message")}

Relevant Logs:
{analysis.get("raw_snippet")}
{rag_context}
Fix Rules for {project_type}:
{fix_rules}

General Rules:
- Prefer minimal and safe fixes
- The "action" field should be one of: "install_dependency", "run_command", "edit_file"
- The "command" field should contain the exact shell command to run
- If action is "edit_file", include "file_path" and "file_content" fields in best_fix
- Assess risk level honestly

Return JSON in this exact format:

{{
  "hypotheses": [
    {{"cause": "...", "probability": 0.0}}
  ],
  "best_fix": {{
    "action": "install_dependency|run_command|edit_file",
    "target": "...",
    "command": "...",
    "explanation": "A clear explanation of what this fix does and why"
  }},
  "confidence": 0.0,
  "risk": "low|medium|high"
}}
"""
            },
        ]

    # --------------------------------------------------
    # Reasoning Function
    # --------------------------------------------------
    def reason(self, analysis: dict, project_type: str = "nodejs",
               past_fixes: list[dict] | None = None) -> dict:
        messages = self.build_prompt(analysis, project_type, past_fixes=past_fixes)

        try:
            response = self.client.chat.completions.create(
                model=self.deployment,
                messages=messages,
                temperature=0.2  # low randomness = stable output
            )

            content = response.choices[0].message.content

            return self.extract_json(content)

        except Exception as e:
            return {
                "error": "LLM call failed",
                "details": str(e)
            }

    def embed(self, text: str):
        response = self.client.embeddings.create(
            model=os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT"),
            input=text
        )
        return response.data[0].embedding