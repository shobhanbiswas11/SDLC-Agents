import React, { useState } from "react";
import Navbar from "./Navbar";
import Sidebar from "./Sidebar";
import ChatWindow from "../chat/ChatWindow";
import ChatInput from "../chat/ChatInput";
import ClarificationForm from "../chat/ClarificationForm";
import ProjectResult from "../chat/ProjectResult";

const MainLayout = () => {
  const [messages, setMessages] = useState([
    {
      id: 1,
      role: "assistant",
      content: "Hello! Describe the project you want to generate.",
    },
  ]);

  const [currentSpec, setCurrentSpec] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [missingFields, setMissingFields] = useState(null);
  const [generationResult, setGenerationResult] = useState(null);

  const handleClarificationSubmit = async (answers) => {
    if (isLoading) return;

    setIsLoading(true);

    try {
      const response = await fetch("http://localhost:8000/generate/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          text: null,
          spec: currentSpec,
          answers: answers,
        }),
      });

      const data = await response.json();

      if (data.status === "complete") {
        setMissingFields(null);
        setCurrentSpec(null);
        setGenerationResult({
          tree: data.tree,
          initInstructions: data.init_instructions,
          runId: data.run_id,
        });

        setMessages((prev) => [
          ...prev,
          {
            id: Date.now(),
            role: "assistant",
            content: "__PROJECT_RESULT__",
          },
        ]);

        console.log("Generated Blueprint:", data);
      }
    } catch (error) {
      console.error(error);
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now(),
          role: "assistant",
          content: "Something went wrong while generating the project.",
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSend = async (userMessage) => {
    if (isLoading) return;

    // Reset previous result when starting a new generation
    setGenerationResult(null);

    const newUserMessage = {
      id: Date.now(),
      role: "user",
      content: userMessage,
    };

    setMessages((prev) => [...prev, newUserMessage]);
    setIsLoading(true);

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

      if (data.status === "missing") {
        setCurrentSpec(data.spec);
        setMissingFields(data.missing_fields);

        setMessages((prev) => [
          ...prev,
          {
            id: Date.now(),
            role: "assistant",
            content:
              "Please provide the following details to continue project generation.",
          },
        ]);
      }

      if (data.status === "complete") {
        setCurrentSpec(null);
        setGenerationResult({
          tree: data.tree,
          initInstructions: data.init_instructions,
          runId: data.run_id,
        });

        setMessages((prev) => [
          ...prev,
          {
            id: Date.now() + 1,
            role: "assistant",
            content: "__PROJECT_RESULT__",
          },
        ]);
      }
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now() + 1,
          role: "assistant",
          content: "Something went wrong while contacting the server.",
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="h-screen flex flex-col bg-zinc-950 overflow-hidden">
      <Navbar />

      <div className="flex flex-1 overflow-hidden">
        <Sidebar />

        <div className="flex flex-col flex-1 bg-zinc-950">
          <div className="flex-1 overflow-y-auto px-6 py-6">
            <ChatWindow
              messages={messages}
              isLoading={isLoading}
              generationResult={generationResult}
            />
          </div>

          <div className="border-t border-zinc-800 bg-zinc-900 p-4">
            {missingFields ? (
              <ClarificationForm
                missingFields={missingFields}
                isLoading={isLoading}
                onSubmit={(answers) => handleClarificationSubmit(answers)}
              />
            ) : (
              <ChatInput onSend={handleSend} isLoading={isLoading} />
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default MainLayout;