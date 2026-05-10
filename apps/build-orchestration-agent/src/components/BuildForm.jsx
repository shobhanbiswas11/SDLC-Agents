import { useState } from "react";

function BuildForm({ onSubmit, loading }) {
  const [path, setPath] = useState("");

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!path) return;
    onSubmit(path);
  };

  return (
    <form onSubmit={handleSubmit} className="form">
      <input
        type="text"
        placeholder="Enter project path..."
        value={path}
        onChange={(e) => setPath(e.target.value)}
      />

      <button type="submit" disabled={loading}>
        {loading ? "Running..." : "Run Build"}
      </button>
    </form>
  );
}

export default BuildForm;