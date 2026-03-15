import {
  useState,
  useRef,
  useCallback,
  useEffect,
  useMemo,
  lazy,
  Suspense,
} from "react";

const MonacoEditor = lazy(() => import("@monaco-editor/react"));
const ReactDiffViewer = lazy(() => import("react-diff-viewer-continued"));

const LANGUAGES = [
  { key: "python", name: "Python", monacoId: "python" },
  { key: "cpp", name: "C++", monacoId: "cpp" },
  { key: "java", name: "Java", monacoId: "java" },
  { key: "javascript", name: "JavaScript", monacoId: "javascript" },
  { key: "typescript", name: "TypeScript", monacoId: "typescript" },
  { key: "go", name: "Go", monacoId: "go" },
  { key: "rust", name: "Rust", monacoId: "rust" },
];

/* ── Inline SVG Icons (professional, corporate-grade) ── */
const Icons = {
  search: (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <circle cx="11" cy="11" r="8" />
      <line x1="21" y1="21" x2="16.65" y2="16.65" />
    </svg>
  ),
  check: (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <polyline points="20 6 9 17 4 12" />
    </svg>
  ),
  wrench: (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" />
    </svg>
  ),
  alertTriangle: (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
      <line x1="12" y1="9" x2="12" y2="13" />
      <line x1="12" y1="17" x2="12.01" y2="17" />
    </svg>
  ),
  file: (
    <svg
      width="13"
      height="13"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14 2 14 8 20 8" />
    </svg>
  ),
  fileCode: (
    <svg
      width="13"
      height="13"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14 2 14 8 20 8" />
      <polyline points="10 13 8 15.5 10 18" />
      <polyline points="14 13 16 15.5 14 18" />
    </svg>
  ),
  folder: (
    <svg
      width="13"
      height="13"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
    </svg>
  ),
  folderOpen: (
    <svg
      width="13"
      height="13"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M5 19a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2h4l2 2h4a2 2 0 0 1 2 2v1" />
      <path d="M4.5 13h15.2a2 2 0 0 1 1.94 2.5l-1.2 5a2 2 0 0 1-1.94 1.5H4a2 2 0 0 1-2-2v-7" />
    </svg>
  ),
  gitBranch: (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <line x1="6" y1="3" x2="6" y2="15" />
      <circle cx="18" cy="6" r="3" />
      <circle cx="6" cy="18" r="3" />
      <path d="M18 9a9 9 0 0 1-9 9" />
    </svg>
  ),
  code: (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <polyline points="16 18 22 12 16 6" />
      <polyline points="8 6 2 12 8 18" />
    </svg>
  ),
  x: (
    <svg
      width="12"
      height="12"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <line x1="18" y1="6" x2="6" y2="18" />
      <line x1="6" y1="6" x2="18" y2="18" />
    </svg>
  ),
  chevronDown: (
    <svg
      width="12"
      height="12"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <polyline points="6 9 12 15 18 9" />
    </svg>
  ),
  chevronRight: (
    <svg
      width="12"
      height="12"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <polyline points="9 18 15 12 9 6" />
    </svg>
  ),
  circleError: (
    <svg
      width="12"
      height="12"
      viewBox="0 0 24 24"
      fill="#ef4444"
      stroke="none"
    >
      <circle cx="12" cy="12" r="10" />
      <line
        x1="8"
        y1="8"
        x2="16"
        y2="16"
        stroke="#fff"
        strokeWidth="2.5"
        strokeLinecap="round"
      />
      <line
        x1="16"
        y1="8"
        x2="8"
        y2="16"
        stroke="#fff"
        strokeWidth="2.5"
        strokeLinecap="round"
      />
    </svg>
  ),
  circleWarn: (
    <svg
      width="12"
      height="12"
      viewBox="0 0 24 24"
      fill="#eab308"
      stroke="none"
    >
      <circle cx="12" cy="12" r="10" />
      <line
        x1="12"
        y1="8"
        x2="12"
        y2="13"
        stroke="#fff"
        strokeWidth="2.5"
        strokeLinecap="round"
      />
      <circle cx="12" cy="16.5" r="1.2" fill="#fff" />
    </svg>
  ),
  circleInfo: (
    <svg
      width="12"
      height="12"
      viewBox="0 0 24 24"
      fill="#3b82f6"
      stroke="none"
    >
      <circle cx="12" cy="12" r="10" />
      <line
        x1="12"
        y1="11"
        x2="12"
        y2="17"
        stroke="#fff"
        strokeWidth="2.5"
        strokeLinecap="round"
      />
      <circle cx="12" cy="7.5" r="1.2" fill="#fff" />
    </svg>
  ),
  checkCircle: (
    <svg
      width="40"
      height="40"
      viewBox="0 0 24 24"
      fill="none"
      stroke="#22c55e"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
      <polyline points="22 4 12 14.01 9 11.01" />
    </svg>
  ),
  searchLg: (
    <svg
      width="40"
      height="40"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <circle cx="11" cy="11" r="8" />
      <line x1="21" y1="21" x2="16.65" y2="16.65" />
    </svg>
  ),
  sidebar: (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
      <line x1="9" y1="3" x2="9" y2="21" />
    </svg>
  ),
};

const SAMPLE_CODE = {
  python: `import os\nimport sys\nimport json\nimport os\n\ndef calculate_sum(x,y):\n    result=x+y\n    return result\n\nclass myClass:\n    def __init__(self,name):\n        self.name=name\n    \n    def get_name( self ):\n        return self.name\n\nunused_var = 42\n\ndef process_data(data=[]):\n    for i in range(len(data)):\n        if data[i] == None:\n            print("Found none")\n    return data\n`,
  cpp: `#include <iostream>\n#include <vector>\nusing namespace std;\n\nclass myClass {\npublic:\n    int x;\n    myClass(int val) { x = val; }\n    ~myClass() {}\n};\n\nint main() {\n    int* ptr = new int(10);\n    int unused = 5;\n    myClass* obj = new myClass(42);\n    vector<int> nums = {1, 2, 3};\n    for(int i=0; i<nums.size(); i++) {\n        cout << nums[i] << endl;\n    }\n    if(ptr != NULL) {\n        cout << *ptr << endl;\n    }\n    return 0;\n}\n`,
  java: `import java.util.*;\nimport java.io.*;\nimport java.util.ArrayList;\n\npublic class DataProcessor {\n    ArrayList data = new ArrayList();\n    public void processData(String input) {\n        if(input == "test") {\n            System.out.println("Test mode");\n        }\n        try {\n            int result = Integer.parseInt(input);\n        } catch(Exception e) {\n        }\n    }\n}\n`,
  javascript: `var data = [1, 2, 3];\nvar unused = "hello";\n\nfunction processData(items) {\n    for (var i = 0; i < items.length; i++) {\n        if (items[i] == null) {\n            console.log("Found null at " + i);\n        }\n    }\n    eval("console.log('done')");\n    return items;\n}\n`,
  typescript: `let data: any = [1, 2, 3];\nlet unused: string = "hello";\n\nfunction processData(items: any[]): any {\n    var result: any[] = [];\n    for (let i = 0; i < items.length; i++) {\n        if (items[i] == null) {\n            console.log("null at " + i);\n        }\n        result.push(items[i]! * 2);\n    }\n    return result;\n}\n`,
  go: `package main\n\nimport (\n\t"fmt"\n\t"os"\n)\n\nfunc processData(data []string) {\n\tfor i := 0; i < len(data); i++ {\n\t\tfmt.Println(data[i])\n\t}\n\tresult, _ := os.Open("test.txt")\n\tfmt.Println(result)\n}\n\nfunc main() {\n\tdata := []string{"hello", "world"}\n\tprocessData(data)\n}\n`,
  rust: `use std::collections::HashMap;\n\nfn process_data(data: Vec<i32>) -> Vec<i32> {\n    let mut result: Vec<i32> = Vec::new();\n    for i in 0..data.len() {\n        let val = data[i].clone();\n        result.push(val);\n    }\n    let unused = 42;\n    return result;\n}\n\nfn main() {\n    let data = vec![1, 2, 3, 4, 5];\n    let result = process_data(data);\n    println!("{:?}", result);\n    let map = HashMap::new();\n    let val = map.get("key").unwrap();\n}\n`,
};

const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000"
).replace(/\/$/, "");

/* ── Build nested tree from flat paths ──── */
function buildFileTree(files) {
  const tree = {};
  for (const path of Object.keys(files).sort()) {
    const parts = path.split("/");
    let node = tree;
    for (let i = 0; i < parts.length; i++) {
      const part = parts[i];
      if (i === parts.length - 1) {
        node[part] = {
          __file: true,
          __path: path,
          __lang: files[path].language,
        };
      } else {
        if (!node[part]) node[part] = {};
        node = node[part];
      }
    }
  }
  return tree;
}

/* ── Recursive tree node component ───────── */
function TreeNode({ name, node, depth, onFileClick, activeFile }) {
  const [open, setOpen] = useState(depth < 2);

  if (node.__file) {
    const isActive = activeFile === node.__path;
    return (
      <div
        className={`tree-file ${isActive ? "active" : ""}`}
        style={{ paddingLeft: 12 + depth * 16 }}
        onClick={() => onFileClick(node.__path)}
        title={node.__path}
      >
        <span className="tree-file-icon">{Icons.fileCode}</span>
        <span className="tree-file-name">{name}</span>
      </div>
    );
  }

  const entries = Object.entries(node).sort(([, a], [, b]) => {
    const aDir = !a.__file;
    const bDir = !b.__file;
    if (aDir !== bDir) return aDir ? -1 : 1;
    return 0;
  });

  return (
    <div className="tree-folder">
      <div
        className="tree-folder-header"
        style={{ paddingLeft: 12 + depth * 16 }}
        onClick={() => setOpen((p) => !p)}
      >
        <span className="tree-folder-arrow">
          {open ? Icons.chevronDown : Icons.chevronRight}
        </span>
        <span className="tree-folder-icon">
          {open ? Icons.folderOpen : Icons.folder}
        </span>
        <span className="tree-folder-name">{name}</span>
      </div>
      {open &&
        entries.map(([childName, childNode]) => (
          <TreeNode
            key={childName}
            name={childName}
            node={childNode}
            depth={depth + 1}
            onFileClick={onFileClick}
            activeFile={activeFile}
          />
        ))}
    </div>
  );
}

function LiveEditor() {
  const [language, setLanguage] = useState("python");
  const [code, setCode] = useState(SAMPLE_CODE.python);
  const [analyzing, setAnalyzing] = useState(false);
  const [fixing, setFixing] = useState(false);
  const [violations, setViolations] = useState(null);
  const [summary, setSummary] = useState(null);
  const [fixResult, setFixResult] = useState(null);
  const [expandedViolation, setExpandedViolation] = useState({});
  const [showDiff, setShowDiff] = useState(false);
  const debounceRef = useRef(null);
  const [autoAnalyze, setAutoAnalyze] = useState(false);

  // ── Repo browser state ────────────────────
  const [repoUrl, setRepoUrl] = useState("");
  const [repoLoading, setRepoLoading] = useState(false);
  const [repoFiles, setRepoFiles] = useState(null);
  const [activeRepoFile, setActiveRepoFile] = useState(null);
  const [showFileTree, setShowFileTree] = useState(true);
  const [fileSearchQuery, setFileSearchQuery] = useState("");

  // ── Branch state ──────────────────────────
  const [branches, setBranches] = useState([]);
  const [selectedBranch, setSelectedBranch] = useState("");
  const [branchesLoading, setBranchesLoading] = useState(false);
  const [showBranchDropdown, setShowBranchDropdown] = useState(false);
  const branchDropdownRef = useRef(null);

  // Auto-analyze on code/language change (debounced)
  useEffect(() => {
    if (!autoAnalyze || !code.trim()) return;
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      runAnalysis();
    }, 1500);
    return () => clearTimeout(debounceRef.current);
  }, [code, language, autoAnalyze]);

  const runAnalysis = useCallback(async () => {
    if (!code.trim()) return;
    setAnalyzing(true);
    setFixResult(null);
    setShowDiff(false);
    try {
      const res = await fetch(`${API_BASE_URL}/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code, language }),
      });
      const data = await res.json();
      if (!res.ok) {
        alert(data.detail || "Analysis failed");
        return;
      }
      setViolations(data.violations || []);
      setSummary(data.summary || null);
    } catch (e) {
      alert("Analysis failed: " + e.message);
    } finally {
      setAnalyzing(false);
    }
  }, [code, language]);

  const runFixAll = useCallback(async () => {
    if (!code.trim() || !violations?.length) return;
    setFixing(true);
    try {
      const res = await fetch(`${API_BASE_URL}/fix`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code, language, violations }),
      });
      const data = await res.json();
      if (!res.ok) {
        alert(data.detail || "Fix failed");
        return;
      }
      setFixResult(data);
      setShowDiff(true);
    } catch (e) {
      alert("Fix failed: " + e.message);
    } finally {
      setFixing(false);
    }
  }, [code, language, violations]);

  const applyFix = useCallback(() => {
    if (fixResult?.fixed_code) {
      setCode(fixResult.fixed_code);
      setViolations([]);
      setSummary(null);
      setFixResult(null);
      setShowDiff(false);
    }
  }, [fixResult]);

  const handleLanguageChange = (newLang) => {
    setLanguage(newLang);
    if (!repoFiles) {
      setCode(SAMPLE_CODE[newLang] || "");
    }
    setViolations(null);
    setSummary(null);
    setFixResult(null);
    setShowDiff(false);
  };

  // ── Fetch branches for a repo ─────────────
  const fetchBranches = useCallback(async (url) => {
    if (!url || (!url.startsWith("http") && !url.startsWith("git@"))) return;
    setBranchesLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/repo-branches`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ repo_url: url }),
      });
      const data = await res.json();
      if (res.ok && data.branches) {
        setBranches(data.branches);
        // Auto-select the first branch (usually main/master) if none selected
        if (!selectedBranch && data.branches.length > 0) {
          setSelectedBranch(data.branches[0].name);
        }
      }
    } catch (e) {
      console.warn("Failed to fetch branches:", e.message);
    } finally {
      setBranchesLoading(false);
    }
  }, [selectedBranch]);

  // Close branch dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (branchDropdownRef.current && !branchDropdownRef.current.contains(e.target)) {
        setShowBranchDropdown(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // ── Repo clone + file load ────────────────
  const loadRepo = useCallback(async (branchOverride) => {
    if (!repoUrl.trim())
      return alert("Please enter a repository URL or local path");
    setRepoLoading(true);
    setRepoFiles(null);
    setActiveRepoFile(null);
    try {
      const isUrl = repoUrl.startsWith("http") || repoUrl.startsWith("git@");
      const payload = isUrl ? { repo_url: repoUrl } : { local_path: repoUrl };

      // Add branch if specified
      const branch = branchOverride || selectedBranch;
      if (branch && isUrl) {
        payload.branch = branch;
      }

      const res = await fetch(`${API_BASE_URL}/repo-files`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok) {
        alert(data.detail || "Failed to load repository");
        return;
      }
      if (data.total_files === 0) {
        alert("No supported source files found in this repository.");
        return;
      }
      setRepoFiles(data.files);
      setShowFileTree(true);

      // Fetch branches if we haven't yet
      if (branches.length === 0 && isUrl) {
        fetchBranches(repoUrl);
      }

      const firstPath = Object.keys(data.files).sort()[0];
      if (firstPath) openRepoFile(firstPath, data.files);
    } catch (e) {
      alert("Failed to load repo: " + e.message);
    } finally {
      setRepoLoading(false);
    }
  }, [repoUrl, selectedBranch, branches.length, fetchBranches]);

  const switchBranch = useCallback((branchName) => {
    setSelectedBranch(branchName);
    setShowBranchDropdown(false);
    // Immediately reload the repo with the new branch
    loadRepo(branchName);
  }, [loadRepo]);

  const openRepoFile = useCallback(
    (path, filesOverride) => {
      const files = filesOverride || repoFiles;
      if (!files || !files[path]) return;
      const file = files[path];
      setActiveRepoFile(path);
      setCode(file.content);
      setLanguage(file.language || "python");
      setViolations(null);
      setSummary(null);
      setFixResult(null);
      setShowDiff(false);
      setExpandedViolation({});
    },
    [repoFiles],
  );

  const closeRepo = useCallback(() => {
    setRepoFiles(null);
    setActiveRepoFile(null);
    setCode(SAMPLE_CODE[language] || "");
    setViolations(null);
    setSummary(null);
    setBranches([]);
    setSelectedBranch("");
    setShowBranchDropdown(false);
  }, [language]);

  // ── File tree ────────────────────────────
  const fileTree = useMemo(() => {
    if (!repoFiles) return null;
    return buildFileTree(repoFiles);
  }, [repoFiles]);

  const filteredFileList = useMemo(() => {
    if (!repoFiles || !fileSearchQuery.trim()) return null;
    const q = fileSearchQuery.toLowerCase();
    return Object.keys(repoFiles)
      .filter((p) => p.toLowerCase().includes(q))
      .sort();
  }, [repoFiles, fileSearchQuery]);

  const fileCount = repoFiles ? Object.keys(repoFiles).length : 0;

  const getSeverityIcon = (sev) => {
    if (sev === "error") return Icons.circleError;
    if (sev === "warning") return Icons.circleWarn;
    return Icons.circleInfo;
  };

  const getSeverityClass = (sev) => {
    if (sev === "error") return "severity-error";
    if (sev === "warning") return "severity-high";
    return "severity-medium";
  };

  return (
    <div className="live-editor-container">
      {/* ── Repo URL Bar ───────────────────── */}
      <div className="repo-url-bar">
        <div className="repo-url-input-wrap">
          <span className="repo-url-icon">{Icons.gitBranch}</span>
          <input
            className="repo-url-input"
            placeholder="Paste GitHub URL or local path to load files into editor…"
            value={repoUrl}
            onChange={(e) => setRepoUrl(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && loadRepo()}
          />
          {repoFiles && (
            <button
              className="repo-close-btn"
              onClick={closeRepo}
              title="Close repo"
            >
              {Icons.x}
            </button>
          )}
        </div>

        {/* ── Branch Selector ─────────────── */}
        {(repoFiles || branches.length > 0) && (
          <div className="branch-selector" ref={branchDropdownRef}>
            <button
              className="branch-selector-btn"
              onClick={() => {
                if (branches.length === 0 && !branchesLoading) {
                  fetchBranches(repoUrl);
                }
                setShowBranchDropdown((p) => !p);
              }}
              disabled={branchesLoading}
              title="Select branch"
            >
              {Icons.gitBranch}
              <span className="branch-name">
                {branchesLoading
                  ? "Loading…"
                  : selectedBranch || "branch"}
              </span>
              {Icons.chevronDown}
            </button>
            {showBranchDropdown && (
              <div className="branch-dropdown">
                <div className="branch-dropdown-header">Switch branch</div>
                {branchesLoading ? (
                  <div className="branch-dropdown-loading">
                    <span className="spinner" /> Fetching branches…
                  </div>
                ) : branches.length === 0 ? (
                  <div className="branch-dropdown-empty">No branches found</div>
                ) : (
                  <div className="branch-dropdown-list">
                    {branches.map((b) => (
                      <button
                        key={b.name}
                        className={`branch-dropdown-item ${
                          selectedBranch === b.name ? "active" : ""
                        }`}
                        onClick={() => switchBranch(b.name)}
                      >
                        <span className="branch-item-icon">
                          {selectedBranch === b.name
                            ? Icons.check
                            : Icons.gitBranch}
                        </span>
                        <span className="branch-item-name">{b.name}</span>
                        <span className="branch-item-sha">{b.sha}</span>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        <button
          className="repo-load-btn"
          onClick={() => loadRepo()}
          disabled={repoLoading || !repoUrl.trim()}
        >
          {repoLoading && <span className="spinner" />}
          {repoLoading ? "Cloning…" : "Load Repo"}
        </button>
      </div>

      {/* ── Toolbar ─────────────────────── */}
      <div className="editor-toolbar">
        <div className="toolbar-left">
          <div className="lang-selector">
            <label>Language</label>
            <select
              value={language}
              onChange={(e) => handleLanguageChange(e.target.value)}
            >
              {LANGUAGES.map((l) => (
                <option key={l.key} value={l.key}>
                  {l.name}
                </option>
              ))}
            </select>
          </div>
          <div className="auto-toggle">
            <label className="toggle-label">
              <input
                type="checkbox"
                checked={autoAnalyze}
                onChange={(e) => setAutoAnalyze(e.target.checked)}
              />
              <span className="toggle-slider" />
              Auto-analyze
            </label>
          </div>
          {activeRepoFile && (
            <span className="active-file-badge" title={activeRepoFile}>
              {Icons.fileCode}
              <span>{activeRepoFile.split("/").pop()}</span>
            </span>
          )}
        </div>
        <div className="toolbar-right">
          <button
            className="analyze-btn"
            onClick={runAnalysis}
            disabled={analyzing || !code.trim()}
          >
            {analyzing ? <span className="spinner" /> : Icons.search}
            {analyzing ? "Analyzing…" : "Analyze"}
          </button>
          {violations?.length > 0 && (
            <button
              className="fix-all-btn"
              onClick={runFixAll}
              disabled={fixing}
            >
              {fixing ? <span className="spinner" /> : Icons.wrench}
              {fixing ? "Fixing…" : "Fix All"}
            </button>
          )}
        </div>
      </div>

      {/* ── Summary Bar ─────────────────── */}
      {summary && (
        <div className="analysis-summary">
          <div className="summary-stats">
            <div
              className={`summary-quality quality-${summary.overall_quality || "unknown"}`}
            >
              {(summary.overall_quality || "analyzed").toUpperCase()}
            </div>
            <div className="summary-counts">
              <span className="stat-error">
                {summary.by_severity?.error || 0} errors
              </span>
              <span className="stat-warning">
                {summary.by_severity?.warning || 0} warnings
              </span>
              <span className="stat-info">
                {summary.by_severity?.info || 0} info
              </span>
            </div>
            <span className="summary-total">
              {summary.total_violations || 0} total
            </span>
          </div>
          {summary.top_issues?.length > 0 && (
            <div className="top-issues">
              {summary.top_issues.map((issue, i) => (
                <span key={i} className="issue-chip">
                  {issue}
                </span>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── Main Layout: [File Tree] | Editor | Violations ── */}
      <div className={`editor-main-layout ${repoFiles ? "with-tree" : ""}`}>
        {/* File Tree Sidebar */}
        {repoFiles && showFileTree && (
          <div className="file-tree-pane">
            <div className="pane-header">
              <span className="pane-title">
                {Icons.folder}
                <span>Files ({fileCount})</span>
              </span>
              <button
                className="tree-collapse-btn"
                onClick={() => setShowFileTree(false)}
                title="Hide file tree"
              >
                {Icons.x}
              </button>
            </div>
            <div className="tree-search">
              <input
                className="tree-search-input"
                placeholder="Search files…"
                value={fileSearchQuery}
                onChange={(e) => setFileSearchQuery(e.target.value)}
              />
            </div>
            <div className="tree-scroll">
              {fileSearchQuery.trim() && filteredFileList ? (
                filteredFileList.length === 0 ? (
                  <div className="tree-empty">No files match</div>
                ) : (
                  filteredFileList.map((path) => (
                    <div
                      key={path}
                      className={`tree-file ${activeRepoFile === path ? "active" : ""}`}
                      style={{ paddingLeft: 12 }}
                      onClick={() => openRepoFile(path)}
                      title={path}
                    >
                      <span className="tree-file-icon">{Icons.fileCode}</span>
                      <span className="tree-file-name">{path}</span>
                    </div>
                  ))
                )
              ) : (
                fileTree &&
                Object.entries(fileTree)
                  .sort(([, a], [, b]) => {
                    const aDir = !a.__file;
                    const bDir = !b.__file;
                    if (aDir !== bDir) return aDir ? -1 : 1;
                    return 0;
                  })
                  .map(([name, node]) => (
                    <TreeNode
                      key={name}
                      name={name}
                      node={node}
                      depth={0}
                      onFileClick={openRepoFile}
                      activeFile={activeRepoFile}
                    />
                  ))
              )}
            </div>
          </div>
        )}

        {/* Show file tree toggle when hidden */}
        {repoFiles && !showFileTree && (
          <button
            className="tree-show-btn"
            onClick={() => setShowFileTree(true)}
            title="Show file tree"
          >
            {Icons.sidebar}
          </button>
        )}

        {/* Editor + Violations split */}
        <div className="editor-split">
          {/* Left: Code Editor */}
          <div className="editor-pane">
            <div className="pane-header">
              <span className="pane-title">
                {Icons.code}
                <span>{activeRepoFile ? activeRepoFile : "Code Editor"}</span>
              </span>
              <span className="char-count">
                {code.length} chars · {code.split("\n").length} lines
              </span>
            </div>
            <div className="monaco-wrapper">
              <Suspense
                fallback={
                  <div className="editor-loading">
                    <span className="spinner" /> Loading editor…
                  </div>
                }
              >
                <MonacoEditor
                  height="100%"
                  language={
                    LANGUAGES.find((l) => l.key === language)?.monacoId ||
                    "plaintext"
                  }
                  value={code}
                  onChange={(val) => setCode(val || "")}
                  theme="vs-dark"
                  options={{
                    fontSize: 14,
                    fontFamily:
                      "'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace",
                    minimap: { enabled: true },
                    scrollBeyondLastLine: false,
                    lineNumbers: "on",
                    renderLineHighlight: "all",
                    bracketPairColorization: { enabled: true },
                    formatOnPaste: true,
                    suggestOnTriggerCharacters: true,
                    wordWrap: "on",
                    padding: { top: 12 },
                  }}
                />
              </Suspense>
            </div>
          </div>

          {/* Right: Violations Panel */}
          <div className="violations-pane">
            <div className="pane-header">
              <span className="pane-title">
                {Icons.alertTriangle}
                <span>
                  {violations
                    ? `${violations.length} Violations`
                    : "Violations"}
                </span>
              </span>
            </div>
            <div className="violations-scroll">
              {!violations && !analyzing && (
                <div className="empty-state">
                  <div className="empty-icon">{Icons.searchLg}</div>
                  <p>
                    Click <strong>Analyze</strong> or enable{" "}
                    <strong>Auto-analyze</strong> to find violations.
                  </p>
                  <p className="empty-hint">
                    Supports Python, C++, Java, JS/TS, Go, Rust
                  </p>
                </div>
              )}
              {analyzing && (
                <div className="analyzing-state">
                  <span className="spinner large" />
                  <p>AI Agent is analyzing your code…</p>
                </div>
              )}
              {violations?.length === 0 && !analyzing && (
                <div className="clean-state">
                  <div className="clean-icon">{Icons.checkCircle}</div>
                  <p>No violations found — code is clean!</p>
                </div>
              )}
              {violations?.map((v, i) => (
                <div
                  key={i}
                  className={`violation-item ${expandedViolation[i] ? "expanded" : ""}`}
                >
                  <div
                    className="violation-item-header"
                    onClick={() =>
                      setExpandedViolation((prev) => ({
                        ...prev,
                        [i]: !prev[i],
                      }))
                    }
                  >
                    <span className="v-icon">
                      {getSeverityIcon(v.severity)}
                    </span>
                    <span className={`v-badge ${getSeverityClass(v.severity)}`}>
                      {v.rule_code}
                    </span>
                    <span className="v-line">L{v.line}</span>
                    <span className="v-msg">{v.message}</span>
                    <span className="expand-icon">
                      {expandedViolation[i]
                        ? Icons.chevronDown
                        : Icons.chevronRight}
                    </span>
                  </div>
                  {expandedViolation[i] && (
                    <div className="violation-item-body">
                      <div className="v-detail">
                        <span className="v-label">Standard</span>
                        <span className="v-value">{v.rule_standard}</span>
                      </div>
                      <div className="v-detail">
                        <span className="v-label">Explanation</span>
                        <span className="v-value">{v.explanation}</span>
                      </div>
                      {v.original_code && (
                        <div className="v-code-block">
                          <div className="v-code-label">Original</div>
                          <pre>{v.original_code}</pre>
                        </div>
                      )}
                      {v.suggested_code && (
                        <div className="v-code-block fixed">
                          <div className="v-code-label">Suggested Fix</div>
                          <pre>{v.suggested_code}</pre>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* ── Diff View (when fix is generated) ── */}
      {showDiff && fixResult && (
        <div className="fix-diff-section">
          <div className="fix-diff-header">
            <h3>{Icons.wrench} AI-Generated Fix</h3>
            <div className="fix-actions">
              <button className="apply-fix-btn" onClick={applyFix}>
                {Icons.check} Apply Fix
              </button>
              <button
                className="dismiss-btn"
                onClick={() => setShowDiff(false)}
              >
                {Icons.x} Dismiss
              </button>
            </div>
          </div>
          {fixResult.explanation && (
            <div className="fix-explanation">
              <strong>Changes:</strong> {fixResult.explanation}
            </div>
          )}
          <div className="diff-wrapper">
            <Suspense
              fallback={
                <div className="diff-loading">
                  <span className="spinner" /> Loading diff…
                </div>
              }
            >
              <ReactDiffViewer
                oldValue={code}
                newValue={fixResult.fixed_code}
                splitView
                useDarkTheme
              />
            </Suspense>
          </div>
        </div>
      )}
    </div>
  );
}

export default LiveEditor;
