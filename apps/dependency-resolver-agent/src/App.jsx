import { useState } from "react";
import Sidebar from "./components/Sidebar";
import Dashboard from "./pages/Dashboard";
import "./App.css";

export default function App() {
  const [activeTab, setActiveTab] = useState("scanner");

  return (
    <div className="app-layout">
      <Sidebar activeTab={activeTab} onTabChange={setActiveTab} />
      <Dashboard activeTab={activeTab} />
    </div>
  );
}
