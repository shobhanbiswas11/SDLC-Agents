export function MessageList({ messages }) {
    if (messages.length === 0) {
        return (
            <div className="chat-empty">
                <div className="chat-empty__title">Start a conversation</div>
                <div className="chat-empty__desc">
                    Describe your product idea and I'll design the perfect architecture for you.
                </div>
            </div>
        );
    }

    return (
        <div className="chat-messages">
            {messages.map((m, i) => (
                <div key={i} className={`msg-group msg-group--${m.role}`}>
                    <div className="msg__label">
                        {m.role === "user" ? "You" : "Architect"}
                    </div>
                    <div className={`msg msg--${m.role}`}>
                        <div className="msg__content" style={{ whiteSpace: "pre-wrap" }}>
                            {m.content}
                        </div>
                    </div>
                </div>
            ))}
        </div>
    );
}
