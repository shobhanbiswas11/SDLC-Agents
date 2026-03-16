export function sendMessage(message, sessionId) {
    const apiBase = import.meta.env.VITE_API_URL || "http://localhost:8000";
    return fetch(`${apiBase}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message, session_id: sessionId }),
    }).then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
    });
}
