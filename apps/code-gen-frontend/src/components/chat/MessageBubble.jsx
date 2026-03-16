import React from "react";
import clsx from "clsx";

const MessageBubble = ({ role = "assistant", content, isLoading = false, progressMessage }) => {
  const isUser = role === "user";

  return (
    <div
      className={clsx(
        "w-full flex",
        isUser ? "justify-end" : "justify-start"
      )}
    >
      <div
        className={clsx(
          "max-w-3xl px-5 py-3 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap break-words",
          isUser
            ? "bg-white text-black rounded-br-md"
            : "bg-zinc-800 text-zinc-100 rounded-bl-md"
        )}
      >
        {isLoading ? (
          <div className="flex flex-col gap-2">
            <div className="flex items-center gap-2 text-zinc-400">
              <span className="w-4 h-4 border-2 border-violet-400 border-t-transparent rounded-full animate-spin"></span>
              <span
                key={progressMessage}
                className="animate-fade-in text-zinc-300"
              >
                {progressMessage || "Thinking..."}
              </span>
            </div>
          </div>
        ) : (
          content
        )}
      </div>
    </div>
  );
};

export default MessageBubble;