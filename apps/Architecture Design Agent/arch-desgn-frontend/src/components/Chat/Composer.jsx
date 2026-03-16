import { useState } from "react";

export function Composer({
    onSend,
    disabled = false,
    placeholder = "Describe your product or add new requirements…",
}) {
    const [text, setText] = useState("");

    const submit = () => {
        const t = text.trim();
        if (!t || disabled) return;
        onSend(t);
        setText("");
    };

    return (
        <div className="composer">
            <div className="composer__wrapper">
                <input
                    className="composer__input"
                    value={text}
                    onChange={(e) => setText(e.target.value)}
                    onKeyDown={(e) => {
                        if (e.key === "Enter" && !e.shiftKey) {
                            e.preventDefault();
                            submit();
                        }
                    }}
                    placeholder={placeholder}
                    disabled={disabled}
                />
                <button
                    className="composer__btn"
                    onClick={submit}
                    disabled={disabled || !text.trim()}
                    aria-label="Send message"
                >
                    {disabled ? (
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <circle cx="12" cy="12" r="10" />
                            <path d="M12 6v6l4 2" />
                        </svg>
                    ) : (
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <line x1="12" y1="19" x2="12" y2="5" />
                            <polyline points="5 12 12 5 19 12" />
                        </svg>
                    )}
                </button>
            </div>
        </div>
    );
}
