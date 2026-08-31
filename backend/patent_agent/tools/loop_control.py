"""Loop-control tool used by adversarial_agent to end the inventor/adversarial LoopAgent."""

from google.adk.tools import ToolContext


def exit_loop(tool_context: ToolContext) -> dict:
    """Call this when the current candidate invention has survived adversarial review
    (or when further iteration would not change the verdict), to stop the invention loop.
    """
    tool_context.actions.escalate = True
    return {"status": "loop_exited"}
