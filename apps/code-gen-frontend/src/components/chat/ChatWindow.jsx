import React from "react";
import MessageBubble from "./MessageBubble";

const ChatWindow = ({ messages, isLoading }) => {
  return (
    <div className="space-y-6">
      {messages.map((message) => (
        <MessageBubble
          key={message.id}
          role={message.role}
          content={message.content}
        />
      ))}

      {isLoading && (
        <MessageBubble role="assistant" isLoading />
      )}
    </div>
  );
};

export default ChatWindow;