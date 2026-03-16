import React, { useState } from "react";

const ChatInput = ({ onSend, isLoading }) => {
  const [message, setMessage] = useState("");

  const handleSubmit = () => {
    const cleaned = message.trim();
    if (!cleaned || isLoading) return;

    onSend(cleaned);
    setMessage("");
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="max-w-4xl mx-auto w-full">
      <div className="flex items-end gap-3 bg-zinc-800 border border-zinc-700 rounded-2xl px-4 py-3 shadow-md">

        <textarea
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={handleKeyDown}
          rows={1}
          placeholder="Describe the project you want to generate..."
          className="flex-1 bg-transparent resize-none outline-none text-zinc-200 placeholder-zinc-500 text-sm leading-relaxed min-h-20 max-h-40 overflow-y-auto"
        />

        <button
          onClick={handleSubmit}
          disabled={isLoading}
          className={`px-4 py-2 rounded-xl text-sm font-medium transition ${isLoading
              ? "bg-zinc-600 text-zinc-300 cursor-not-allowed"
              : "bg-white text-black hover:bg-zinc-200"
            }`}
        >
          {isLoading ? (
            <span className="flex items-center gap-2">
              <span className="w-4 h-4 border-2 border-zinc-400 border-t-transparent rounded-full animate-spin"></span>
              Generating...
            </span>
          ) : (
            "Send"
          )}
        </button>

      </div>
    </div>
  );
};

export default ChatInput;