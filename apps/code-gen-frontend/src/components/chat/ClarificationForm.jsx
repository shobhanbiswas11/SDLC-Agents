import React, { useState } from "react";

const ClarificationForm = ({ missingFields, onSubmit, isLoading }) => {
  const [answers, setAnswers] = useState({});

  const handleChange = (field, value) => {
    setAnswers((prev) => ({
      ...prev,
      [field]: value,
    }));
  };

  const handleSubmit = () => {
    if (isLoading) return;
    onSubmit(answers);
  };

  return (
    <div className="max-w-4xl mx-auto w-full space-y-4 bg-zinc-900 p-6 rounded-2xl border border-zinc-800">
      <h3 className="text-zinc-200 font-semibold">
        Provide Missing Information
      </h3>

      {missingFields.map((field) => (
        <div key={field} className="flex flex-col gap-2">
          <label className="text-zinc-400 text-sm">{field}</label>
          <input
            type="text"
            className="bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-zinc-200 outline-none"
            onChange={(e) => handleChange(field, e.target.value)}
          />
        </div>
      ))}

      <button
        onClick={handleSubmit}
        disabled={isLoading}
        className={`px-4 py-2 rounded-xl text-sm font-medium transition ${
          isLoading
            ? "bg-zinc-600 text-zinc-300 cursor-not-allowed"
            : "bg-white text-black hover:bg-zinc-200"
        }`}
      >
        {isLoading ? "Generating..." : "Submit"}
      </button>
    </div>
  );
};

export default ClarificationForm;