import React from "react";

const Sidebar = () => {
  return (
    <aside className="w-64 h-full border-r border-zinc-800 bg-zinc-900 p-4">
      <h2 className="text-zinc-300 text-sm font-semibold uppercase tracking-wider mb-4">
        History
      </h2>

      <div className="text-zinc-500 text-sm">
        No chats yet.
      </div>
    </aside>
  );
};

export default Sidebar;