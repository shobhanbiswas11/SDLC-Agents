import { useLayoutEffect, useRef, useState, useCallback } from "react";
import mermaid from "mermaid";

/* ─── One-time global init (at module level, runs once) ─── */
mermaid.initialize({
    startOnLoad: false,
    securityLevel: "loose",
    theme: "default",
    themeVariables: {
        primaryColor: "#f3f4f6",
        primaryTextColor: "#111111",
        primaryBorderColor: "#d1d5db",
        lineColor: "#6b7280",
        secondaryColor: "#f9fafb",
        tertiaryColor: "#e5e7eb",
        background: "#ffffff",
        mainBkg: "#f3f4f6",
        nodeBorder: "#d1d5db",
        clusterBkg: "#f9fafb",
        titleColor: "#111111",
        edgeLabelBackground: "#ffffff",
    },
});

/* ─── Monotonic counter for unique IDs ─── */
let _idCounter = 0;

/* ─── Client-side sanitization ─── */
function sanitize(raw) {
    let s = raw;
    s = s.replace(/^```(?:mermaid|mmd)?\s*\n?/gim, "");
    s = s.replace(/\n?```\s*$/gm, "");
    s = s.replace(/```/g, "").replace(/`/g, "");
    s = s.replace(/&gt;/g, ">").replace(/&lt;/g, "<").replace(/&amp;/g, "&").replace(/&quot;/g, '"');
    s = s.replace(/[\u201c\u201d]/g, '"').replace(/[\u2018\u2019]/g, "'");
    s = s.replace(/\u2014>/g, "-->").replace(/- >/g, "-->");
    s = s.replace(/^(\s*)SubGraph\b/gim, "$1subgraph");
    s = s.replace(
        /^(\s*subgraph[ \t]+)([A-Za-z0-9]\w*(?:[ \t]+\w+)+)[ \t]*$/gm,
        (_match, prefix, label) => {
            if (label.includes("[") || label.includes('"')) return _match;
            const id = label.replace(/[^a-zA-Z0-9]/g, "");
            return `${prefix}${id}["${label.trim()}"]`;
        }
    );
    return s.trim();
}

export function MermaidRenderer({ code, containerRef }) {
    const internalRef = useRef(null);
    const ref = containerRef || internalRef;
    const [status, setStatus] = useState("loading");
    const cleanCode = sanitize(code);

    const doRender = useCallback(async () => {
        const el = ref.current;
        if (!el || !cleanCode) {
            setStatus("error");
            return;
        }

        _idCounter++;
        const id = `mmd${_idCounter}`;

        // Strategy 1: mermaid.render()
        try {
            for (const staleId of [id, `d${id}`]) {
                document.getElementById(staleId)?.remove();
            }
            const { svg } = await mermaid.render(id, cleanCode);
            el.innerHTML = svg;
            setStatus("ok");
            return;
        } catch (e1) {
            console.warn("[Mermaid] render() failed:", e1);
            document.getElementById(id)?.remove();
            document.getElementById(`d${id}`)?.remove();
        }

        // Strategy 2: mermaid.run()
        try {
            el.innerHTML = "";
            const div = document.createElement("div");
            div.className = "mermaid";
            div.id = `run${_idCounter}`;
            div.textContent = cleanCode;
            el.appendChild(div);
            await mermaid.run({ nodes: [div] });
            setStatus("ok");
            return;
        } catch (e2) {
            console.warn("[Mermaid] run() failed:", e2);
        }

        // Strategy 3: innerHTML + mermaid.run()
        try {
            el.innerHTML = `<div class="mermaid">${cleanCode}</div>`;
            await mermaid.run({ nodes: el.querySelectorAll(".mermaid") });
            setStatus("ok");
            return;
        } catch (e3) {
            console.warn("[Mermaid] innerHTML+run() failed:", e3);
        }

        setStatus("error");
    }, [cleanCode]);

    useLayoutEffect(() => {
        let active = true;
        doRender().then(() => {
            if (!active) return;
        });
        return () => {
            active = false;
        };
    }, [doRender]);

    return (
        <div className="diagram-container" style={{ position: "relative", minHeight: 80 }}>
            <div
                ref={ref}
                style={{
                    display: status === "error" ? "none" : "block",
                    minHeight: status === "loading" ? 80 : undefined,
                }}
            />

            {status === "loading" && <div className="loading-spinner" />}

            {status === "error" && (
                <div className="diagram-fallback">
                    <div className="diagram-fallback__notice">
                        ⚠ Diagram couldn't auto-render — showing source code
                    </div>
                    <pre>{cleanCode || code}</pre>
                </div>
            )}
        </div>
    );
}
