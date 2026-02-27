import React from "react";
import Navbar from "./Navbar";
import Sidebar from "./Sidebar";
import ChatWindow from "../chat/ChatWindow";
import ChatInput from "../chat/ChatInput";

const MainLayout = () => {
  return (
    <div className="h-screen flex flex-col bg-zinc-950 overflow-hidden">
      
      {/* Top Navbar */}
      <Navbar />

      {/* Body Section */}
      <div className="flex flex-1 overflow-hidden">
        
        {/* Sidebar */}
        <Sidebar />

        {/* Chat Area */}
        <div className="flex flex-col flex-1 bg-zinc-950">
          
          {/* Scrollable Chat Window */}
          <div className="flex-1 overflow-y-auto px-6 py-6">
            <ChatWindow />
          </div>

          {/* Fixed Bottom Input */}
          <div className="border-t border-zinc-800 bg-zinc-900 p-4">
            <ChatInput />
          </div>

        </div>
      </div>
    </div>
  );
};

export default MainLayout;