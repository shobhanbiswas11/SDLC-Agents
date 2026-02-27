import React from "react";
import MessageBubble from "./MessageBubble";

const ChatWindow = ({ messages }) => {
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