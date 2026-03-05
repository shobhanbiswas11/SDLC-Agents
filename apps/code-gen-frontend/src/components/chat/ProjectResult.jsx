import React, { useState } from "react";
import {
    FolderOpen,
    FileText,
    Download,
    ChevronRight,
    ChevronDown,
    Terminal,
    CheckCircle2,
} from "lucide-react";

const API_BASE = "http://localhost:8000";

/* ───────────────────────── helpers ───────────────────────── */

/**
 * Build a nested tree structure from a flat list of file paths.
 * Each node: { name, path, children: [] | null }
 */
function buildTree(paths) {
    const root = { name: "", children: [] };

    for (const p of paths) {
        const parts = p.split("/");
        let current = root;

        parts.forEach((part, i) => {
            const isFile = i === parts.length - 1;
            let child = current.children.find((c) => c.name === part);

            if (!child) {
                child = {
                    name: part,
                    path: isFile ? p : null,
                    children: isFile ? null : [],
                };
                current.children.push(child);
            }
            current = child;
        });
    }

    return root.children;
}

/* ─────────────────── tree node component ─────────────────── */

const TreeNode = ({ node, depth = 0 }) => {
    const [open, setOpen] = useState(depth < 2);
    const isFolder = node.children !== null;

    return (
        <div>
            <div
                className={`flex items-center gap-2 py-1 px-2 rounded-lg cursor-pointer transition-colors
          hover:bg-zinc-700/40 text-sm ${isFolder ? "text-zinc-200 font-medium" : "text-zinc-400"
                    }`}
                style={{ paddingLeft: `${depth * 16 + 8}px` }}
                onClick={() => isFolder && setOpen(!open)}
            >
                {isFolder ? (
                    <>
                        {open ? (
                            <ChevronDown size={14} className="text-zinc-500 flex-shrink-0" />
                        ) : (
                            <ChevronRight size={14} className="text-zinc-500 flex-shrink-0" />
                        )}
                        <FolderOpen size={15} className="text-amber-400 flex-shrink-0" />
                    </>
                ) : (
                    <>
                        <span className="w-[14px]" />
                        <FileText size={15} className="text-blue-400 flex-shrink-0" />
                    </>
                )}
                <span className="truncate">{node.name}</span>
            </div>

            {isFolder && open && (
                <div>
                    {node.children.map((child, i) => (
                        <TreeNode key={i} node={child} depth={depth + 1} />
                    ))}
                </div>
            )}
        </div>
    );
};

/* ───────────────── main result component ──────────────────── */

const ProjectResult = ({ tree, initInstructions, runId }) => {
    const treeNodes = buildTree(tree || []);

    const handleDownload = () => {
        window.open(`${API_BASE}/download/${runId}`, "_blank");
    };

    return (
        <div className="w-full flex justify-start">
            <div className="max-w-3xl w-full space-y-4">
                {/* Success header */}
                <div className="flex items-center gap-3 bg-emerald-500/10 border border-emerald-500/20 rounded-2xl px-5 py-3">
                    <CheckCircle2 size={20} className="text-emerald-400 flex-shrink-0" />
                    <span className="text-emerald-300 font-medium text-sm">
                        Project generated successfully!
                    </span>
                </div>

                {/* Folder tree */}
                {tree && tree.length > 0 && (
                    <div className="bg-zinc-800/60 border border-zinc-700/50 rounded-2xl overflow-hidden">
                        <div className="flex items-center gap-2 px-5 py-3 border-b border-zinc-700/50">
                            <FolderOpen size={16} className="text-amber-400" />
                            <span className="text-zinc-200 text-sm font-semibold">
                                Project Structure
                            </span>
                            <span className="ml-auto text-zinc-500 text-xs">
                                {tree.length} files
                            </span>
                        </div>
                        <div className="px-3 py-2 max-h-72 overflow-y-auto custom-scrollbar">
                            {treeNodes.map((node, i) => (
                                <TreeNode key={i} node={node} />
                            ))}
                        </div>
                    </div>
                )}

                {/* Init instructions */}
                {initInstructions && (
                    <div className="bg-zinc-800/60 border border-zinc-700/50 rounded-2xl overflow-hidden">
                        <div className="flex items-center gap-2 px-5 py-3 border-b border-zinc-700/50">
                            <Terminal size={16} className="text-violet-400" />
                            <span className="text-zinc-200 text-sm font-semibold">
                                Setup Instructions
                            </span>
                        </div>
                        <pre className="px-5 py-4 text-sm text-zinc-300 leading-relaxed whitespace-pre-wrap overflow-x-auto custom-scrollbar max-h-80">
                            {initInstructions}
                        </pre>
                    </div>
                )}

                {/* Download button */}
                {runId && (
                    <button
                        onClick={handleDownload}
                        className="flex items-center gap-2 w-full justify-center px-5 py-3 rounded-2xl
              bg-gradient-to-r from-violet-600 to-indigo-600
              hover:from-violet-500 hover:to-indigo-500
              text-white font-medium text-sm
              transition-all duration-200
              shadow-lg shadow-violet-600/20 hover:shadow-violet-500/30
              active:scale-[0.98]"
                    >
                        <Download size={16} />
                        Download Project ZIP
                    </button>
                )}
            </div>
        </div>
    );
};

export default ProjectResult;
