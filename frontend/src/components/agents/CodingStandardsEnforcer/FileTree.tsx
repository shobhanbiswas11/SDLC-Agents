'use client';

import { useState } from 'react';
import { Icons } from './icons';

interface FileNode {
  __file?: boolean;
  __path?: string;
  __lang?: string;
  [key: string]: any;
}

export type Tree = Record<string, FileNode>;

export function buildFileTree(
  files: Record<string, { language: string }>,
): Tree {
  const tree: Tree = {};
  for (const path of Object.keys(files).sort()) {
    const parts = path.split('/');
    let node: Tree = tree;
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
        node = node[part] as Tree;
      }
    }
  }
  return tree;
}

interface TreeNodeProps {
  name: string;
  node: FileNode;
  depth: number;
  onFileClick: (path: string) => void;
  activeFile: string | null;
}

export function TreeNode({
  name,
  node,
  depth,
  onFileClick,
  activeFile,
}: TreeNodeProps) {
  const [open, setOpen] = useState(depth < 2);

  if (node.__file) {
    const isActive = activeFile === node.__path;
    return (
      <div
        className={`tree-file ${isActive ? 'active' : ''}`}
        style={{ paddingLeft: 12 + depth * 16 }}
        onClick={() => onFileClick(node.__path as string)}
        title={node.__path}
      >
        <span className="tree-file-icon">{Icons.fileCode}</span>
        <span className="tree-file-name">{name}</span>
      </div>
    );
  }

  const entries = Object.entries(node).sort(([, a], [, b]) => {
    const aDir = !(a as FileNode).__file;
    const bDir = !(b as FileNode).__file;
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
            node={childNode as FileNode}
            depth={depth + 1}
            onFileClick={onFileClick}
            activeFile={activeFile}
          />
        ))}
    </div>
  );
}
