import { useMemo } from "react";
import "./DependencyGraph.css";

function TreeNode({ node, depth = 0 }) {
  if (!node) return null;

  return (
    <div className="tree-node" style={{ "--depth": depth }}>
      <div className="tree-node-content">
        <span className="tree-connector">{depth > 0 ? "|-" : "o"}</span>
        <span className="tree-pkg-name">{node.name}</span>
        {node.version && (
          <span className="tree-pkg-version">{node.version}</span>
        )}
      </div>
      {node.children && node.children.length > 0 && (
        <div className="tree-children">
          {node.children.map((child, i) => (
            <TreeNode
              key={`${child.name || child}-${i}`}
              node={typeof child === "string" ? { name: child } : child}
              depth={depth + 1}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export default function DependencyGraph({ data }) {
  const stats = useMemo(() => {
    if (!data) return null;
    const deps = data.dependencies || [];
    const graph = data.graph || {};
    return {
      totalPackages: deps.length,
      totalEdges: (graph.edges || []).length,
      roots: (data.root_dependencies || []).length,
    };
  }, [data]);

  if (!data) {
    return (
      <div className="graph-empty fade-in">
        <div className="empty-icon">DG</div>
        <p>Run a scan to see the dependency graph</p>
      </div>
    );
  }

  const graph = data.graph || {};
  const nodes = graph.nodes || [];
  const edges = graph.edges || [];
  const roots = data.root_dependencies || [];

  // Build adjacency for tree rendering
  const adj = {};
  edges.forEach(({ source, target }) => {
    if (!adj[source]) adj[source] = [];
    adj[source].push(target);
  });

  const nodeMap = {};
  nodes.forEach((n) => {
    nodeMap[n.id] = n;
  });

  function buildTree(id, visited = new Set()) {
    if (visited.has(id))
      return { name: id, version: nodeMap[id]?.version || "", children: [] };
    visited.add(id);
    const children = (adj[id] || []).map((child) => buildTree(child, visited));
    return {
      name: id,
      version: nodeMap[id]?.version || "",
      children,
    };
  }

  return (
    <div className="graph-panel fade-in">
      <div className="graph-header">
        <h2 className="graph-title">
          <span>DG</span> Dependency Graph
        </h2>
        {stats && (
          <div className="graph-stats">
            <span className="stat-badge">
              <span className="stat-num">{stats.totalPackages}</span> packages
            </span>
            <span className="stat-badge">
              <span className="stat-num">{stats.totalEdges}</span> edges
            </span>
            <span className="stat-badge">
              <span className="stat-num">{stats.roots}</span> roots
            </span>
          </div>
        )}
      </div>

      <div className="graph-tree-container">
        {roots.map((root) => (
          <TreeNode key={root} node={buildTree(root)} depth={0} />
        ))}
      </div>

      {/* Tabular view */}
      <div className="graph-table-section">
        <h3 className="section-title">All Resolved Packages</h3>
        <div className="graph-table-wrapper">
          <table className="graph-table">
            <thead>
              <tr>
                <th>Package</th>
                <th>Version</th>
                <th>Ecosystem</th>
                <th>Dependencies</th>
              </tr>
            </thead>
            <tbody>
              {(data.dependencies || []).map((dep, i) => (
                <tr key={`${dep.name}-${i}`}>
                  <td className="pkg-name-cell">{dep.name}</td>
                  <td>
                    <code>{dep.version || "—"}</code>
                  </td>
                  <td>
                    <span className={`eco-badge eco-${dep.ecosystem}`}>
                      {dep.ecosystem}
                    </span>
                  </td>
                  <td className="dep-count">{(dep.children || []).length}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
