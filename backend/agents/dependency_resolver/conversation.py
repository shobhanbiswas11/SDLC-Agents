"""
Conversation management for human-in-the-loop resolution
Tracks messages, context, and resolution decisions through chat
"""

import json
import os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class ConversationMessage:
    """Single message in conversation"""
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: str
    context: Optional[Dict[str, Any]] = None

    def to_dict(self):
        return asdict(self)


class ConversationManager:
    """Manages human-in-the-loop conversation for resolution"""

    def __init__(self, session_id: str, state_dir: str = "state"):
        """
        Initialize conversation manager

        Args:
            session_id: Unique session identifier
            state_dir: Directory for storing conversation history
        """
        self.session_id = session_id
        self.state_dir = state_dir
        self.conversation_file = os.path.join(state_dir, f"{session_id}_conversation.json")
        self.messages: List[ConversationMessage] = []
        self.context: Dict[str, Any] = {}

        # Load existing conversation if available
        self._load_conversation()

    def add_message(
        self,
        role: str,
        content: str,
        context: Optional[Dict[str, Any]] = None
    ) -> ConversationMessage:
        """
        Add message to conversation

        Args:
            role: 'user' or 'assistant'
            content: Message text
            context: Optional contextual information

        Returns:
            The added message
        """
        message = ConversationMessage(
            role=role,
            content=content,
            timestamp=datetime.now().isoformat(),
            context=context
        )

        self.messages.append(message)

        # Update global context
        if context:
            self.context.update(context)

        # Persist
        self._save_conversation()

        logger.info(f"[{self.session_id}] Added {role} message")
        return message

    def get_conversation_history(self) -> List[Dict[str, str]]:
        """
        Get conversation in format suitable for LLM

        Returns:
            List of dicts with 'role' and 'content'
        """
        return [
            {"role": msg.role, "content": msg.content}
            for msg in self.messages
        ]

    def get_system_prompt(self) -> str:
        """Get system prompt for LLM conversation"""
        return """You are an expert dependency resolver AI assistant. Your role is to:

1. Help users understand dependency conflicts in their npm/Python packages
2. Analyze version constraints and compatibility issues
3. Suggest resolution strategies (minimal changes, latest versions, or hybrid)
4. Explain technical decisions in clear language
5. Guide users through manual resolution if needed

When helping resolve dependencies:
- Be clear and technical but understandable
- Explain trade-offs between different approaches
- Ask clarifying questions when needed
- Provide specific version recommendations
- Consider security, stability, and feature updates

Keep responses concise but informative. Focus on actionable advice."""

    def get_full_context(self) -> Dict[str, Any]:
        """Get full context for LLM understanding"""
        return {
            "session_id": self.session_id,
            "message_count": len(self.messages),
            "has_conflicts": self.context.get("has_conflicts", False),
            "packages_count": self.context.get("packages_count", 0),
            "stage": self.context.get("stage", "initial"),
            **self.context
        }

    def clear_conversation(self):
        """Clear conversation history"""
        self.messages = []
        self.context = {}
        if os.path.exists(self.conversation_file):
            os.remove(self.conversation_file)
        logger.info(f"[{self.session_id}] Conversation cleared")

    def _save_conversation(self):
        """Save conversation to file"""
        try:
            data = {
                "session_id": self.session_id,
                "messages": [msg.to_dict() for msg in self.messages],
                "context": self.context,
                "last_updated": datetime.now().isoformat()
            }

            os.makedirs(self.state_dir, exist_ok=True)
            with open(self.conversation_file, 'w') as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            logger.error(f"Failed to save conversation: {e}")

    def _load_conversation(self):
        """Load conversation from file if exists"""
        try:
            if os.path.exists(self.conversation_file):
                with open(self.conversation_file, 'r') as f:
                    data = json.load(f)

                # Reconstruct messages
                self.messages = [
                    ConversationMessage(
                        role=msg["role"],
                        content=msg["content"],
                        timestamp=msg["timestamp"],
                        context=msg.get("context")
                    )
                    for msg in data.get("messages", [])
                ]

                # Restore context
                self.context = data.get("context", {})

                logger.info(f"[{self.session_id}] Loaded {len(self.messages)} messages")

        except Exception as e:
            logger.error(f"Failed to load conversation: {e}")
            self.messages = []
            self.context = {}

    def get_summary(self) -> str:
        """Get brief summary of conversation"""
        if not self.messages:
            return "No conversation yet"

        user_msgs = sum(1 for m in self.messages if m.role == "user")
        assistant_msgs = sum(1 for m in self.messages if m.role == "assistant")

        return f"Conversation with {user_msgs} user messages and {assistant_msgs} assistant responses"


def create_conversation_manager(session_id: str, state_dir: str = "state") -> ConversationManager:
    """Factory function to create conversation manager"""
    return ConversationManager(session_id, state_dir)
