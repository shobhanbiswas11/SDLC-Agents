import React from "react";
import MessageBubble from "./MessageBubble";

const ChatWindow = () => {
  const messages = [
    {
      id: 1,
      role: "assistant",
      content: "Hello! Describe the project you want to generate.",
    },
    {
      id: 2,
      role: "user",
      content: "Build a FastAPI backend with JWT authentication.",
    },
    {
      id: 3,
      role: "assistant",
      content:
        "Some required fields are missing. What should be the project name?",
    },
  ];

  return (
    <div className="space-y-6">
      {messages.map((message) => (
        <MessageBubble
          key={message.id}
          role={message.role}
          content={message.content}
        />
      ))}
    </div>
  );
};

export default ChatWindow;