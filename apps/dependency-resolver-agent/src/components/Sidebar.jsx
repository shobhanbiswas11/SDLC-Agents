import { useState } from "react";
import "./Sidebar.css";

const NAV_ITEMS = [
  { id: "scanner", icon: "RS", label: "Repository Scanner" },
  { id: "graph", icon: "DG", label: "Dependency Graph" },
  { id: "conflicts", icon: "CA", label: "Conflict Analysis" },
  { id: "ai", icon: "AI", label: "Intelligence" },
];

export default function Sidebar({ activeTab, onTabChange }) {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <aside className={`sidebar ${collapsed ? "collapsed" : ""}`}>
      <div className="sidebar-header">
        <div className="sidebar-logo">
          <span className="logo-icon">DR</span>
          {!collapsed && (
            <div className="logo-text-wrap">
              <span className="logo-text">Dependency Resolver</span>
              <span className="logo-subtext">Enterprise Console</span>
            </div>
          )}
        </div>
        <button
          className="sidebar-toggle"
          onClick={() => setCollapsed(!collapsed)}
          aria-label="Toggle sidebar"
        >
          {collapsed ? ">" : "<"}
        </button>
      </div>

      <nav className="sidebar-nav">
        {NAV_ITEMS.map((item) => (
          <button
            key={item.id}
            className={`nav-item ${activeTab === item.id ? "active" : ""}`}
            onClick={() => onTabChange(item.id)}
            title={item.label}
          >
            <span className="nav-icon">{item.icon}</span>
            {!collapsed && <span className="nav-label">{item.label}</span>}
            {activeTab === item.id && <span className="nav-indicator" />}
          </button>
        ))}
      </nav>

      <div className="sidebar-footer">
        {!collapsed && <span className="sidebar-version">Version 0.1.0</span>}
      </div>
    </aside>
  );
}
