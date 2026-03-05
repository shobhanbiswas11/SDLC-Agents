import { useState, useRef, useEffect } from "react";
import { sendMessage } from "../lib/api";
import { Composer } from "../components/Chat/Composer";
import { MessageList } from "../components/Chat/MessageList";
import { MermaidRenderer } from "../components/MermaidRenderer";


export default function ChatPage() {
    const [sessionId, setSessionId] = useState(undefined);
    const [messages, setMessages] = useState([]);
    const [last, setLast] = useState(null);
    const [loading, setLoading] = useState(false);

    // Answers map for question cards: key → answer string
    const [answers, setAnswers] = useState({});
    const [copied, setCopied] = useState(false);

    const messagesEndRef = useRef(null);
    const diagramRef = useRef(null);

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages, loading]);

    async function onSend(text) {
        setMessages((m) => [...m, { role: "user", content: text }]);
        setLoading(true);
        setAnswers({});

        try {
            const res = await sendMessage(text, sessionId);
            setSessionId(res.session_id);
            setLast(res);

            const assistantText = renderAssistantSummary(res);
            if (assistantText) {
                setMessages((m) => [...m, { role: "assistant", content: assistantText }]);
            }
        } catch (err) {
            const detail = err?.message || "Unknown error";
            setMessages((m) => [
                ...m,
                { role: "assistant", content: `Error: ${detail}\n\nPlease try rephrasing or simplifying your input.` },
            ]);
        } finally {
            setLoading(false);
        }
    }

    /** Submit all selected options / typed answers for all question cards */
    function submitAnswers(questions) {
        const parts = [];
        for (const q of questions) {
            const ans = answers[q.key]?.trim();
            if (ans) {
                parts.push(`${q.question}: ${ans}`);
            }
        }
        if (parts.length === 0) return;
        onSend(parts.join("\n"));
    }

    /** Select / deselect an option for a question (multi-select via comma) */
    function selectOption(key, opt) {
        setAnswers((prev) => {
            const current = prev[key] ?? "";
            const selected = current.split(",").map((s) => s.trim()).filter(Boolean);
            const idx = selected.indexOf(opt);
            if (idx >= 0) {
                selected.splice(idx, 1);
            } else {
                selected.push(opt);
            }
            return { ...prev, [key]: selected.join(", ") };
        });
    }

    function setAnswer(key, value) {
        setAnswers((prev) => ({ ...prev, [key]: value }));
    }

    const hasAnswers = Object.values(answers).some((v) => v.trim());
    const questions = last?.stage === "intake" ? last.intake?.questions ?? [] : [];

    return (
        <div className="app-shell">
            {/* ── Header ── */}
            <div className="app-header">
                <div className="app-header__left">
                    <div className="app-header__logo">A</div>
                    <h1>Architecture Design Agent</h1>
                </div>
            </div>

            {/* ── Main Content ── */}
            <div className="app-main">
                {/* Left: Chat Panel */}
                <div className="chat-panel">
                    <MessageList messages={messages} />
                    {loading && (
                        <div className="loading-dots">
                            <span /><span /><span />
                        </div>
                    )}
                    <div ref={messagesEndRef} />
                    <Composer
                        onSend={onSend}
                        disabled={loading}
                        placeholder={
                            questions.length > 0
                                ? "Or type your answer here…"
                                : "Describe your product or add requirements…"
                        }
                    />
                </div>

                {/* Right: Result Panel */}
                <div className="result-panel">
                    <div className="result-panel__header">
                        <h2>Architecture Panel</h2>
                    </div>

                    <div className="result-panel__content">
                        {!last && !loading && (
                            <div className="result-placeholder">
                                <p>Start by describing your product idea. I'll design the perfect architecture for you.</p>
                            </div>
                        )}

                        {loading && (
                            <div className="result-placeholder">
                                <div className="loading-spinner" />
                                <p>Analyzing your requirements…</p>
                            </div>
                        )}

                        {/* ─── Iterative Intake: Question Cards ─── */}
                        {questions.length > 0 && !loading && (
                            <div className="questions-section">
                                <h3>Select your preferences</h3>
                                <div className="questions-grid">
                                    {questions.map((q) => {
                                        const currentAnswer = answers[q.key] ?? "";
                                        return (
                                            <div
                                                key={q.key}
                                                className={`question-card${currentAnswer.trim() ? " answered" : ""}`}
                                            >
                                                <div className="question-card__label">{q.question}</div>
                                                <div className="question-card__reason">{q.reason}</div>

                                                {q.options && q.options.length > 0 && (
                                                    <div className="question-card__options">
                                                        {q.options.map((opt) => {
                                                            const selectedOpts = currentAnswer.split(",").map((s) => s.trim());
                                                            const isSelected = selectedOpts.includes(opt);
                                                            return (
                                                                <button
                                                                    key={opt}
                                                                    className={`option-btn${isSelected ? " selected" : ""}`}
                                                                    onClick={() => selectOption(q.key, opt)}
                                                                >
                                                                    {opt}
                                                                </button>
                                                            );
                                                        })}
                                                    </div>
                                                )}

                                                <input
                                                    className="question-card__input"
                                                    placeholder="Or type a custom answer…"
                                                    value={currentAnswer}
                                                    onChange={(e) => setAnswer(q.key, e.target.value)}
                                                />
                                            </div>
                                        );
                                    })}
                                </div>

                                <button
                                    className="submit-answers-btn"
                                    disabled={!hasAnswers || loading}
                                    onClick={() => submitAnswers(questions)}
                                >
                                    Submit Answers →
                                </button>
                            </div>
                        )}

                        {/* ─── Architecture Results ─── */}
                        {last?.architecture && !loading && (
                            <>
                                {last.impact && (
                                    <div style={{ marginBottom: 16 }}>
                                        <span className={`impact-badge impact-badge--${last.impact.impact}`}>
                                            ● {last.impact.impact} impact
                                        </span>
                                        {last.impact.reasons?.length > 0 && (
                                            <ul className="impact-reasons">
                                                {last.impact.reasons.map((r, i) => (
                                                    <li key={i}>{r}</li>
                                                ))}
                                            </ul>
                                        )}
                                    </div>
                                )}

                                {last.architecture.delta && (
                                    <div className="delta-section">
                                        <h3>Delta View</h3>
                                        <div className="delta-versions">
                                            <strong>v{last.architecture.delta.version_from}</strong>
                                            <span className="arrow">→</span>
                                            <strong>v{last.architecture.delta.version_to}</strong>
                                        </div>
                                        {last.architecture.delta.what_changed.length > 0 && (
                                            <ul className="delta-list">
                                                {last.architecture.delta.what_changed.map((x, i) => (
                                                    <li key={i}>{x}</li>
                                                ))}
                                            </ul>
                                        )}
                                        {last.architecture.delta.migration_steps.length > 0 && (
                                            <>
                                                <h4>Migration Steps</h4>
                                                <ol className="delta-list">
                                                    {last.architecture.delta.migration_steps.map((x, i) => (
                                                        <li key={i}>{x}</li>
                                                    ))}
                                                </ol>
                                            </>
                                        )}
                                    </div>
                                )}

                                <div className="diagram-section">
                                    <div className="diagram-section__header">
                                        <h3>Architecture Diagram</h3>
                                        <div className="diagram-section__actions">
                                            <button
                                                className="diagram-icon-btn"
                                                title="Copy Mermaid code"
                                                onClick={() => {
                                                    const code = last.architecture.diagram?.content ?? "";
                                                    navigator.clipboard.writeText(code).then(() => {
                                                        setCopied(true);
                                                        setTimeout(() => setCopied(false), 2000);
                                                    });
                                                }}
                                            >
                                                {copied ? (
                                                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="20 6 9 17 4 12" /></svg>
                                                ) : (
                                                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="9" y="9" width="13" height="13" rx="2" /><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" /></svg>
                                                )}
                                            </button>
                                            <button
                                                className="diagram-icon-btn"
                                                title="Download as SVG"
                                                onClick={() => {
                                                    const svgEl = diagramRef.current?.querySelector("svg");
                                                    if (!svgEl) return;
                                                    try {
                                                        const clone = svgEl.cloneNode(true);
                                                        // Set explicit dimensions
                                                        const bbox = svgEl.getBoundingClientRect();
                                                        clone.setAttribute("width", Math.round(bbox.width));
                                                        clone.setAttribute("height", Math.round(bbox.height));
                                                        clone.setAttribute("xmlns", "http://www.w3.org/2000/svg");
                                                        // Add white background
                                                        const bg = document.createElementNS("http://www.w3.org/2000/svg", "rect");
                                                        bg.setAttribute("width", "100%");
                                                        bg.setAttribute("height", "100%");
                                                        bg.setAttribute("fill", "#ffffff");
                                                        clone.insertBefore(bg, clone.firstChild);
                                                        const svgData = new XMLSerializer().serializeToString(clone);
                                                        const blob = new Blob([svgData], { type: "image/svg+xml;charset=utf-8" });
                                                        const a = document.createElement("a");
                                                        a.href = URL.createObjectURL(blob);
                                                        a.download = "architecture-diagram.svg";
                                                        document.body.appendChild(a);
                                                        a.click();
                                                        document.body.removeChild(a);
                                                        URL.revokeObjectURL(a.href);
                                                    } catch (err) {
                                                        console.error("Download failed:", err);
                                                    }
                                                }}
                                            >
                                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><polyline points="7 10 12 15 17 10" /><line x1="12" y1="15" x2="12" y2="3" /></svg>
                                            </button>
                                        </div>
                                    </div>
                                    <MermaidRenderer
                                        key={last.architecture.diagram?.content}
                                        code={last.architecture.diagram?.content ?? ""}
                                        containerRef={diagramRef}
                                    />
                                </div>
                            </>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}

function renderAssistantSummary(res) {
    if (res.stage === "intake") {
        const count = res.intake?.questions?.length ?? 0;
        if (count > 0) {
            return `I need ${count} more detail${count > 1 ? "s" : ""} — please select from the options on the right panel.`;
        }
        return "Processing your requirements…";
    }

    if (res.architecture) {
        const rec = res.architecture.recommended?.name ?? "Recommendation";
        const rawRationale = res.architecture.recommended?.rationale;
        let rationale = "";
        if (Array.isArray(rawRationale)) {
            rationale = rawRationale.slice(0, 3).join("; ");
        } else if (typeof rawRationale === "string") {
            rationale = rawRationale;
        }
        return `Architecture ready!\n\nRecommended: ${rec}${rationale ? `\nWhy: ${rationale}` : ""}`;
    }

    return "";
}
