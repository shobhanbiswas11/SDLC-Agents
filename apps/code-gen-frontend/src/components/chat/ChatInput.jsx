import React, { useState } from "react";

const ChatInput = ({ onSend }) => {
  const [message, setMessage] = useState("");

  const handleSubmit = () => {
    if (!message.trim()) return;

    onSend(message);
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
          className="flex-1 bg-transparent resize-none outline-none text-zinc-200 placeholder-zinc-500 text-sm leading-relaxed max-h-40 overflow-y-auto"
        />

        <button
          onClick={handleSubmit}
          className="bg-white text-black px-4 py-2 rounded-xl text-sm font-medium hover:bg-zinc-200 transition"
        >
          Send
        </button>
      </div>
    </div>
  );
};

export default ChatInput;