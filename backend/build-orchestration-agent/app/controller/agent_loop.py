"""
Build Agent Loop
-----------------
Core ReAct loop with Human-in-the-Loop (HITL) approval.
Emits conversational messages so the frontend reads like a chat with an LLM.
"""

import subprocess
import os
from app.utils.log_streamer import publish_log, publish_approval_request, publish_status
from app.services.hitl_manager import request_approval


class BuildAgent:
    def __init__(self, executor, analyzer, reasoner, project_type: str = "nodejs",
                 retriever=None):
        self.executor = executor
        self.analyzer = analyzer
        self.reasoner = reasoner
        self.retriever = retriever
        self.project_type = project_type
        self.max_iterations = 5
        self.task_id = "unknown"

    # -----------------------------------------
    # Logging helpers
    # -----------------------------------------
    def log(self, message: str, step: str = "info"):
        print(message)
        publish_log(self.task_id, message, step)

    # -----------------------------------------
    # Main loop
    # -----------------------------------------
    def run(self, project_path: str):
        history = []

        self.log(
            f"Hi! I'm your Build Agent. Let me run the build for your **{self.project_type}** project and see what happens.",
            step="info",
        )
        publish_status(self.task_id, "running", "Starting build pipeline...")

        for iteration in range(1, self.max_iterations + 1):
            attempt_label = f"(attempt {iteration} of {self.max_iterations})" if iteration > 1 else ""

            if iteration == 1:
                self.log("Running the build now...", step="build")
            else:
                self.log(f"Let me try building again {attempt_label}...", step="build")

            publish_status(self.task_id, "building", f"Running build {attempt_label}...")

            # ── Execute Build ──────────────────────
            result = self.executor.run_build(project_path)

            if result["success"]:
                if iteration == 1:
                    self.log(
                        "Great news — the build **passed** on the first try! Everything looks good.",
                        step="success",
                    )
                else:
                    self.log(
                        f"The build **passed** after {iteration} attempts. The fix worked!",
                        step="success",
                    )
                publish_status(self.task_id, "success", "Build completed successfully!")

                return {
                    "status": "SUCCESS",
                    "history": history,
                    "final_result": result,
                }

            # ── Analyze ────────────────────────────
            if iteration == 1:
                self.log(
                    "The build **failed**. Let me analyze the error logs to understand what went wrong...",
                    step="error",
                )
            else:
                self.log(
                    "Unfortunately the build still fails. Let me look at the new error...",
                    step="error",
                )
            publish_status(self.task_id, "analyzing", "Analyzing build error logs...")

            analysis = self.analyzer.analyze(result["logs"], self.project_type)

            error_type = analysis["error_type"]
            error_msg = analysis["message"]
            target = analysis.get("target", "")

            target_info = f" in `{target}`" if target else ""
            self.log(
                f"I identified the issue — it's a **{error_type}** error{target_info}:\n\n> {error_msg}",
                step="analysis",
            )

            # ── RAG: Retrieve ──────────────────────
            self.log("Let me think about how to fix this...", step="reasoning")
            publish_status(self.task_id, "reasoning", "Reasoning about the fix...")

            past_fixes = []
            if self.retriever and self.retriever.has_data:
                error_text = f"{error_type}: {error_msg}"
                past_fixes = self.retriever.retrieve(error_text, k=3)
                if past_fixes:
                    self.log(
                        f"I found **{len(past_fixes)} similar issues** I've fixed before. "
                        "I'll use that experience to suggest a better fix.",
                        step="rag",
                    )

            # ── Reason ─────────────────────────────
            reasoning = self.reasoner.reason(analysis, self.project_type, past_fixes=past_fixes)

            if reasoning.get("error"):
                self.log(
                    f"I ran into a problem while reasoning about the fix: {reasoning['error']}. "
                    "Let me try again...",
                    step="error",
                )
                history.append({
                    "iteration": iteration,
                    "analysis": analysis,
                    "reasoning": reasoning,
                    "applied": False,
                    "hitl_decision": None,
                    "result": result,
                })
                continue

            best_fix = reasoning.get("best_fix", {})
            confidence = reasoning.get("confidence", 0)
            risk = reasoning.get("risk", "unknown")
            explanation = best_fix.get("explanation", "")
            command = best_fix.get("command", "")
            action = best_fix.get("action", "")

            # Build a conversational explanation
            conf_pct = int(confidence * 100) if isinstance(confidence, (int, float)) else confidence

            self.log(
                f"Here's what I think is happening and how to fix it:\n\n"
                f"**Diagnosis:** {explanation}\n\n"
                f"**Proposed fix:** `{command}`\n\n"
                f"I'm **{conf_pct}% confident** this will work, and the risk level is **{risk}**.",
                step="reasoning",
            )

            # ── Hypotheses (if available) ──────────
            hypotheses = reasoning.get("hypotheses", [])
            if hypotheses:
                hyp_lines = []
                for h in hypotheses[:3]:
                    prob = int(h.get("probability", 0) * 100)
                    hyp_lines.append(f"- {h.get('cause', 'Unknown')} ({prob}% likely)")
                self.log(
                    "My analysis considers these possible causes:\n" + "\n".join(hyp_lines),
                    step="reasoning",
                )

            # ── HITL: Request Approval ─────────────
            self.log(
                "I need your approval before I apply this fix. "
                "Please review the details and approve, modify, or reject.",
                step="approval",
            )
            publish_status(self.task_id, "awaiting_approval", "Waiting for your approval...")

            fix_details = {
                "iteration": iteration,
                "analysis": {
                    "error_type": error_type,
                    "message": error_msg,
                    "target": target,
                    "confidence": analysis["confidence"],
                },
                "reasoning": {
                    "hypotheses": hypotheses,
                    "best_fix": best_fix,
                    "confidence": confidence,
                    "risk": risk,
                },
            }

            hitl_response = request_approval(self.task_id, fix_details)
            decision = hitl_response.get("decision", "timeout")

            # ── Handle Decision ────────────────────
            if decision == "reject":
                self.log(
                    "Got it — you've rejected this fix. I'll try a different approach in the next iteration.",
                    step="approval",
                )
                publish_status(self.task_id, "rejected", "Fix was rejected.")

                history.append({
                    "iteration": iteration,
                    "analysis": analysis,
                    "reasoning": reasoning,
                    "applied": False,
                    "hitl_decision": "rejected",
                    "result": result,
                })
                continue

            elif decision == "timeout":
                self.log(
                    "The approval request timed out. I'll stop here — feel free to start a new build when you're ready.",
                    step="error",
                )
                publish_status(self.task_id, "timeout", "Approval timed out.")

                history.append({
                    "iteration": iteration,
                    "analysis": analysis,
                    "reasoning": reasoning,
                    "applied": False,
                    "hitl_decision": "timeout",
                    "result": result,
                })

                return {
                    "status": "TIMEOUT",
                    "history": history,
                }

            elif decision == "modify":
                modified_cmd = hitl_response.get("modified_command", "")
                self.log(
                    f"Thanks! You've modified the command to:\n\n`{modified_cmd}`\n\nI'll use your version instead.",
                    step="approval",
                )
                best_fix["command"] = modified_cmd
                command = modified_cmd
                reasoning["best_fix"] = best_fix
            else:
                self.log("Thanks for approving! Applying the fix now...", step="approval")

            # ── Apply Fix ──────────────────────────
            publish_status(self.task_id, "applying_fix", "Applying the approved fix...")

            applied = self.apply_fix(project_path, reasoning)

            history.append({
                "iteration": iteration,
                "analysis": analysis,
                "reasoning": reasoning,
                "applied": applied,
                "hitl_decision": decision,
                "result": result,
            })

            if not applied:
                self.log(
                    "Hmm, I wasn't able to apply that fix. Let me try a different approach...",
                    step="error",
                )
                publish_status(self.task_id, "fix_failed", "Fix could not be applied.")
                continue

            self.log("Fix applied successfully! Rebuilding to see if it worked...", step="retry")
            publish_status(self.task_id, "rebuilding", "Re-running build after fix...")

            # ── RAG: Store on success ──────────────
            peek_result = self.executor.run_build(project_path)
            if peek_result["success"] and self.retriever:
                error_text = f"{error_type}: {error_msg}"
                fix_metadata = {
                    "error_type": error_type,
                    "error_message": error_msg,
                    "fix_action": best_fix.get("action"),
                    "fix_command": command,
                    "fix_explanation": explanation,
                    "project_type": self.project_type,
                    "outcome": "success",
                }
                self.retriever.store(error_text, fix_metadata)
                self.log(
                    "The fix worked! I've saved this solution to my memory so I can use it if I see a similar issue in the future.",
                    step="success",
                )

                publish_status(self.task_id, "success", "Build succeeded after fix!")
                return {
                    "status": "SUCCESS",
                    "history": history,
                    "final_result": peek_result,
                }

        # ── Exhausted iterations ───────────────
        self.log(
            f"I've tried {self.max_iterations} different approaches but wasn't able to fix the build automatically. "
            "I recommend reviewing the error details above and trying a manual fix. "
            "If you'd like, you can start a new session and I'll try again with a fresh perspective.",
            step="summary",
        )
        publish_status(
            self.task_id, "failed",
            "Build could not be fixed automatically. Please review the error details above.",
        )

        return {
            "status": "FAILED",
            "history": history,
        }

    # -----------------------------------------
    # Apply Fix
    # -----------------------------------------
    def apply_fix(self, project_path: str, reasoning: dict):
        fix = reasoning.get("best_fix", {})
        raw_action = fix.get("action", "")
        command = fix.get("command", "")

        action = self.normalize_action(raw_action)

        if action in ("install_dependency", "run_command"):
            return self.run_fix_in_container(project_path, command)

        if action == "edit_file":
            return self.apply_file_edit(project_path, fix)

        # Fallback: try running as shell command if we have one
        if command:
            return self.run_fix_in_container(project_path, command)

        return False

    def normalize_action(self, action: str):
        action = action.lower().strip()

        if "install" in action and "dependency" in action:
            return "install_dependency"

        if "run" in action and "command" in action:
            return "run_command"

        if "edit" in action and "file" in action:
            return "edit_file"

        return action

    def run_fix_in_container(self, project_path: str, command: str):
        """Run the fix command inside a container using the executor."""
        try:
            result = self.executor.run_command(project_path, command)

            if result["success"]:
                return True
            else:
                self.log(
                    f"The fix command returned an error:\n\n```\n{result['logs']}\n```",
                    step="error",
                )
                return False

        except Exception as e:
            self.log(f"Something went wrong while applying the fix: {e}", step="error")
            return False

    def apply_file_edit(self, project_path: str, fix: dict):
        """Apply a file edit fix (write content to a file)."""
        file_path = fix.get("file_path", "")
        file_content = fix.get("file_content", "")

        if not file_path or not file_content:
            self.log("I need both a file path and content to edit a file, but one was missing.", step="error")
            return False

        try:
            full_path = os.path.join(os.path.abspath(project_path), file_path)

            # Safety: don't write outside project
            if not full_path.startswith(os.path.abspath(project_path)):
                self.log("I can't write outside the project directory for security reasons.", step="error")
                return False

            os.makedirs(os.path.dirname(full_path), exist_ok=True)

            with open(full_path, "w") as f:
                f.write(file_content)

            self.log(f"I've updated the file `{file_path}`.", step="fix")
            return True

        except Exception as e:
            self.log(f"I couldn't edit the file: {e}", step="error")
            return False