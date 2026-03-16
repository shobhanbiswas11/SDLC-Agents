import React from "react";
import MessageBubble from "./MessageBubble";
import ProjectResult from "./ProjectResult";

const ChatWindow = ({ messages, isLoading, generationResult, progressMessage }) => {
  return (
    <div className="space-y-6">
      {messages.map((message) => {
        // Render rich project result instead of a plain bubble
        if (
          message.role === "assistant" &&
          message.content === "__PROJECT_RESULT__" &&
          generationResult
        ) {
          return (
            <ProjectResult
              key={message.id}
              tree={generationResult.tree}
              initInstructions={generationResult.initInstructions}
              runId={generationResult.runId}
            />
          );
        }

        return (
          <MessageBubble
            key={message.id}
            role={message.role}
            content={message.content}
          />
        );
      })}

      {isLoading && (
        <MessageBubble role="assistant" isLoading progressMessage={progressMessage} />
      )}
    </div>
  );
};

export default ChatWindow;