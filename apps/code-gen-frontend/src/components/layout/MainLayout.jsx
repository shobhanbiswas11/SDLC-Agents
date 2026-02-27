import React, { useState } from "react";
import Navbar from "./Navbar";
import Sidebar from "./Sidebar";
import ChatWindow from "../chat/ChatWindow";
import ChatInput from "../chat/ChatInput";

const MainLayout = () => {
  const [messages, setMessages] = useState([
    {
      id: 1,
      role: "assistant",
      content: "Hello! Describe the project you want to generate.",
    },
  ]);

  const [currentSpec, setCurrentSpec] = useState(null);

  const handleSend = async (userMessage) => {
    const newUserMessage = {
      id: Date.now(),
      role: "user",
      content: userMessage,
    };

    setMessages((prev) => [...prev, newUserMessage]);

    try {
      const response = await fetch("http://localhost:8000/generate/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          text: currentSpec ? null : userMessage,
          spec: currentSpec,
        }),
      });

      const data = await response.json();
      console.log("FULL RESPONSE:", data);

      if (data.status === "missing") {
        setCurrentSpec(data.spec);

        const formatted =
          "Please clarify the following questions.\n\n" +
          "Just write the question number and give answers:\n\n" +
          data.questions;

        setMessages((prev) => [
          ...prev,
          {
            id: Date.now(),
            role: "assistant",
            content: formatted,
          },
        ]);
      }

      if (data.status === "complete") {
        setCurrentSpec(null);

        const assistantMessage = {
          id: Date.now() + 1,
          role: "assistant",
          content: `Project generated successfully!\n\nRun ID: ${data.run_id}`,
        };

        setMessages((prev) => [...prev, assistantMessage]);
      }
    } catch (error) {
      console.error("Error:", error);

      setMessages((prev) => [
        ...prev,
        {
          id: Date.now() + 1,
          role: "assistant",
          content: "Something went wrong while contacting the server.",
        },
      ]);
    }
  };

  return (
    <div className="h-screen flex flex-col bg-zinc-950 overflow-hidden">
      <Navbar />

      <div className="flex flex-1 overflow-hidden">
        <Sidebar />

        <div className="flex flex-col flex-1 bg-zinc-950">
          <div className="flex-1 overflow-y-auto px-6 py-6">
            <ChatWindow messages={messages} />
          </div>

          <div className="border-t border-zinc-800 bg-zinc-900 p-4">
            <ChatInput onSend={handleSend} />
          </div>
        </div>
      </div>
    </div>
  );
};

export default MainLayout;