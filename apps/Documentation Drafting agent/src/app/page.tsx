// // 'use client';
// // import { useState, useEffect, useRef } from "react";
// // import ReactMarkdown from 'react-markdown';
// // import remarkGfm from 'remark-gfm';
// // import { Copy, Download, RefreshCw, Zap, Github, FolderOpen, ChevronRight, Check, X, AlertCircle } from "lucide-react";

// // /* ─── GLOBAL STYLES ─────────────────────────────────────────────────────── */
// // const STYLES = `
// // @import url('https://fonts.googleapis.com/css2?family=Unbounded:wght@400;600;700;900&family=IBM+Plex+Mono:wght@300;400;500;600&family=Instrument+Serif:ital@0;1&display=swap');

// // *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

// // :root {
// //   --bg:        #07070f;
// //   --bg2:       #0c0c18;
// //   --surface:   rgba(255,255,255,0.028);
// //   --surface2:  rgba(255,255,255,0.04);
// //   --surface3:  rgba(255,255,255,0.065);
// //   --border:    rgba(255,255,255,0.07);
// //   --border2:   rgba(255,255,255,0.13);

// //   --violet:    #7c6cf8;
// //   --violet-d:  #5b4fd8;
// //   --mint:      #00e8a2;
// //   --mint-d:    #00b87e;
// //   --amber:     #f5a623;
// //   --rose:      #ff4f72;
// //   --sky:       #38bdf8;

// //   --text:      #e8eaf6;
// //   --text2:     #9094b8;
// //   --text3:     #5a5e82;

// //   --radius:    14px;
// //   --radius-sm: 8px;
// //   --font-display: 'Unbounded', sans-serif;
// //   --font-mono:    'IBM Plex Mono', monospace;
// //   --font-serif:   'Instrument Serif', serif;

// //   --glow-violet: 0 0 40px rgba(124,108,248,0.18);
// //   --glow-mint:   0 0 40px rgba(0,232,162,0.15);
// // }

// // body {
// //   background: var(--bg);
// //   color: var(--text);
// //   font-family: var(--font-mono);
// //   -webkit-font-smoothing: antialiased;
// // }

// // /* ── SCROLLBAR ── */
// // ::-webkit-scrollbar { width: 4px; height: 4px; }
// // ::-webkit-scrollbar-track { background: transparent; }
// // ::-webkit-scrollbar-thumb { background: var(--border2); border-radius: 99px; }

// // /* ── ROOT ── */
// // .dg-root {
// //   min-height: 100vh;
// //   background: var(--bg);
// //   position: relative;
// //   overflow-x: hidden;
// // }

// // /* ── AURORA BACKGROUND ── */
// // .dg-aurora {
// //   position: fixed; inset: 0; z-index: 0; pointer-events: none;
// //   overflow: hidden;
// // }

// // .dg-aurora-blob {
// //   position: absolute;
// //   border-radius: 50%;
// //   filter: blur(90px);
// //   opacity: 0;
// //   animation: auroraFloat 18s ease-in-out infinite;
// // }

// // .dg-aurora-blob:nth-child(1) {
// //   width: 600px; height: 600px;
// //   background: radial-gradient(circle, rgba(124,108,248,0.25), transparent 70%);
// //   top: -200px; left: -100px;
// //   animation-delay: 0s;
// //   opacity: 0.5;
// // }

// // .dg-aurora-blob:nth-child(2) {
// //   width: 500px; height: 500px;
// //   background: radial-gradient(circle, rgba(0,232,162,0.2), transparent 70%);
// //   top: 30%; right: -150px;
// //   animation-delay: -6s;
// //   opacity: 0.4;
// // }

// // .dg-aurora-blob:nth-child(3) {
// //   width: 400px; height: 400px;
// //   background: radial-gradient(circle, rgba(245,166,35,0.15), transparent 70%);
// //   bottom: -100px; left: 40%;
// //   animation-delay: -12s;
// //   opacity: 0.3;
// // }

// // @keyframes auroraFloat {
// //   0%, 100% { transform: translate(0, 0) scale(1); }
// //   33%       { transform: translate(30px, -40px) scale(1.08); }
// //   66%       { transform: translate(-20px, 20px) scale(0.95); }
// // }

// // /* ── GRID OVERLAY ── */
// // .dg-grid {
// //   position: fixed; inset: 0; z-index: 0; pointer-events: none;
// //   background-image:
// //     linear-gradient(rgba(255,255,255,0.022) 1px, transparent 1px),
// //     linear-gradient(90deg, rgba(255,255,255,0.022) 1px, transparent 1px);
// //   background-size: 48px 48px;
// //   mask-image: radial-gradient(ellipse 80% 80% at 50% 50%, black 30%, transparent 100%);
// // }

// // /* ── LAYOUT ── */
// // .dg-wrapper {
// //   position: relative; z-index: 1;
// //   max-width: 1280px;
// //   margin: 0 auto;
// //   padding: 0 24px 80px;
// // }

// // /* ── HEADER ── */
// // .dg-header {
// //   display: flex;
// //   align-items: center;
// //   justify-content: space-between;
// //   padding: 28px 0 60px;
// // }

// // .dg-brand {
// //   display: flex; align-items: center; gap: 14px;
// // }

// // .dg-brand-mark {
// //   width: 44px; height: 44px;
// //   border-radius: 12px;
// //   background: linear-gradient(135deg, var(--violet), var(--mint));
// //   display: flex; align-items: center; justify-content: center;
// //   box-shadow: 0 0 30px rgba(124,108,248,0.4), 0 0 60px rgba(0,232,162,0.15);
// //   position: relative;
// //   overflow: hidden;
// // }

// // .dg-brand-mark::after {
// //   content: '';
// //   position: absolute; inset: 1px;
// //   background: linear-gradient(135deg, rgba(255,255,255,0.15), transparent);
// //   border-radius: 11px;
// // }

// // .dg-brand-name {
// //   font-family: var(--font-display);
// //   font-size: 20px; font-weight: 700;
// //   letter-spacing: -0.5px;
// //   background: linear-gradient(135deg, #fff 30%, var(--violet) 100%);
// //   -webkit-background-clip: text; -webkit-text-fill-color: transparent;
// //   background-clip: text;
// // }

// // .dg-brand-tag {
// //   font-family: var(--font-mono);
// //   font-size: 10px; color: var(--text3);
// //   letter-spacing: 2px; text-transform: uppercase;
// //   margin-top: 1px;
// // }

// // .dg-status-pill {
// //   display: flex; align-items: center; gap: 8px;
// //   background: rgba(0,232,162,0.07);
// //   border: 1px solid rgba(0,232,162,0.2);
// //   color: var(--mint);
// //   font-family: var(--font-mono);
// //   font-size: 11px; letter-spacing: 1.5px;
// //   padding: 6px 14px 6px 10px;
// //   border-radius: 99px;
// // }

// // .dg-status-dot {
// //   width: 7px; height: 7px;
// //   background: var(--mint);
// //   border-radius: 50%;
// //   animation: pulse 2s ease-in-out infinite;
// //   box-shadow: 0 0 8px var(--mint);
// // }

// // @keyframes pulse {
// //   0%, 100% { opacity: 1; transform: scale(1); }
// //   50%       { opacity: 0.6; transform: scale(0.8); }
// // }

// // /* ── HERO ── */
// // .dg-hero {
// //   text-align: center;
// //   padding: 0 20px 64px;
// // }

// // .dg-eyebrow {
// //   display: inline-flex; align-items: center; gap: 8px;
// //   background: var(--surface2);
// //   border: 1px solid var(--border2);
// //   border-radius: 99px;
// //   padding: 6px 16px;
// //   font-family: var(--font-mono);
// //   font-size: 11px; color: var(--text2);
// //   letter-spacing: 2px; text-transform: uppercase;
// //   margin-bottom: 24px;
// // }

// // .dg-hero-title {
// //   font-family: var(--font-display);
// //   font-size: clamp(38px, 7vw, 72px);
// //   font-weight: 900;
// //   letter-spacing: -2px;
// //   line-height: 0.95;
// //   margin-bottom: 24px;
// // }

// // .dg-hero-title .line1 {
// //   display: block; color: #fff;
// // }

// // .dg-hero-title .line2 {
// //   display: block;
// //   background: linear-gradient(135deg, var(--violet) 0%, var(--mint) 50%, var(--sky) 100%);
// //   -webkit-background-clip: text; -webkit-text-fill-color: transparent;
// //   background-clip: text;
// //   background-size: 200% 100%;
// //   animation: shimmer 4s linear infinite;
// // }

// // @keyframes shimmer {
// //   0%   { background-position: 100% 0; }
// //   100% { background-position: -100% 0; }
// // }

// // .dg-hero-sub {
// //   font-family: var(--font-mono);
// //   font-size: 15px; color: var(--text2);
// //   max-width: 520px; margin: 0 auto;
// //   line-height: 1.8;
// // }

// // /* ── MAIN SPLIT LAYOUT ── */
// // .dg-split {
// //   display: grid;
// //   grid-template-columns: 420px 1fr;
// //   gap: 20px;
// //   align-items: start;
// // }

// // @media (max-width: 900px) {
// //   .dg-split { grid-template-columns: 1fr; }
// // }

// // /* ── CARD BASE ── */
// // .dg-card {
// //   background: var(--surface);
// //   border: 1px solid var(--border);
// //   border-radius: var(--radius);
// //   position: relative;
// //   overflow: hidden;
// //   backdrop-filter: blur(20px);
// //   -webkit-backdrop-filter: blur(20px);
// //   transition: border-color 0.3s;
// // }

// // .dg-card::before {
// //   content: '';
// //   position: absolute; top: 0; left: 0; right: 0; height: 1px;
// //   background: linear-gradient(90deg, transparent 0%, var(--violet) 30%, var(--mint) 70%, transparent 100%);
// //   opacity: 0.5;
// // }

// // .dg-card-glow {
// //   position: absolute; pointer-events: none;
// //   border-radius: 50%;
// //   filter: blur(60px);
// //   opacity: 0; transition: opacity 0.5s;
// // }

// // .dg-card:hover .dg-card-glow { opacity: 1; }

// // /* ── CARD HEADER ── */
// // .dg-card-head {
// //   display: flex; align-items: center; gap: 10px;
// //   padding: 14px 20px;
// //   border-bottom: 1px solid var(--border);
// //   background: var(--surface2);
// // }

// // .dg-traffic {
// //   display: flex; gap: 6px; align-items: center;
// // }

// // .dg-dot-red   { width: 10px; height: 10px; border-radius: 50%; background: #ff5f57; }
// // .dg-dot-amber { width: 10px; height: 10px; border-radius: 50%; background: #febc2e; }
// // .dg-dot-green { width: 10px; height: 10px; border-radius: 50%; background: #28c840; }

// // .dg-card-head-title {
// //   margin-left: 4px;
// //   font-family: var(--font-mono);
// //   font-size: 11px; color: var(--text3);
// //   letter-spacing: 1.5px; text-transform: uppercase;
// // }

// // /* ── FORM BODY ── */
// // .dg-body { padding: 24px; }

// // /* ── MODE TABS ── */
// // .dg-tabs {
// //   display: flex;
// //   background: rgba(0,0,0,0.3);
// //   border: 1px solid var(--border);
// //   border-radius: var(--radius-sm);
// //   padding: 4px;
// //   gap: 4px;
// //   margin-bottom: 24px;
// // }

// // .dg-tab {
// //   flex: 1;
// //   display: flex; align-items: center; justify-content: center; gap: 7px;
// //   padding: 9px 12px;
// //   font-family: var(--font-mono);
// //   font-size: 11px; font-weight: 600;
// //   color: var(--text3);
// //   background: transparent;
// //   border: none; border-radius: 6px;
// //   cursor: pointer;
// //   text-transform: uppercase; letter-spacing: 1px;
// //   transition: all 0.2s;
// // }

// // .dg-tab:hover { color: var(--text2); background: var(--surface3); }

// // .dg-tab.active {
// //   background: linear-gradient(135deg, rgba(124,108,248,0.25), rgba(0,232,162,0.1));
// //   color: #fff;
// //   border: 1px solid rgba(124,108,248,0.35);
// //   box-shadow: 0 0 20px rgba(124,108,248,0.15);
// // }

// // /* ── FIELD ── */
// // .dg-field { margin-bottom: 18px; }

// // .dg-label {
// //   display: flex; align-items: center; gap: 7px;
// //   font-family: var(--font-mono);
// //   font-size: 10px; font-weight: 600;
// //   color: var(--text3);
// //   letter-spacing: 2px; text-transform: uppercase;
// //   margin-bottom: 8px;
// // }

// // .dg-label-dot {
// //   width: 5px; height: 5px;
// //   border-radius: 50%;
// //   background: var(--violet);
// // }

// // /* ── INPUT ── */
// // .dg-input-wrap { position: relative; }

// // .dg-input-icon {
// //   position: absolute; left: 13px; top: 50%; transform: translateY(-50%);
// //   color: var(--text3); pointer-events: none;
// //   display: flex; align-items: center;
// // }

// // .dg-input {
// //   width: 100%;
// //   background: rgba(0,0,0,0.3);
// //   border: 1px solid var(--border);
// //   border-radius: var(--radius-sm);
// //   color: var(--text);
// //   font-family: var(--font-mono);
// //   font-size: 13px;
// //   padding: 11px 14px 11px 38px;
// //   outline: none;
// //   transition: border-color 0.2s, box-shadow 0.2s, background 0.2s;
// //   -webkit-appearance: none;
// // }

// // .dg-input::placeholder { color: var(--text3); }

// // .dg-input:focus {
// //   border-color: rgba(124,108,248,0.5);
// //   box-shadow: 0 0 0 3px rgba(124,108,248,0.1), 0 0 20px rgba(124,108,248,0.08);
// //   background: rgba(124,108,248,0.04);
// // }

// // .dg-input:disabled { opacity: 0.45; cursor: not-allowed; }

// // textarea.dg-input {
// //   padding-top: 11px; resize: vertical; min-height: 80px;
// //   padding-left: 14px;
// // }

// // .dg-hint {
// //   margin-top: 6px;
// //   font-size: 11px; color: var(--text3);
// //   font-family: var(--font-mono);
// //   padding-left: 2px;
// // }

// // /* ── SELECT ── */
// // .dg-select-wrap { position: relative; }

// // .dg-select-wrap::after {
// //   content: "▾";
// //   position: absolute; right: 14px; top: 50%;
// //   transform: translateY(-50%);
// //   color: var(--text3); font-size: 12px;
// //   pointer-events: none;
// // }

// // select.dg-input {
// //   padding-left: 38px;
// //   cursor: pointer;
// //   appearance: none;
// // }

// // /* ── DIVIDER ── */
// // .dg-divider {
// //   height: 1px;
// //   background: linear-gradient(90deg, transparent, var(--border2), transparent);
// //   margin: 20px 0;
// // }

// // /* ── TOGGLE ROW ── */
// // .dg-toggle-row {
// //   display: flex; align-items: flex-start; gap: 12px;
// //   padding: 14px;
// //   background: rgba(0,0,0,0.2);
// //   border: 1px solid var(--border);
// //   border-radius: var(--radius-sm);
// //   cursor: pointer;
// //   transition: all 0.2s;
// //   margin-bottom: 20px;
// // }

// // .dg-toggle-row:hover { border-color: var(--border2); background: rgba(124,108,248,0.04); }

// // .dg-switch {
// //   position: relative; width: 38px; height: 21px; flex-shrink: 0; margin-top: 1px;
// // }

// // .dg-switch input { opacity: 0; width: 0; height: 0; }

// // .dg-slider {
// //   position: absolute; inset: 0;
// //   background: rgba(255,255,255,0.06);
// //   border: 1px solid var(--border2);
// //   border-radius: 99px;
// //   cursor: pointer;
// //   transition: all 0.25s;
// // }

// // .dg-slider::before {
// //   content: '';
// //   position: absolute; left: 3px; top: 50%;
// //   transform: translateY(-50%);
// //   width: 13px; height: 13px;
// //   background: var(--text3);
// //   border-radius: 50%;
// //   transition: all 0.25s;
// // }

// // input:checked + .dg-slider {
// //   background: linear-gradient(135deg, rgba(124,108,248,0.3), rgba(0,232,162,0.2));
// //   border-color: rgba(124,108,248,0.5);
// // }

// // input:checked + .dg-slider::before {
// //   transform: translate(17px, -50%);
// //   background: var(--violet);
// //   box-shadow: 0 0 10px rgba(124,108,248,0.6);
// // }

// // .dg-toggle-text { flex: 1; }

// // .dg-toggle-label {
// //   font-size: 13px; color: var(--text);
// //   font-family: var(--font-mono);
// //   margin-bottom: 3px;
// // }

// // .dg-toggle-desc {
// //   font-size: 11px; color: var(--text3);
// //   font-family: var(--font-mono); line-height: 1.5;
// // }

// // /* ── SUBMIT BUTTON ── */
// // .dg-btn {
// //   width: 100%;
// //   padding: 14px 20px;
// //   border-radius: var(--radius-sm);
// //   background: linear-gradient(135deg, var(--violet), var(--violet-d));
// //   border: none;
// //   color: #fff;
// //   font-family: var(--font-display);
// //   font-size: 13px; font-weight: 700;
// //   letter-spacing: 0.5px;
// //   cursor: pointer;
// //   display: flex; align-items: center; justify-content: center; gap: 10px;
// //   position: relative; overflow: hidden;
// //   transition: all 0.25s;
// //   text-transform: uppercase;
// //   box-shadow: 0 0 30px rgba(124,108,248,0.3), 0 1px 0 rgba(255,255,255,0.1) inset;
// // }

// // .dg-btn::before {
// //   content: '';
// //   position: absolute; inset: 0;
// //   background: linear-gradient(135deg, rgba(255,255,255,0.1), transparent);
// // }

// // .dg-btn::after {
// //   content: '';
// //   position: absolute; inset: 0;
// //   background: linear-gradient(135deg, var(--mint), var(--violet));
// //   opacity: 0; transition: opacity 0.3s;
// // }

// // .dg-btn:hover:not(:disabled)::after { opacity: 1; }
// // .dg-btn:hover:not(:disabled) { transform: translateY(-1px); box-shadow: 0 8px 40px rgba(124,108,248,0.4); }
// // .dg-btn:active:not(:disabled) { transform: translateY(0); }
// // .dg-btn:disabled { opacity: 0.35; cursor: not-allowed; }
// // .dg-btn > * { position: relative; z-index: 1; }

// // .dg-btn.loading {
// //   background: linear-gradient(135deg, rgba(56,189,248,0.3), rgba(124,108,248,0.3));
// //   box-shadow: 0 0 30px rgba(56,189,248,0.2);
// // }

// // /* ── SPINNER ── */
// // .dg-spin {
// //   width: 16px; height: 16px;
// //   border: 2px solid rgba(255,255,255,0.3);
// //   border-top-color: #fff;
// //   border-radius: 50%;
// //   animation: spin 0.65s linear infinite;
// // }

// // @keyframes spin { to { transform: rotate(360deg); } }

// // /* ── RIGHT PANEL ── */
// // .dg-right { display: flex; flex-direction: column; gap: 16px; }

// // /* ── PIPELINE CARD ── */
// // .dg-pipeline { }

// // .dg-pipeline-title {
// //   display: flex; align-items: center; gap: 8px;
// //   font-family: var(--font-mono);
// //   font-size: 10px; color: var(--text3);
// //   letter-spacing: 2px; text-transform: uppercase;
// // }

// // .dg-pipeline-body { padding: 20px 24px; }

// // .dg-step {
// //   display: flex; gap: 14px; align-items: stretch;
// //   animation: fadeSlideIn 0.4s ease both;
// // }

// // @keyframes fadeSlideIn {
// //   from { opacity: 0; transform: translateX(-8px); }
// //   to   { opacity: 1; transform: translateX(0); }
// // }

// // .dg-step-left {
// //   display: flex; flex-direction: column; align-items: center;
// //   width: 30px; flex-shrink: 0;
// // }

// // .dg-step-node {
// //   width: 30px; height: 30px;
// //   border-radius: 50%;
// //   display: flex; align-items: center; justify-content: center;
// //   font-size: 11px; font-weight: 600;
// //   font-family: var(--font-mono);
// //   flex-shrink: 0; z-index: 1;
// //   transition: all 0.4s;
// //   position: relative;
// // }

// // .dg-step-node.waiting {
// //   background: rgba(255,255,255,0.04);
// //   border: 1px solid var(--border);
// //   color: var(--text3);
// // }

// // .dg-step-node.running {
// //   background: rgba(56,189,248,0.1);
// //   border: 1.5px solid var(--sky);
// //   color: var(--sky);
// //   box-shadow: 0 0 16px rgba(56,189,248,0.35), 0 0 40px rgba(56,189,248,0.1);
// //   animation: nodeGlow 1.2s ease-in-out infinite;
// // }

// // @keyframes nodeGlow {
// //   0%, 100% { box-shadow: 0 0 12px rgba(56,189,248,0.3); }
// //   50%       { box-shadow: 0 0 24px rgba(56,189,248,0.55); }
// // }

// // .dg-step-node.done {
// //   background: rgba(0,232,162,0.12);
// //   border: 1.5px solid var(--mint);
// //   color: var(--mint);
// //   box-shadow: 0 0 12px rgba(0,232,162,0.2);
// // }

// // .dg-step-node.error {
// //   background: rgba(255,79,114,0.1);
// //   border: 1.5px solid var(--rose);
// //   color: var(--rose);
// // }

// // .dg-connector {
// //   width: 1px; flex: 1; min-height: 18px;
// //   margin-top: 5px;
// //   background: var(--border);
// //   transition: background 0.4s, opacity 0.4s;
// // }

// // .dg-connector.lit {
// //   background: linear-gradient(to bottom, var(--mint), transparent);
// //   opacity: 0.5;
// // }

// // .dg-step-info { flex: 1; padding: 4px 0 18px; }

// // .dg-step-name {
// //   font-size: 13px; font-family: var(--font-mono); font-weight: 500;
// //   margin-bottom: 3px; transition: color 0.3s;
// // }

// // .dg-step-name.waiting  { color: var(--text3); }
// // .dg-step-name.running  { color: #fff; }
// // .dg-step-name.done     { color: var(--mint); }
// // .dg-step-name.error    { color: var(--rose); }

// // .dg-step-msg {
// //   font-size: 11px; font-family: var(--font-mono);
// //   line-height: 1.5; transition: color 0.3s;
// // }

// // .dg-step-msg.waiting  { color: var(--text3); }
// // .dg-step-msg.running  { color: var(--sky); }
// // .dg-step-msg.done     { color: var(--text2); }
// // .dg-step-msg.error    { color: var(--rose); }

// // .dg-cursor {
// //   display: inline-block; width: 7px; height: 11px;
// //   background: var(--sky); margin-left: 3px;
// //   vertical-align: middle;
// //   animation: blink 0.8s step-end infinite;
// // }

// // @keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0; } }

// // /* ── PREVIEW CARD ── */
// // .dg-preview { flex: 1; min-height: 0; }

// // .dg-preview-head {
// //   display: flex; align-items: center; justify-content: space-between;
// //   gap: 10px;
// // }

// // .dg-preview-title {
// //   display: flex; align-items: center; gap: 8px;
// //   font-family: var(--font-mono);
// //   font-size: 10px; color: var(--text3);
// //   letter-spacing: 2px; text-transform: uppercase;
// // }

// // .dg-preview-actions {
// //   display: flex; gap: 8px;
// // }

// // .dg-action-btn {
// //   display: flex; align-items: center; gap: 6px;
// //   padding: 7px 12px;
// //   background: var(--surface2);
// //   border: 1px solid var(--border);
// //   border-radius: 6px;
// //   color: var(--text2);
// //   font-family: var(--font-mono);
// //   font-size: 11px; cursor: pointer;
// //   transition: all 0.2s;
// // }

// // .dg-action-btn:hover {
// //   border-color: var(--border2);
// //   color: var(--text);
// //   background: var(--surface3);
// // }

// // .dg-action-btn.primary {
// //   border-color: rgba(0,232,162,0.3);
// //   color: var(--mint);
// //   background: rgba(0,232,162,0.05);
// // }

// // .dg-action-btn.primary:hover {
// //   background: rgba(0,232,162,0.1);
// //   box-shadow: 0 0 20px rgba(0,232,162,0.15);
// // }

// // /* ── MARKDOWN PREVIEW BODY ── */
// // .dg-preview-body {
// //   padding: 24px;
// //   height: 400px;
// //   overflow-y: auto;
// //   font-family: var(--font-mono);
// //   font-size: 13px; line-height: 1.75;
// //   color: var(--text2);
// // }

// // .dg-preview-body h1,
// // .dg-preview-body h2,
// // .dg-preview-body h3 {
// //   font-family: var(--font-display);
// //   color: #fff;
// //   margin: 1.4em 0 0.6em;
// //   letter-spacing: -0.5px;
// // }

// // .dg-preview-body h1 { font-size: 22px; }
// // .dg-preview-body h2 { font-size: 17px; color: var(--violet); }
// // .dg-preview-body h3 { font-size: 14px; color: var(--text); }

// // .dg-preview-body p { margin-bottom: 0.9em; }

// // .dg-preview-body code {
// //   background: rgba(124,108,248,0.12);
// //   border: 1px solid rgba(124,108,248,0.2);
// //   border-radius: 4px;
// //   padding: 1px 6px;
// //   color: var(--violet);
// //   font-size: 12px;
// // }

// // .dg-preview-body pre {
// //   background: rgba(0,0,0,0.4);
// //   border: 1px solid var(--border2);
// //   border-radius: 8px;
// //   padding: 16px;
// //   overflow-x: auto;
// //   margin: 12px 0;
// // }

// // .dg-preview-body pre code {
// //   background: none; border: none; padding: 0;
// //   color: var(--mint); font-size: 12px;
// // }

// // .dg-preview-body ul, .dg-preview-body ol {
// //   padding-left: 20px; margin-bottom: 0.9em;
// // }

// // .dg-preview-body li { margin-bottom: 4px; }

// // .dg-preview-body blockquote {
// //   border-left: 3px solid var(--violet);
// //   padding-left: 14px;
// //   color: var(--text2);
// //   margin: 12px 0;
// // }

// // .dg-preview-body a { color: var(--sky); text-decoration: none; }
// // .dg-preview-body a:hover { color: var(--mint); }

// // .dg-preview-body table {
// //   width: 100%; border-collapse: collapse; margin: 12px 0;
// //   font-size: 12px;
// // }

// // .dg-preview-body th {
// //   background: rgba(124,108,248,0.1);
// //   border: 1px solid var(--border2);
// //   padding: 8px 12px;
// //   color: var(--violet);
// //   text-align: left;
// // }

// // .dg-preview-body td {
// //   border: 1px solid var(--border);
// //   padding: 7px 12px;
// // }

// // .dg-preview-body hr {
// //   border: none; border-top: 1px solid var(--border2);
// //   margin: 20px 0;
// // }

// // .dg-preview-empty {
// //   display: flex; flex-direction: column;
// //   align-items: center; justify-content: center;
// //   height: 100%;
// //   gap: 12px;
// // }

// // .dg-preview-empty-icon {
// //   width: 52px; height: 52px;
// //   border-radius: 14px;
// //   background: var(--surface2);
// //   border: 1px solid var(--border);
// //   display: flex; align-items: center; justify-content: center;
// //   color: var(--text3);
// // }

// // .dg-preview-empty-text {
// //   font-family: var(--font-mono);
// //   font-size: 12px; color: var(--text3);
// //   letter-spacing: 1px; text-align: center; line-height: 1.6;
// // }

// // /* ── REFINE BOX ── */
// // .dg-refine {
// //   display: flex; gap: 8px; padding: 16px 24px;
// //   border-top: 1px solid var(--border);
// //   background: var(--surface2);
// //   border-radius: 0 0 var(--radius) var(--radius);
// // }

// // .dg-refine-input {
// //   flex: 1;
// //   background: rgba(0,0,0,0.3);
// //   border: 1px solid var(--border);
// //   border-radius: 6px;
// //   color: var(--text);
// //   font-family: var(--font-mono);
// //   font-size: 12px;
// //   padding: 9px 12px;
// //   outline: none;
// //   transition: border-color 0.2s;
// // }

// // .dg-refine-input:focus { border-color: rgba(124,108,248,0.4); }
// // .dg-refine-input::placeholder { color: var(--text3); }

// // .dg-refine-btn {
// //   display: flex; align-items: center; gap: 6px;
// //   padding: 9px 16px;
// //   background: rgba(124,108,248,0.15);
// //   border: 1px solid rgba(124,108,248,0.3);
// //   border-radius: 6px;
// //   color: var(--violet);
// //   font-family: var(--font-mono);
// //   font-size: 11px; font-weight: 600;
// //   cursor: pointer; white-space: nowrap;
// //   transition: all 0.2s;
// //   text-transform: uppercase; letter-spacing: 1px;
// // }

// // .dg-refine-btn:hover:not(:disabled) {
// //   background: rgba(124,108,248,0.25);
// //   box-shadow: 0 0 20px rgba(124,108,248,0.2);
// // }

// // .dg-refine-btn:disabled { opacity: 0.3; cursor: not-allowed; }

// // /* ── SUCCESS BANNER ── */
// // .dg-success {
// //   padding: 20px 24px;
// //   border-top: 1px solid rgba(0,232,162,0.2);
// //   background: rgba(0,232,162,0.04);
// //   display: flex; align-items: center; gap: 16px;
// // }

// // .dg-success-icon {
// //   width: 38px; height: 38px;
// //   border-radius: 50%;
// //   background: rgba(0,232,162,0.15);
// //   border: 1.5px solid rgba(0,232,162,0.4);
// //   display: flex; align-items: center; justify-content: center;
// //   color: var(--mint);
// //   flex-shrink: 0;
// //   box-shadow: 0 0 20px rgba(0,232,162,0.2);
// // }

// // .dg-success-text { flex: 1; }

// // .dg-success-label {
// //   font-size: 12px; font-weight: 600;
// //   color: var(--mint);
// //   font-family: var(--font-mono);
// //   margin-bottom: 2px;
// // }

// // .dg-success-sub {
// //   font-size: 11px; color: var(--text2);
// //   font-family: var(--font-mono);
// // }

// // .dg-success-link {
// //   display: inline-flex; align-items: center; gap: 5px;
// //   color: var(--sky);
// //   font-size: 12px; font-family: var(--font-mono);
// //   text-decoration: none;
// //   border-bottom: 1px solid rgba(56,189,248,0.3);
// //   padding-bottom: 1px;
// //   transition: color 0.2s;
// // }

// // .dg-success-link:hover { color: var(--mint); border-color: rgba(0,232,162,0.4); }

// // /* ── TOAST ── */
// // .dg-toast {
// //   position: fixed; bottom: 24px; left: 50%;
// //   transform: translateX(-50%);
// //   background: #150810;
// //   border: 1px solid rgba(255,79,114,0.35);
// //   color: var(--rose);
// //   font-family: var(--font-mono); font-size: 13px;
// //   padding: 12px 18px;
// //   border-radius: 10px;
// //   display: flex; align-items: center; gap: 10px;
// //   max-width: 500px; width: 90%;
// //   box-shadow: 0 8px 40px rgba(0,0,0,0.6), 0 0 30px rgba(255,79,114,0.1);
// //   z-index: 9999;
// //   animation: toastIn 0.3s ease;
// // }

// // @keyframes toastIn {
// //   from { opacity: 0; transform: translateX(-50%) translateY(12px); }
// //   to   { opacity: 1; transform: translateX(-50%) translateY(0); }
// // }

// // .dg-toast-close {
// //   background: none; border: none;
// //   color: var(--text3); cursor: pointer;
// //   font-size: 18px; line-height: 1;
// //   margin-left: auto; padding: 0;
// //   transition: color 0.2s;
// // }

// // .dg-toast-close:hover { color: var(--text); }

// // /* ── CONFETTI CANVAS ── */
// // .dg-confetti {
// //   position: fixed; inset: 0;
// //   z-index: 99999; pointer-events: none;
// // }

// // /* ── FOOTER ── */
// // .dg-footer {
// //   text-align: center; padding-top: 60px;
// //   font-family: var(--font-mono);
// //   font-size: 11px; color: var(--text3);
// //   letter-spacing: 1.5px;
// // }

// // .dg-footer span { color: var(--violet); }
// // `;

// // /* ─── PIPELINE STEPS ─────────────────────────────────────────────────────── */
// // const STEP_DEFS = [
// //   { id: "fetching", label: "Fetch Repository", icon: "01" },
// //   { id: "parsing", label: "Parse & Rank Files", icon: "02" },
// //   { id: "caching", label: "Extract Metadata", icon: "03" },
// //   { id: "generating", label: "Generate via AI", icon: "04" },
// //   { id: "pushing", label: "Push to GitHub", icon: "05" },
// // ];

// // const makeSteps = () => STEP_DEFS.map(s => ({ ...s, status: "waiting", message: "Waiting to start" }));

// // /* ─── SIMPLE CONFETTI (no external dep) ─────────────────────────────────── */
// // function Confetti({ active }: { active: boolean }) {
// //   const canvasRef = useRef<HTMLCanvasElement>(null);

// //   useEffect(() => {
// //     if (!active) return;
// //     const canvas = canvasRef.current;
// //     if (!canvas) return;
// //     canvas.width = window.innerWidth;
// //     canvas.height = window.innerHeight;
// //     const ctx = canvas.getContext("2d");
// //     if (!ctx) return;
// //     const pieces = Array.from({ length: 220 }, () => ({
// //       x: Math.random() * canvas.width,
// //       y: Math.random() * -canvas.height,
// //       w: 8 + Math.random() * 8,
// //       h: 4 + Math.random() * 4,
// //       color: ["#7c6cf8", "#00e8a2", "#f5a623", "#ff4f72", "#38bdf8"][Math.floor(Math.random() * 5)],
// //       rot: Math.random() * 360,
// //       vx: (Math.random() - 0.5) * 2.5,
// //       vy: 2 + Math.random() * 4,
// //       vr: (Math.random() - 0.5) * 6,
// //       alpha: 1,
// //     }));
// //     let raf: number;
// //     const draw = () => {
// //       ctx.clearRect(0, 0, canvas.width, canvas.height);
// //       let alive = false;
// //       pieces.forEach(p => {
// //         p.x += p.vx; p.y += p.vy; p.rot += p.vr;
// //         if (p.y < canvas.height + 20) alive = true;
// //         else p.alpha -= 0.02;
// //         ctx.save();
// //         ctx.globalAlpha = Math.max(0, p.alpha);
// //         ctx.translate(p.x, p.y);
// //         ctx.rotate((p.rot * Math.PI) / 180);
// //         ctx.fillStyle = p.color;
// //         ctx.fillRect(-p.w / 2, -p.h / 2, p.w, p.h);
// //         ctx.restore();
// //       });
// //       if (alive) raf = requestAnimationFrame(draw);
// //     };
// //     raf = requestAnimationFrame(draw);
// //     return () => cancelAnimationFrame(raf);
// //   }, [active]);

// //   if (!active) return null;
// //   return <canvas ref={canvasRef} className="dg-confetti" />;
// // }

// // /* ─── MAIN COMPONENT ─────────────────────────────────────────────────────── */
// // export default function DocuGenius() {
// //   const [repo, setRepo] = useState("");
// //   const [token, setToken] = useState("");
// //   const [mode, setMode] = useState("github");
// //   const [localPath, setLocalPath] = useState("");
// //   const [targetAudience, setTargetAudience] = useState("Mixed");
// //   const [customInstructions, setCustomInstructions] = useState("");
// //   const [autoGenerate, setAutoGenerate] = useState(true);
// //   const [loading, setLoading] = useState(false);
// //   const [success, setSuccess] = useState(false);
// //   const [error, setError] = useState("");
// //   const [readmeUrl, setReadmeUrl] = useState("");
// //   const [generatedMarkdown, setGeneratedMarkdown] = useState("");
// //   const [refineText, setRefineText] = useState("");
// //   const [steps, setSteps] = useState(makeSteps());
// //   const [showRight, setShowRight] = useState(false);
// //   const [confettiActive, setConfettiActive] = useState(false);
// //   const [commitReady, setCommitReady] = useState(false);
// //   const [committing, setCommitting] = useState(false);
// //   const previewRef = useRef<HTMLDivElement>(null);

// //   useEffect(() => {
// //     if (previewRef.current) {
// //       previewRef.current.scrollTop = previewRef.current.scrollHeight;
// //     }
// //   }, [generatedMarkdown]);

// //   const updateStep = (id: string, patch: any) =>
// //     setSteps(prev => prev.map(s => s.id === id ? { ...s, ...patch } : s));

// //   const handleSubmit = async (e: any, overrideInstructions: string | null = null) => {
// //     e?.preventDefault();
// //     if (mode === "github" && (!repo || !token)) { setError("Please provide both repository and access token"); return; }
// //     if (mode === "local" && !localPath) { setError("Please provide an absolute path"); return; }

// //     setLoading(true); setError(""); setSuccess(false); setCommitReady(false);
// //     setReadmeUrl(""); setGeneratedMarkdown("");
// //     setSteps(makeSteps()); setShowRight(true);

// //     const finalInstructions = overrideInstructions !== null ? overrideInstructions : customInstructions;

// //     try {
// //       const payload = mode === "github"
// //         ? { repo, access_token: token, branch: "main", commit_message: "Update README", custom_instructions: finalInstructions, sections: [], target_audience: targetAudience, auto_commit: autoGenerate }
// //         : { local_path: localPath, repo: "", access_token: "", branch: "main", custom_instructions: finalInstructions, sections: [], target_audience: targetAudience, auto_commit: autoGenerate };

// //       const res = await fetch("http://localhost:8000/stream-readme", {
// //         method: "POST",
// //         headers: { "Content-Type": "application/json" },
// //         body: JSON.stringify(payload),
// //       });

// //       if (!res.ok) {
// //         let d; try { d = await res.json(); } catch (_) { }
// //         throw new Error(d?.detail || res.statusText);
// //       }

// //       if (!res.body) throw new Error("No response body");
// //       const reader = res.body.getReader();
// //       const decoder = new TextDecoder();
// //       let buffer = "";

// //       while (true) {
// //         const { value, done } = await reader.read();
// //         if (done) break;
// //         buffer += decoder.decode(value, { stream: true });
// //         const parts = buffer.split("\n\n");
// //         buffer = parts.pop() || "";
// //         for (const part of parts) {
// //           if (!part.startsWith("data: ")) continue;
// //           try {
// //             const data = JSON.parse(part.slice(6));
// //             if (data.step === "error") {
// //               setError(data.message);
// //               setSteps(prev => prev.map(s => s.status === "running" ? { ...s, status: "error", message: data.message } : s));
// //               break;
// //             }
// //             if (data.step && data.step !== "done") {
// //               updateStep(data.step, { status: data.status, message: data.message });
// //             }
// //             if (data.step === "generating" && data.chunk) {
// //               setGeneratedMarkdown(prev => prev + data.chunk);
// //             }
// //             if (data.step === "done") {
// //               if (data.file_url) {
// //                 setSuccess(true);
// //                 setReadmeUrl(data.file_url);
// //                 setConfettiActive(true);
// //                 setTimeout(() => setConfettiActive(false), 5000);
// //               } else {
// //                 setCommitReady(true);
// //               }
// //             }
// //           } catch (_) { }
// //         }
// //       }

// //       try {
// //         await fetch(`http://localhost:8000/preferences/${repo}`, {
// //           method: "POST",
// //           headers: { "Content-Type": "application/json" },
// //           body: JSON.stringify({ auto_generate_on_push: autoGenerate }),
// //         });
// //       } catch (_) { }

// //     } catch (err: any) {
// //       setError(err.message || "An error occurred");
// //     } finally {
// //       setLoading(false);
// //     }
// //   };

// //   const handleRefine = (e: any) => {
// //     e.preventDefault();
// //     if (!refineText.trim()) return;
// //     const newInstr = customInstructions
// //       ? `${customInstructions}\n\nRefinement: ${refineText}`
// //       : `Refinement: ${refineText}`;
// //     setCustomInstructions(newInstr);
// //     setRefineText("");
// //     handleSubmit(null, newInstr);
// //   };

// //   const handleCommit = async () => {
// //     setCommitting(true);
// //     setError("");
// //     try {
// //       const payload = {
// //         repo: mode === "github" ? repo : "",
// //         access_token: token,
// //         local_path: mode === "local" ? localPath : "",
// //         markdown_content: generatedMarkdown,
// //       };
// //       const res = await fetch("http://localhost:8000/commit-readme", {
// //         method: "POST",
// //         headers: { "Content-Type": "application/json" },
// //         body: JSON.stringify(payload)
// //       });
// //       if (!res.ok) {
// //         let d; try { d = await res.json(); } catch (_) { }
// //         throw new Error(d?.detail || res.statusText);
// //       }
// //       setCommitReady(false);
// //       setSuccess(true);
// //       if (mode === "github") {
// //         const owner = repo.split("/")[0];
// //         const rName = repo.split("/")[1];
// //         setReadmeUrl(`https://github.com/${owner}/${rName}/blob/main/README.md`);
// //       } else {
// //         setReadmeUrl(`file://${localPath}/README.md`);
// //       }
// //       setConfettiActive(true);
// //       setTimeout(() => setConfettiActive(false), 5000);
// //     } catch (err: any) {
// //       setError(err.message || "Failed to commit README");
// //     } finally {
// //       setCommitting(false);
// //     }
// //   };

// //   const copyToClipboard = () => {
// //     navigator.clipboard.writeText(generatedMarkdown);
// //   };

// //   const downloadFile = () => {
// //     const blob = new Blob([generatedMarkdown], { type: "text/markdown" });
// //     const url = URL.createObjectURL(blob);
// //     const a = document.createElement("a");
// //     a.href = url; a.download = "README.md";
// //     document.body.appendChild(a); a.click();
// //     document.body.removeChild(a); URL.revokeObjectURL(url);
// //   };

// //   const canSubmit = !loading && (mode === "github" ? (repo && token) : localPath);

// //   return (
// //     <>
// //       <style>{STYLES}</style>
// //       <Confetti active={confettiActive} />

// //       <div className="dg-root">
// //         {/* Aurora */}
// //         <div className="dg-aurora">
// //           <div className="dg-aurora-blob" />
// //           <div className="dg-aurora-blob" />
// //           <div className="dg-aurora-blob" />
// //         </div>
// //         <div className="dg-grid" />

// //         <div className="dg-wrapper">

// //           {/* ── Header ── */}
// //           <header className="dg-header">
// //             <div className="dg-brand">
// //               <div className="dg-brand-mark">
// //                 <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5">
// //                   <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
// //                 </svg>
// //               </div>
// //               <div>
// //                 <div className="dg-brand-name">DocuGenius</div>
// //                 <div className="dg-brand-tag">AI · readme generator</div>
// //               </div>
// //             </div>
// //             <div className="dg-status-pill">
// //               <div className="dg-status-dot" />
// //               System Online
// //             </div>
// //           </header>

// //           {/* ── Hero ── */}
// //           <div className="dg-hero">
// //             <div className="dg-eyebrow">
// //               <Zap size={11} />
// //               Powered by Claude
// //             </div>
// //             <h1 className="dg-hero-title">
// //               <span className="line1">Your codebase.</span>
// //               <span className="line2">Documented instantly.</span>
// //             </h1>
// //             <p className="dg-hero-sub">
// //               Analyze any GitHub repository or local project and generate a stunning, professional README in seconds. Commit directly. No manual work.
// //             </p>
// //           </div>

// //           {/* ── Split Layout ── */}
// //           <div className="dg-split">

// //             {/* ── Left: Form ── */}
// //             <div>
// //               <div className="dg-card">
// //                 <div className="dg-card-glow" style={{ width: 300, height: 300, top: -100, left: -100, background: "radial-gradient(circle, rgba(124,108,248,0.12), transparent 70%)" }} />
// //                 <div className="dg-card-head">
// //                   <div className="dg-traffic">
// //                     <div className="dg-dot-red" />
// //                     <div className="dg-dot-amber" />
// //                     <div className="dg-dot-green" />
// //                   </div>
// //                   <span className="dg-card-head-title">readme.generator — ssh</span>
// //                 </div>

// //                 <div className="dg-body">

// //                   {/* Mode Tabs */}
// //                   <div className="dg-tabs">
// //                     <button type="button" className={`dg-tab ${mode === "github" ? "active" : ""}`} onClick={() => setMode("github")}>
// //                       <Github size={12} /> GitHub
// //                     </button>
// //                     <button type="button" className={`dg-tab ${mode === "local" ? "active" : ""}`} onClick={() => setMode("local")}>
// //                       <FolderOpen size={12} /> Local
// //                     </button>
// //                   </div>

// //                   {mode === "github" ? (
// //                     <>
// //                       <div className="dg-field">
// //                         <div className="dg-label"><div className="dg-label-dot" /> Repository</div>
// //                         <div className="dg-input-wrap">
// //                           <span className="dg-input-icon"><Github size={13} /></span>
// //                           <input className="dg-input" placeholder="owner/repository" value={repo} onChange={e => setRepo(e.target.value)} disabled={loading} autoComplete="off" spellCheck="false" />
// //                         </div>
// //                       </div>
// //                       <div className="dg-field">
// //                         <div className="dg-label" style={{ color: "var(--sky)" }}><div className="dg-label-dot" style={{ background: "var(--sky)" }} /> Access Token</div>
// //                         <div className="dg-input-wrap">
// //                           <span className="dg-input-icon">
// //                             <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="11" width="18" height="11" rx="2" /><path d="M7 11V7a5 5 0 0 1 10 0v4" /></svg>
// //                           </span>
// //                           <input className="dg-input" type="password" placeholder="ghp_••••••••••••••••" value={token} onChange={e => setToken(e.target.value)} disabled={loading} />
// //                         </div>
// //                         <div className="dg-hint">// Required for read access and pushing the README</div>
// //                       </div>
// //                     </>
// //                   ) : (
// //                     <div className="dg-field">
// //                       <div className="dg-label"><div className="dg-label-dot" /> Local Path</div>
// //                       <div className="dg-input-wrap">
// //                         <span className="dg-input-icon"><FolderOpen size={13} /></span>
// //                         <input className="dg-input" placeholder="/home/user/my-project" value={localPath} onChange={e => setLocalPath(e.target.value)} disabled={loading} autoComplete="off" spellCheck="false" />
// //                       </div>
// //                       <div className="dg-hint">// README.md will be written directly to this directory</div>
// //                     </div>
// //                   )}

// //                   <div className="dg-divider" />

// //                   {/* Target Audience */}
// //                   <div className="dg-field">
// //                     <div className="dg-label" style={{ color: "var(--amber)" }}>
// //                       <div className="dg-label-dot" style={{ background: "var(--amber)" }} /> Target Audience
// //                     </div>
// //                     <div className="dg-select-wrap">
// //                       <span className="dg-input-icon">
// //                         <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" /><path d="M23 21v-2a4 4 0 0 0-3-3.87" /><path d="M16 3.13a4 4 0 0 1 0 7.75" /></svg>
// //                       </span>
// //                       <select className="dg-input" value={targetAudience} onChange={e => setTargetAudience(e.target.value)} disabled={loading}>
// //                         <option value="Mixed">Mixed — Default</option>
// //                         <option value="Beginner Developers">Beginner Developers</option>
// //                         <option value="Advanced Engineers">Advanced Engineers</option>
// //                         <option value="End Users">End Users (No Code)</option>
// //                       </select>
// //                     </div>
// //                   </div>

// //                   {/* Custom Instructions */}
// //                   <div className="dg-field">
// //                     <div className="dg-label"><div className="dg-label-dot" style={{ background: "var(--mint)" }} /> Additional Instructions
// //                       <span style={{ marginLeft: 4, color: "var(--text3)" }}>— optional</span>
// //                     </div>
// //                     <textarea
// //                       className="dg-input"
// //                       placeholder="e.g., Focus on API endpoints. Use a casual tone..."
// //                       value={customInstructions}
// //                       onChange={e => setCustomInstructions(e.target.value)}
// //                       disabled={loading}
// //                     />
// //                   </div>

// //                   {/* Auto-generate toggle */}
// //                   <label className="dg-toggle-row">
// //                     <label className="dg-switch" onClick={e => e.stopPropagation()}>
// //                       <input type="checkbox" checked={autoGenerate} onChange={e => setAutoGenerate(e.target.checked)} />
// //                       <span className="dg-slider" />
// //                     </label>
// //                     <div className="dg-toggle-text">
// //                       <div className="dg-toggle-label">Auto-regenerate on push</div>
// //                       <div className="dg-toggle-desc">Webhooks trigger README updates on every git push</div>
// //                     </div>
// //                   </label>

// //                   {/* Submit */}
// //                   <button
// //                     id="primary-submit-btn"
// //                     type="button"
// //                     className={`dg-btn ${loading ? "loading" : ""}`}
// //                     disabled={!canSubmit}
// //                     onClick={handleSubmit}
// //                   >
// //                     {loading ? (
// //                       <>
// //                         <div className="dg-spin" />
// //                         <span>Analyzing Codebase...</span>
// //                       </>
// //                     ) : (
// //                       <>
// //                         <Zap size={15} />
// //                         <span>Generate README</span>
// //                         <ChevronRight size={14} style={{ marginLeft: 4 }} />
// //                       </>
// //                     )}
// //                   </button>
// //                 </div>
// //               </div>
// //             </div>

// //             {/* ── Right: Pipeline + Preview ── */}
// //             <div className="dg-right">

// //               {/* Pipeline */}
// //               {showRight && (
// //                 <div className="dg-card dg-pipeline">
// //                   <div className="dg-card-head">
// //                     <div className="dg-traffic">
// //                       <div className="dg-dot-red" /><div className="dg-dot-amber" /><div className="dg-dot-green" />
// //                     </div>
// //                     <div className="dg-pipeline-title">
// //                       <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="3" /><path d="M12 1v4M12 19v4M4.22 4.22l2.83 2.83M16.95 16.95l2.83 2.83M1 12h4M19 12h4M4.22 19.78l2.83-2.83M16.95 7.05l2.83-2.83" /></svg>
// //                       Agent Pipeline
// //                     </div>
// //                     {loading && (
// //                       <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 6, color: "var(--sky)", fontFamily: "var(--font-mono)", fontSize: 11 }}>
// //                         <div className="dg-spin" style={{ width: 12, height: 12, borderWidth: 1.5 }} />
// //                         running
// //                       </div>
// //                     )}
// //                   </div>
// //                   <div className="dg-pipeline-body">
// //                     {steps.map((step, idx) => (
// //                       <div key={step.id} className="dg-step" style={{ animationDelay: `${idx * 60}ms` }}>
// //                         <div className="dg-step-left">
// //                           <div className={`dg-step-node ${step.status}`}>
// //                             {step.status === "done" ? <Check size={12} /> :
// //                               step.status === "error" ? <X size={12} /> :
// //                                 step.icon}
// //                           </div>
// //                           {idx < steps.length - 1 && (
// //                             <div className={`dg-connector ${step.status === "done" ? "lit" : ""}`} />
// //                           )}
// //                         </div>
// //                         <div className="dg-step-info">
// //                           <div className={`dg-step-name ${step.status}`}>{step.label}</div>
// //                           <div className={`dg-step-msg ${step.status}`}>
// //                             {step.message}
// //                             {step.status === "running" && <span className="dg-cursor" />}
// //                           </div>
// //                         </div>
// //                       </div>
// //                     ))}
// //                   </div>
// //                 </div>
// //               )}

// //               {/* Preview */}
// //               <div className="dg-card dg-preview">
// //                 <div className="dg-card-head">
// //                   <div className="dg-traffic">
// //                     <div className="dg-dot-red" /><div className="dg-dot-amber" /><div className="dg-dot-green" />
// //                   </div>
// //                   <div className="dg-preview-title">
// //                     <span style={{ color: "var(--sky)" }}>●</span>
// //                     Live Preview — README.md
// //                   </div>
// //                   {success && (
// //                     <div className="dg-preview-actions" style={{ marginLeft: "auto" }}>
// //                       <button type="button" onClick={copyToClipboard} className="dg-action-btn">
// //                         <Copy size={11} /> Copy
// //                       </button>
// //                       <button type="button" onClick={downloadFile} className="dg-action-btn primary">
// //                         <Download size={11} /> Download
// //                       </button>
// //                     </div>
// //                   )}
// //                 </div>

// //                 <div className="dg-preview-body" ref={previewRef}>
// //                   {generatedMarkdown ? (
// //                     <ReactMarkdown remarkPlugins={[remarkGfm]}>
// //                       {generatedMarkdown}
// //                     </ReactMarkdown>
// //                   ) : (
// //                     <div className="dg-preview-empty">
// //                       <div className="dg-preview-empty-icon">
// //                         <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
// //                           <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
// //                           <polyline points="14 2 14 8 20 8" />
// //                           <line x1="16" y1="13" x2="8" y2="13" />
// //                           <line x1="16" y1="17" x2="8" y2="17" />
// //                           <polyline points="10 9 9 9 8 9" />
// //                         </svg>
// //                       </div>
// //                       <div className="dg-preview-empty-text">
// //                         Your generated README<br />will stream here in real time
// //                       </div>
// //                     </div>
// //                   )}
// //                 </div>

// //                 {/* Success Banner */}
// //                 {success && readmeUrl && (
// //                   <div className="dg-success">
// //                     <div className="dg-success-icon">
// //                       <Check size={18} />
// //                     </div>
// //                     <div className="dg-success-text">
// //                       <div className="dg-success-label">
// //                         {mode === "local" ? "README saved locally" : "README pushed to GitHub"}
// //                       </div>
// //                       <a href={readmeUrl} target="_blank" rel="noopener noreferrer" className="dg-success-link">
// //                         {mode === "local" ? "Open file" : "View on GitHub"} →
// //                       </a>
// //                     </div>
// //                   </div>
// //                 )}

// //                 {/* Refine / Commit */}
// //                 {(commitReady || success) && (
// //                   <div className="dg-refine">
// //                     <input
// //                       className="dg-refine-input"
// //                       placeholder="Not perfect? Describe what to change..."
// //                       value={refineText}
// //                       onChange={e => setRefineText(e.target.value)}
// //                       disabled={loading || committing}
// //                       onKeyDown={e => e.key === "Enter" && handleRefine(e)}
// //                     />
// //                     <button type="button" onClick={handleRefine} className="dg-refine-btn" disabled={loading || committing || !refineText.trim()}>
// //                       <RefreshCw size={12} /> Refine
// //                     </button>
// //                     {commitReady && (
// //                       <button type="button" className="dg-btn" onClick={handleCommit} disabled={committing} style={{ padding: '8px 16px', borderRadius: '6px', fontSize: '11px', width: 'auto', marginLeft: '8px' }}>
// //                         {committing ? <div className="dg-spin" /> : (mode === "github" ? "Push to GitHub" : "Save Locally")}
// //                       </button>
// //                     )}
// //                   </div>
// //                 )}
// //               </div>

// //             </div>
// //           </div>

// //           {/* ── Footer ── */}
// //           <footer className="dg-footer">
// //             DocuGenius AI — Powered by <span>Claude</span> · {new Date().getFullYear()}
// //           </footer>
// //         </div>
// //       </div>

// //       {/* Error Toast */}
// //       {error && (
// //         <div className="dg-toast">
// //           <AlertCircle size={15} />
// //           {error}
// //           <button className="dg-toast-close" onClick={() => setError("")}>×</button>
// //         </div>
// //       )}
// //     </>
// //   );
// // }

// 'use client';

// import { useState, useEffect, useRef } from "react";
// import ReactMarkdown from 'react-markdown';
// import remarkGfm from 'remark-gfm';
// import { motion, AnimatePresence } from "framer-motion";

// import {
//   ThemeProvider, createTheme, CssBaseline,
//   Box, Stack, Typography, TextField, Button,
//   ToggleButtonGroup, ToggleButton, Select, MenuItem,
//   FormControl, InputLabel, Switch,
//   Chip, Tooltip, LinearProgress, Divider,
//   Paper, Alert, Snackbar, CircularProgress,
// } from "@mui/material";

// import {
//   Bolt as BoltIcon,
//   GitHub as GitHubIcon,
//   FolderOpen as FolderIcon,
//   ContentCopy as CopyIcon,
//   Download as DownloadIcon,
//   Autorenew as RefineIcon,
//   CheckCircle as CheckCircleIcon,
//   ErrorOutline as ErrorIcon,
//   ArrowForward as ArrowIcon,
//   Description as DocumentIcon,
//   ChatBubbleOutline as ChatIcon,
//   CloudUpload as PushIcon,
//   SaveAlt as SaveIcon,
//   Terminal as TerminalIcon,
// } from "@mui/icons-material";

// /* ─── DESIGN TOKENS ──────────────────────────────────────────────────────── */
// const C = {
//   bg:      "#06070d",
//   surface: "#0b0c18",
//   card:    "#0e0f1e",
//   border:  "rgba(255,255,255,0.06)",
//   border2: "rgba(255,255,255,0.11)",
//   cyan:    "#22d3ee",
//   amber:   "#f59e0b",
//   violet:  "#818cf8",
//   green:   "#34d399",
//   red:     "#f87171",
//   text:    "#dde1f0",
//   text2:   "#6b728f",
//   text3:   "#9299b8",
// };

// /* ─── MUI THEME ───────────────────────────────────────────────────────────── */
// const theme = createTheme({
//   palette: {
//     mode: "dark",
//     primary:    { main: C.cyan },
//     secondary:  { main: C.amber },
//     error:      { main: C.red },
//     warning:    { main: C.amber },
//     info:       { main: C.violet },
//     background: { default: C.bg, paper: C.card },
//     text:       { primary: C.text, secondary: C.text2 },
//   },
//   typography: {
//     fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
//     h1: { fontFamily: "'Syne', sans-serif", fontWeight: 800 },
//     h2: { fontFamily: "'Syne', sans-serif", fontWeight: 700 },
//     h3: { fontFamily: "'Syne', sans-serif", fontWeight: 700 },
//     h4: { fontFamily: "'Syne', sans-serif", fontWeight: 600 },
//     button: { fontFamily: "'Syne', sans-serif", fontWeight: 700, letterSpacing: 1.2 },
//   },
//   shape: { borderRadius: 8 },
//   components: {
//     MuiButton: {
//       styleOverrides: { root: { textTransform: "uppercase", borderRadius: 8, padding: "11px 22px" } },
//     },
//     MuiPaper: {
//       styleOverrides: {
//         root: { backgroundImage: "none", border: `1px solid ${C.border}`, background: C.card },
//       },
//     },
//     MuiTextField: {
//       defaultProps: { variant: "outlined", size: "small" },
//       styleOverrides: {
//         root: {
//           "& .MuiOutlinedInput-root": {
//             fontFamily: "'JetBrains Mono', monospace", fontSize: 13,
//             backgroundColor: "rgba(0,0,0,0.25)", borderRadius: 8,
//             "& fieldset":            { borderColor: C.border2 },
//             "&:hover fieldset":       { borderColor: "rgba(34,211,238,0.35)" },
//             "&.Mui-focused fieldset": { borderColor: C.cyan, borderWidth: "1px" },
//           },
//           "& .MuiInputLabel-root": { fontFamily: "'JetBrains Mono', monospace", fontSize: 12, color: C.text2 },
//           "& .MuiInputLabel-root.Mui-focused": { color: C.cyan },
//         },
//       },
//     },
//     MuiSelect: {
//       styleOverrides: {
//         root: { fontFamily: "'JetBrains Mono', monospace", fontSize: 13, backgroundColor: "rgba(0,0,0,0.25)" },
//       },
//     },
//     MuiToggleButton: {
//       styleOverrides: {
//         root: {
//           fontFamily: "'JetBrains Mono', monospace", fontSize: 11, fontWeight: 600,
//           letterSpacing: 1.5, textTransform: "uppercase",
//           color: C.text2, borderColor: C.border, borderRadius: "8px !important", padding: "8px 18px",
//           transition: "all 0.2s",
//           "&.Mui-selected": { color: C.cyan, backgroundColor: "rgba(34,211,238,0.08)", borderColor: "rgba(34,211,238,0.35)", "&:hover": { backgroundColor: "rgba(34,211,238,0.12)" } },
//           "&:hover": { backgroundColor: "rgba(34,211,238,0.04)", borderColor: C.border2 },
//         },
//       },
//     },
//     MuiChip:     { styleOverrides: { root: { fontFamily: "'JetBrains Mono', monospace", fontWeight: 600 } } },
//     MuiDivider:  { styleOverrides: { root: { borderColor: C.border } } },
//     MuiMenuItem: { styleOverrides: { root: { fontFamily: "'JetBrains Mono', monospace", fontSize: 13 } } },
//     MuiLinearProgress: {
//       styleOverrides: {
//         root: { borderRadius: 2, height: 2, backgroundColor: "rgba(34,211,238,0.08)" },
//         bar:  { borderRadius: 2, background: `linear-gradient(90deg, ${C.cyan}, ${C.amber})` },
//       },
//     },
//   },
// });

// /* ─── PIPELINE STEPS ─────────────────────────────────────────────────────── */
// const STEP_DEFS = [
//   { id: "fetching",   label: "Fetch Repository",  icon: "01" },
//   { id: "parsing",    label: "Parse & Rank Files", icon: "02" },
//   { id: "caching",    label: "Extract Metadata",   icon: "03" },
//   { id: "generating", label: "Generate via AI",    icon: "04" },
//   { id: "pushing",    label: "Push to GitHub",     icon: "05" },
// ];
// const makeSteps = () => STEP_DEFS.map(s => ({ ...s, status: "waiting", message: "Waiting to start" }));

// const stepBorderColor = (s: string) =>
//   s === "running" ? C.cyan : s === "done" ? C.green : s === "error" ? C.red : "rgba(255,255,255,0.12)";
// const stepBg = (s: string) =>
//   s === "running" ? "rgba(34,211,238,0.08)" : s === "done" ? "rgba(52,211,153,0.08)" : s === "error" ? "rgba(248,113,113,0.08)" : "rgba(255,255,255,0.03)";
// const stepLabelColor = (s: string) =>
//   s === "running" ? C.text : s === "done" ? C.green : s === "error" ? C.red : "rgba(255,255,255,0.35)";
// const stepMsgColor = (s: string) =>
//   s === "running" ? C.cyan : s === "done" ? C.text3 : s === "error" ? C.red : "rgba(255,255,255,0.2)";

// /* ─── CONFETTI ────────────────────────────────────────────────────────────── */
// function Confetti({ active }: { active: boolean }) {
//   const canvasRef = useRef<HTMLCanvasElement>(null);
//   useEffect(() => {
//     if (!active) return;
//     const canvas = canvasRef.current; if (!canvas) return;
//     canvas.width = window.innerWidth; canvas.height = window.innerHeight;
//     const ctx = canvas.getContext("2d"); if (!ctx) return;
//     const pieces = Array.from({ length: 250 }, () => ({
//       x: Math.random() * canvas.width, y: Math.random() * -canvas.height,
//       w: 7 + Math.random() * 9, h: 4 + Math.random() * 5,
//       color: [C.cyan, C.amber, C.green, C.red, C.violet][Math.floor(Math.random() * 5)],
//       rot: Math.random() * 360, vx: (Math.random() - .5) * 3,
//       vy: 2 + Math.random() * 4, vr: (Math.random() - .5) * 7, alpha: 1,
//     }));
//     let raf: number;
//     const draw = () => {
//       ctx.clearRect(0, 0, canvas.width, canvas.height);
//       let alive = false;
//       pieces.forEach(p => {
//         p.x += p.vx; p.y += p.vy; p.rot += p.vr;
//         if (p.y < canvas.height + 20) alive = true; else p.alpha -= 0.015;
//         ctx.save(); ctx.globalAlpha = Math.max(0, p.alpha);
//         ctx.translate(p.x, p.y); ctx.rotate((p.rot * Math.PI) / 180);
//         ctx.fillStyle = p.color; ctx.fillRect(-p.w / 2, -p.h / 2, p.w, p.h);
//         ctx.restore();
//       });
//       if (alive) raf = requestAnimationFrame(draw);
//     };
//     raf = requestAnimationFrame(draw);
//     return () => cancelAnimationFrame(raf);
//   }, [active]);
//   if (!active) return null;
//   return <canvas ref={canvasRef} style={{ position: "fixed", inset: 0, zIndex: 99999, pointerEvents: "none" }} />;
// }

// /* ─── CARD SHELL ─────────────────────────────────────────────────────────── */
// function Card({ children, accentColor = C.cyan, sx = {}, ...props }: any) {
//   return (
//     <Paper elevation={0} sx={{
//       background: C.card, border: `1px solid ${C.border}`,
//       borderRadius: "12px", overflow: "hidden", position: "relative",
//       "&::before": {
//         content: '""', position: "absolute", top: 0, left: 0, right: 0, height: "1px",
//         background: `linear-gradient(90deg, transparent, ${accentColor} 40%, rgba(255,255,255,0.08) 60%, transparent)`,
//         opacity: 0.8,
//       },
//       ...sx,
//     }} {...props}>
//       {children}
//     </Paper>
//   );
// }

// /* ─── WINDOW CHROME ──────────────────────────────────────────────────────── */
// function Chrome({ title, right }: { title: string; right?: React.ReactNode }) {
//   return (
//     <Box sx={{ display: "flex", alignItems: "center", gap: 1.5, px: 2.5, py: 1.25, borderBottom: `1px solid ${C.border}`, background: "rgba(0,0,0,0.18)" }}>
//       <Stack direction="row" spacing={0.6}>
//         {["#ff5f57", "#febc2e", "#28c840"].map((c, i) => (
//           <Box key={i} sx={{ width: 9, height: 9, borderRadius: "50%", background: c, opacity: 0.85 }} />
//         ))}
//       </Stack>
//       <Box sx={{ display: "flex", alignItems: "center", gap: 0.75, flex: 1 }}>
//         <TerminalIcon sx={{ fontSize: 10, color: C.text2, opacity: 0.5 }} />
//         <Typography sx={{ fontSize: 10, color: C.text2, letterSpacing: 2, textTransform: "uppercase", fontFamily: "'JetBrains Mono',monospace" }}>
//           {title}
//         </Typography>
//       </Box>
//       {right}
//     </Box>
//   );
// }

// /* ─── SECTION LABEL ──────────────────────────────────────────────────────── */
// function SectionLabel({ n, children }: { n: string; children: React.ReactNode }) {
//   return (
//     <Box sx={{ display: "flex", alignItems: "center", gap: 1.5, mb: 1.5 }}>
//       <Typography sx={{ fontSize: 10, color: C.cyan, fontFamily: "'JetBrains Mono',monospace", letterSpacing: 2, opacity: 0.65 }}>
//         [{n}]
//       </Typography>
//       <Typography sx={{ fontSize: 10, color: C.text2, fontFamily: "'JetBrains Mono',monospace", letterSpacing: 2, textTransform: "uppercase" }}>
//         {children}
//       </Typography>
//     </Box>
//   );
// }

// /* ─── MAIN COMPONENT ─────────────────────────────────────────────────────── */
// export default function DocuGenius() {
//   const [repo,               setRepo]               = useState("");
//   const [token,              setToken]              = useState("");
//   const [mode,               setMode]               = useState("github");
//   const [localPath,          setLocalPath]          = useState("");
//   const [targetAudience,     setTargetAudience]     = useState("Mixed");
//   const [customInstructions, setCustomInstructions] = useState("");
//   const [autoGenerate,       setAutoGenerate]       = useState(true);
//   const [loading,            setLoading]            = useState(false);
//   const [success,            setSuccess]            = useState(false);
//   const [error,              setError]              = useState("");
//   const [readmeUrl,          setReadmeUrl]          = useState("");
//   const [generatedMarkdown,  setGeneratedMarkdown]  = useState("");
//   const [refineText,         setRefineText]         = useState("");
//   const [steps,              setSteps]              = useState(makeSteps());
//   const [showRight,          setShowRight]          = useState(false);
//   const [confettiActive,     setConfettiActive]     = useState(false);
//   const [commitReady,        setCommitReady]        = useState(false);
//   const [committing,         setCommitting]         = useState(false);
//   const [snackOpen,          setSnackOpen]          = useState(false);
//   const [appTab,             setAppTab]             = useState("readme");
//   const [chatMessages,       setChatMessages]       = useState<{ role: string; text: string; contextFiles?: string[] }[]>([]);
//   const [chatInput,          setChatInput]          = useState("");
//   const [chatLoading,        setChatLoading]        = useState(false);
//   const chatEndRef = useRef<HTMLDivElement>(null);
//   const previewRef = useRef<HTMLDivElement>(null);

//   useEffect(() => {
//     if (previewRef.current) previewRef.current.scrollTop = previewRef.current.scrollHeight;
//   }, [generatedMarkdown]);
//   useEffect(() => {
//     if (chatEndRef.current) chatEndRef.current.scrollIntoView({ behavior: "smooth" });
//   }, [chatMessages]);

//   const updateStep = (id: string, patch: any) =>
//     setSteps(prev => prev.map(s => s.id === id ? { ...s, ...patch } : s));

//   /* ── Chat ── */
//   const handleChatSubmit = async (e: any) => {
//     e.preventDefault();
//     if (!chatInput.trim()) return;
//     if (mode === "github" && (!repo || !token)) { setError("Please provide both repository and access token"); return; }
//     if (mode === "local" && !localPath) { setError("Please provide an absolute path"); return; }
//     const message = chatInput;
//     setChatInput("");
//     setChatMessages(prev => [...prev, { role: "user", text: message }]);
//     setChatLoading(true);
//     try {
//       const payload = mode === "github"
//         ? { repo, access_token: token, message }
//         : { local_path: localPath, repo: "", access_token: "", message };
//       const res = await fetch("http://localhost:8000/chat", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
//       if (!res.ok) throw new Error(await res.text());
//       const data = await res.json();
//       setChatMessages(prev => [...prev, { role: "ai", text: data.answer, contextFiles: data.context_files }]);
//     } catch (err: any) {
//       setChatMessages(prev => [...prev, { role: "ai", text: `Error: ${err.message}` }]);
//     } finally { setChatLoading(false); }
//   };

//   /* ── Generate ── */
//   const handleSubmit = async (e: any, overrideInstructions: string | null = null) => {
//     e?.preventDefault();
//     if (mode === "github" && (!repo || !token)) { setError("Please provide both repository and access token"); return; }
//     if (mode === "local" && !localPath) { setError("Please provide an absolute path"); return; }
//     setLoading(true); setError(""); setSuccess(false); setCommitReady(false);
//     setReadmeUrl(""); setGeneratedMarkdown(""); setSteps(makeSteps()); setShowRight(true);
//     const finalInstructions = overrideInstructions !== null ? overrideInstructions : customInstructions;
//     try {
//       const payload = mode === "github"
//         ? { repo, access_token: token, branch: "main", commit_message: "Update README", custom_instructions: finalInstructions, sections: [], target_audience: targetAudience, auto_commit: autoGenerate }
//         : { local_path: localPath, repo: "", access_token: "", branch: "main", custom_instructions: finalInstructions, sections: [], target_audience: targetAudience, auto_commit: autoGenerate };
//       const res = await fetch("http://localhost:8000/stream-readme", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
//       if (!res.ok) { let d; try { d = await res.json(); } catch (_) {} throw new Error(d?.detail || res.statusText); }
//       if (!res.body) throw new Error("No response body");
//       const reader = res.body.getReader();
//       const decoder = new TextDecoder();
//       let buffer = "";
//       while (true) {
//         const { value, done } = await reader.read();
//         if (done) break;
//         buffer += decoder.decode(value, { stream: true });
//         const parts = buffer.split("\n\n"); buffer = parts.pop() || "";
//         for (const part of parts) {
//           if (!part.startsWith("data: ")) continue;
//           try {
//             const data = JSON.parse(part.slice(6));
//             if (data.step === "error") { setError(data.message); setSteps(prev => prev.map(s => s.status === "running" ? { ...s, status: "error", message: data.message } : s)); break; }
//             if (data.step && data.step !== "done") updateStep(data.step, { status: data.status, message: data.message });
//             if (data.step === "generating" && data.chunk) setGeneratedMarkdown(prev => prev + data.chunk);
//             if (data.step === "done") {
//               if (data.file_url) { setSuccess(true); setReadmeUrl(data.file_url); setConfettiActive(true); setTimeout(() => setConfettiActive(false), 5000); }
//               else setCommitReady(true);
//             }
//           } catch (_) {}
//         }
//       }
//       try { await fetch(`http://localhost:8000/preferences/${repo}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ auto_generate_on_push: autoGenerate }) }); } catch (_) {}
//     } catch (err: any) { setError(err.message || "An error occurred"); }
//     finally { setLoading(false); }
//   };

//   /* ── Refine ── */
//   const handleRefine = (e: any) => {
//     e.preventDefault();
//     if (!refineText.trim()) return;
//     const newInstr = customInstructions ? `${customInstructions}\n\nRefinement: ${refineText}` : `Refinement: ${refineText}`;
//     setCustomInstructions(newInstr); setRefineText(""); handleSubmit(null, newInstr);
//   };

//   /* ── Commit ── */
//   const handleCommit = async () => {
//     setCommitting(true); setError("");
//     try {
//       const payload = { repo: mode === "github" ? repo : "", access_token: token, local_path: mode === "local" ? localPath : "", markdown_content: generatedMarkdown };
//       const res = await fetch("http://localhost:8000/commit-readme", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
//       if (!res.ok) { let d; try { d = await res.json(); } catch (_) {} throw new Error(d?.detail || res.statusText); }
//       setCommitReady(false); setSuccess(true);
//       if (mode === "github") { const [owner, rName] = repo.split("/"); setReadmeUrl(`https://github.com/${owner}/${rName}/blob/main/README.md`); }
//       else setReadmeUrl(`file://${localPath}/README.md`);
//       setConfettiActive(true); setTimeout(() => setConfettiActive(false), 5000);
//     } catch (err: any) { setError(err.message || "Failed to commit README"); }
//     finally { setCommitting(false); }
//   };

//   const copyToClipboard = () => { navigator.clipboard.writeText(generatedMarkdown); setSnackOpen(true); };
//   const downloadFile = () => {
//     const blob = new Blob([generatedMarkdown], { type: "text/markdown" });
//     const url = URL.createObjectURL(blob);
//     const a = document.createElement("a"); a.href = url; a.download = "README.md";
//     document.body.appendChild(a); a.click(); document.body.removeChild(a); URL.revokeObjectURL(url);
//   };

//   const canSubmit = !loading && (mode === "github" ? (repo && token) : localPath);
//   const doneCount = steps.filter(s => s.status === "done").length;
//   const progress  = (doneCount / STEP_DEFS.length) * 100;

//   /* ══════════════════════════════════════════════════════════════════════════
//      RENDER
//   ══════════════════════════════════════════════════════════════════════════ */
//   return (
//     <ThemeProvider theme={theme}>
//       <CssBaseline />
//       <style>{`
//         body { background: ${C.bg}; }
//         ::selection { background: rgba(34,211,238,0.2); color: #fff; }
//         ::-webkit-scrollbar { width: 4px; height: 4px; }
//         ::-webkit-scrollbar-track { background: transparent; }
//         ::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.08); border-radius: 4px; }
//         ::-webkit-scrollbar-thumb:hover { background: rgba(34,211,238,0.3); }
//       `}</style>

//       <Confetti active={confettiActive} />

//       {/* ── Background ── */}
//       <Box sx={{ position: "fixed", inset: 0, zIndex: 0, pointerEvents: "none", overflow: "hidden" }}>
//         {/* Dot grid */}
//         <Box sx={{
//           position: "absolute", inset: 0,
//           backgroundImage: `radial-gradient(circle, rgba(255,255,255,0.055) 1px, transparent 1px)`,
//           backgroundSize: "32px 32px",
//           maskImage: "radial-gradient(ellipse 90% 90% at 50% 40%, black 15%, transparent 100%)",
//         }} />
//         {/* Central cyan glow */}
//         <Box sx={{ position: "absolute", top: -220, left: "50%", transform: "translateX(-50%)", width: 1000, height: 700, background: "radial-gradient(ellipse, rgba(34,211,238,0.065) 0%, transparent 65%)", filter: "blur(40px)" }} />
//         {/* Bottom-right amber */}
//         <Box sx={{ position: "absolute", bottom: -200, right: -50, width: 650, height: 500, background: "radial-gradient(ellipse, rgba(245,159,11,0.055) 0%, transparent 65%)", filter: "blur(60px)" }} />
//         {/* Bottom-left violet */}
//         <Box sx={{ position: "absolute", bottom: -80, left: -80, width: 500, height: 400, background: "radial-gradient(ellipse, rgba(129,140,248,0.05) 0%, transparent 65%)", filter: "blur(60px)" }} />
//       </Box>

//       {/* ── Page wrapper ── */}
//       <Box sx={{ position: "relative", zIndex: 1, maxWidth: 1340, mx: "auto", px: { xs: 2, md: 4 }, pb: 14 }}>

//         {/* ── Nav ── */}
//         <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", py: 3.5 }}>
//           <Stack direction="row" alignItems="center" spacing={2}>
//             <Box sx={{
//               width: 40, height: 40, borderRadius: "10px",
//               border: `1px solid rgba(34,211,238,0.3)`,
//               background: "rgba(34,211,238,0.05)",
//               display: "flex", alignItems: "center", justifyContent: "center",
//               position: "relative",
//               "&::after": { content: '""', position: "absolute", inset: "-1px", borderRadius: "10px", background: "linear-gradient(135deg,rgba(34,211,238,0.35),transparent 60%)", opacity: 0.5 },
//             }}>
//               <BoltIcon sx={{ color: C.cyan, fontSize: 20 }} />
//             </Box>
//             <Box>
//               <Typography sx={{ fontFamily: "'Syne',sans-serif", fontWeight: 800, fontSize: 17, color: C.text, letterSpacing: -0.3, "& span": { color: C.cyan } }}>
//                 Docu<span>Genius</span>
//               </Typography>
//               <Typography sx={{ fontSize: 9, color: C.text2, letterSpacing: 2.5, textTransform: "uppercase", mt: "-1px", fontFamily: "'JetBrains Mono',monospace" }}>
//                 AI · readme generator
//               </Typography>
//             </Box>
//           </Stack>

//           <Box sx={{ display: "flex", alignItems: "center", gap: 0.9, px: 1.5, py: 0.7, border: `1px solid rgba(52,211,153,0.18)`, borderRadius: "99px", background: "rgba(52,211,153,0.04)" }}>
//             <Box sx={{ width: 6, height: 6, borderRadius: "50%", background: C.green, animation: "pulse 2.5s ease-in-out infinite", "@keyframes pulse": { "0%,100%": { opacity: 1, transform: "scale(1)" }, "50%": { opacity: 0.5, transform: "scale(0.7)" } } }} />
//             <Typography sx={{ fontSize: 9, color: C.green, fontFamily: "'JetBrains Mono',monospace", letterSpacing: 2, textTransform: "uppercase" }}>online</Typography>
//           </Box>
//         </Box>

//         {/* ── Hero ── */}
//         <motion.div initial={{ opacity: 0, y: 28 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}>
//           <Box sx={{ textAlign: "center", pt: 6, pb: 8, position: "relative" }}>
//             {/* Decorative ghost text */}
//             <Box sx={{ position: "absolute", top: "38%", left: "6%", transform: "translateY(-50%)", opacity: 0.03, fontFamily: "'Syne',sans-serif", fontSize: "9vw", fontWeight: 800, color: C.cyan, userSelect: "none", lineHeight: 1, pointerEvents: "none" }}>{"{ }"}</Box>
//             <Box sx={{ position: "absolute", top: "38%", right: "6%", transform: "translateY(-50%)", opacity: 0.03, fontFamily: "'JetBrains Mono',monospace", fontSize: "8vw", fontWeight: 800, color: C.amber, userSelect: "none", lineHeight: 1, pointerEvents: "none" }}>{"</>"}</Box>

//             {/* Eyebrow */}
//             {/* <Box sx={{ display: "inline-flex", alignItems: "center", gap: 0.75, px: 1.75, py: 0.7, mb: 3.5, border: `1px solid rgba(34,211,238,0.2)`, borderRadius: "6px", background: "rgba(34,211,238,0.05)" }}> */}
//               {/* <BoltIcon sx={{ fontSize: 11, color: C.cyan }} /> */}
//               {/* <Typography sx={{ fontSize: 10, color: C.cyan, fontFamily: "'JetBrains Mono',monospace", letterSpacing: 2.5, textTransform: "uppercase" }}>Powered by Claude</Typography> */}
//             {/* </Box> */}

//             {/* Headline */}
//             <Typography variant="h1" sx={{ fontSize: "clamp(20px, 6.5vw, 22px)", letterSpacing: -2.5, lineHeight: 0.92, mb: 3 }}>
//               {/* <Box component="span" sx={{ display: "block", color: C.text, mb: "0.1em" }}>Your codebase.</Box> */}
//               <Box component="span" sx={{
//                 display: "block", WebkitTextFillColor: "transparent",
//                 WebkitBackgroundClip: "text", backgroundClip: "text",
//                 background: `linear-gradient(110deg, ${C.cyan} 0%, #67e8f9 30%, ${C.amber} 70%, #fde68a 100%)`,
//                 backgroundSize: "200% 100%",
//                 animation: "shimmer 5s linear infinite",
//                 "@keyframes shimmer": { "0%": { backgroundPosition: "100% 0" }, "100%": { backgroundPosition: "-100% 0" } },
//               }}>Documented.</Box>
//             </Typography>

//             {/* Divider decoration */}
//             <Box sx={{ display: "flex", alignItems: "center", gap: 2, maxWidth: 460, mx: "auto", mb: 3 }}>
//               <Box sx={{ flex: 1, height: "1px", background: `linear-gradient(90deg, transparent, ${C.border2})` }} />
//               <Typography sx={{ fontSize: 9, color: C.text2, fontFamily: "'JetBrains Mono',monospace", letterSpacing: 3, opacity: 0.5 }}>v2</Typography>
//               <Box sx={{ flex: 1, height: "1px", background: `linear-gradient(90deg, ${C.border2}, transparent)` }} />
//             </Box>

//             <Typography sx={{ fontSize: 14, color: C.text2, maxWidth: 480, mx: "auto", lineHeight: 2, fontFamily: "'JetBrains Mono',monospace" }}>
//               Analyze any GitHub repo or local project.<br />Generate a professional README in seconds.
//             </Typography>
//           </Box>
//         </motion.div>

//         {/* ── Mode tab switcher (above grid) ── */}
//         <Box sx={{ display: "flex", gap: "4px", p: "4px", mb: 2.5, background: "rgba(0,0,0,0.4)", border: `1px solid ${C.border}`, borderRadius: "12px", width: "fit-content" }}>
//           {[
//             { id: "readme", Icon: DocumentIcon, label: "README Gen", rgb: "34,211,238" },
//             { id: "chat",   Icon: ChatIcon,     label: "Code Chat",  rgb: "52,211,153" },
//           ].map(tab => (
//             <Button key={tab.id} onClick={() => setAppTab(tab.id)} sx={{
//               color: appTab === tab.id ? "#fff" : C.text2,
//               background: appTab === tab.id ? `rgba(${tab.rgb},0.12)` : "transparent",
//               border: appTab === tab.id ? `1px solid rgba(${tab.rgb},0.3)` : "1px solid transparent",
//               py: 0.85, px: 2.5, borderRadius: "8px", textTransform: "none",
//               fontWeight: 600, fontSize: 13, fontFamily: "'JetBrains Mono',monospace", gap: 0.85,
//               "&:hover": { background: `rgba(${tab.rgb},0.07)` }, transition: "all 0.2s", whiteSpace: "nowrap",
//             }}>
//               <tab.Icon sx={{ fontSize: 15 }} />{tab.label}
//             </Button>
//           ))}
//         </Box>

//         <AnimatePresence mode="wait">

//         {/* ══════════════════════════════════════════
//             CHAT MODE: full-width sidebar + big chat
//         ══════════════════════════════════════════ */}
//         {appTab === "chat" && (
//           <motion.div key="chat-layout" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} transition={{ duration: 0.25 }}>
//             <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", md: "300px 1fr" }, gap: 2.5, alignItems: "start" }}>

//               {/* Left sidebar: source config */}
//               <Card accentColor={C.green}>
//                 <Chrome title="code.chat — source" />
//                 <Box sx={{ p: 2.5 }}>
//                   <SectionLabel n="01">Source</SectionLabel>
//                   <ToggleButtonGroup value={mode} exclusive onChange={(_, v) => v && setMode(v)} fullWidth
//                     sx={{ mb: 2.5, gap: "4px", "& .MuiToggleButtonGroup-grouped": { border: `1px solid ${C.border} !important`, borderRadius: "8px !important" } }}>
//                     <ToggleButton value="github" sx={{ flex: 1, gap: 0.75 }}><GitHubIcon sx={{ fontSize: 13 }} /> GitHub</ToggleButton>
//                     <ToggleButton value="local"  sx={{ flex: 1, gap: 0.75 }}><FolderIcon  sx={{ fontSize: 13 }} /> Local</ToggleButton>
//                   </ToggleButtonGroup>
//                   <AnimatePresence mode="wait">
//                     {mode === "github" ? (
//                       <motion.div key="gh2" initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -4 }} transition={{ duration: 0.15 }}>
//                         <Stack spacing={2}>
//                           <TextField label="Repository" placeholder="owner/repository" value={repo} onChange={e => setRepo(e.target.value)} fullWidth InputProps={{ startAdornment: <GitHubIcon sx={{ fontSize: 13, mr: 1, color: C.text2 }} /> }} />
//                           <Box>
//                             <TextField label="Access Token" type="password" placeholder="ghp_••••••••••" value={token} onChange={e => setToken(e.target.value)} fullWidth
//                               sx={{ "& .MuiOutlinedInput-root fieldset": { borderColor: "rgba(245,159,11,0.2)" }, "& .MuiOutlinedInput-root.Mui-focused fieldset": { borderColor: C.amber }, "& .MuiInputLabel-root.Mui-focused": { color: C.amber } }} />
//                             <Typography sx={{ fontSize: 10, color: C.text2, mt: 0.6, fontFamily: "'JetBrains Mono',monospace" }}>// read access required</Typography>
//                           </Box>
//                         </Stack>
//                       </motion.div>
//                     ) : (
//                       <motion.div key="local2" initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -4 }} transition={{ duration: 0.15 }}>
//                         <TextField label="Absolute Local Path" placeholder="/home/user/project" value={localPath} onChange={e => setLocalPath(e.target.value)} fullWidth InputProps={{ startAdornment: <FolderIcon sx={{ fontSize: 13, mr: 1, color: C.text2 }} /> }} />
//                         <Typography sx={{ fontSize: 10, color: C.text2, mt: 0.6, fontFamily: "'JetBrains Mono',monospace" }}>// absolute path to project</Typography>
//                       </motion.div>
//                     )}
//                   </AnimatePresence>

//                   <Divider sx={{ my: 2.5 }} />

//                   {/* Chat tips */}
//                   <Box sx={{ p: 1.75, borderRadius: "8px", background: "rgba(52,211,153,0.04)", border: `1px solid rgba(52,211,153,0.12)` }}>
//                     <Typography sx={{ fontSize: 10, color: C.green, fontFamily: "'JetBrains Mono',monospace", letterSpacing: 1.5, textTransform: "uppercase", mb: 1.5 }}>
//                       Try asking
//                     </Typography>
//                     {[
//                       "Where are the API routes?",
//                       "Explain the auth flow",
//                       "What does X file do?",
//                       "List all dependencies",
//                     ].map((q, i) => (
//                       <Box key={i} onClick={() => setChatInput(q)} sx={{
//                         px: 1.25, py: 0.75, mb: 0.75, borderRadius: "6px", cursor: "pointer",
//                         border: `1px solid ${C.border}`, background: "rgba(0,0,0,0.2)",
//                         fontSize: 11, color: C.text3, fontFamily: "'JetBrains Mono',monospace",
//                         transition: "all 0.15s",
//                         "&:hover": { borderColor: "rgba(52,211,153,0.3)", color: C.green, background: "rgba(52,211,153,0.06)" },
//                         "&:last-child": { mb: 0 },
//                       }}>
//                         {q}
//                       </Box>
//                     ))}
//                   </Box>

//                   {chatMessages.length > 0 && (
//                     <Button fullWidth variant="outlined" onClick={() => setChatMessages([])} sx={{ mt: 2, fontSize: 10, py: 0.75, borderColor: C.border, color: C.text2, fontFamily: "'JetBrains Mono',monospace", "&:hover": { borderColor: C.border2, color: C.text } }}>
//                       Clear chat
//                     </Button>
//                   )}
//                 </Box>
//               </Card>

//               {/* Right: large chat panel */}
//               <Card accentColor={C.green} sx={{ display: "flex", flexDirection: "column" }}>
//                 <Chrome title="code.chat — conversation"
//                   right={
//                     <Box sx={{ display: "flex", alignItems: "center", gap: 0.9 }}>
//                       <Box sx={{ width: 6, height: 6, borderRadius: "50%", background: C.green, boxShadow: `0 0 8px ${C.green}` }} />
//                       <Typography sx={{ fontSize: 9, color: C.green, fontFamily: "'JetBrains Mono',monospace", letterSpacing: 2, textTransform: "uppercase" }}>live</Typography>
//                     </Box>
//                   }
//                 />

//                 {/* Messages area */}
//                 <Box sx={{ flex: 1, overflowY: "auto", p: 3, display: "flex", flexDirection: "column", gap: 2, minHeight: "60vh", maxHeight: "70vh" }}>
//                   {chatMessages.length === 0 ? (
//                     <Box sx={{ m: "auto", textAlign: "center" }}>
//                       <Box sx={{ width: 72, height: 72, borderRadius: "50%", background: "rgba(52,211,153,0.07)", border: `1px solid rgba(52,211,153,0.18)`, display: "flex", alignItems: "center", justifyContent: "center", mx: "auto", mb: 2.5 }}>
//                         <ChatIcon sx={{ fontSize: 32, color: C.green, opacity: 0.7 }} />
//                       </Box>
//                       <Typography sx={{ fontSize: 16, color: C.text, fontFamily: "'Syne',sans-serif", fontWeight: 700, mb: 1 }}>
//                         Ask about your codebase
//                       </Typography>
//                       <Typography sx={{ fontSize: 13, color: C.text2, fontFamily: "'JetBrains Mono',monospace", lineHeight: 1.8 }}>
//                         Configure a source on the left, then<br />ask any question about your code.
//                       </Typography>
//                     </Box>
//                   ) : chatMessages.map((msg, i) => (
//                     <Box key={i} sx={{ display: "flex", gap: 1.5, alignItems: "flex-start", flexDirection: msg.role === "user" ? "row-reverse" : "row" }}>
//                       {/* Avatar */}
//                       <Box sx={{
//                         width: 32, height: 32, borderRadius: "50%", flexShrink: 0,
//                         background: msg.role === "user" ? "rgba(34,211,238,0.12)" : "rgba(52,211,153,0.1)",
//                         border: `1px solid ${msg.role === "user" ? "rgba(34,211,238,0.25)" : "rgba(52,211,153,0.22)"}`,
//                         display: "flex", alignItems: "center", justifyContent: "center",
//                         fontSize: 12, fontFamily: "'JetBrains Mono',monospace", color: msg.role === "user" ? C.cyan : C.green,
//                         fontWeight: 600,
//                       }}>
//                         {msg.role === "user" ? "U" : "AI"}
//                       </Box>
//                       <Box sx={{ flex: 1, maxWidth: "80%" }}>
//                         <Box sx={{
//                           background: msg.role === "user" ? "rgba(34,211,238,0.07)" : "rgba(255,255,255,0.03)",
//                           border: `1px solid ${msg.role === "user" ? "rgba(34,211,238,0.2)" : C.border}`,
//                           px: 2.25, py: 1.75, borderRadius: "12px",
//                           borderTopRightRadius: msg.role === "user" ? "4px" : "12px",
//                           borderTopLeftRadius: msg.role === "ai" ? "4px" : "12px",
//                           fontSize: 13.5, lineHeight: 1.75, color: C.text,
//                         }}>
//                           <ReactMarkdown components={{
//                             code({ node, inline, className, children, ...props }: any) {
//                               return inline
//                                 ? <code style={{ background: "rgba(34,211,238,0.1)", padding: "2px 6px", borderRadius: 4, fontSize: 12, color: C.cyan }} {...props}>{children}</code>
//                                 : <pre style={{ background: "rgba(0,0,0,0.5)", padding: "12px 16px", borderRadius: 8, overflowX: "auto", marginTop: 10, fontSize: 12, border: `1px solid ${C.border2}` }}><code {...props}>{children}</code></pre>
//                             }
//                           }}>{msg.text}</ReactMarkdown>
//                         </Box>
//                         {msg.contextFiles && msg.contextFiles.length > 0 && (
//                           <Box sx={{ mt: 0.75, display: "flex", flexWrap: "wrap", gap: 0.5 }}>
//                             <Typography sx={{ fontSize: 10, color: C.text2, fontFamily: "'JetBrains Mono',monospace", mr: 0.5, alignSelf: "center" }}>refs:</Typography>
//                             {msg.contextFiles.map((file, idx) => (
//                               <Chip key={idx} label={file.split("/").pop()} size="small" sx={{ height: 18, fontSize: 10, background: "rgba(34,211,238,0.07)", color: C.cyan, border: `1px solid rgba(34,211,238,0.18)`, fontFamily: "'JetBrains Mono',monospace" }} />
//                             ))}
//                           </Box>
//                         )}
//                       </Box>
//                     </Box>
//                   ))}
//                   {chatLoading && (
//                     <Box sx={{ display: "flex", gap: 1.5, alignItems: "flex-start" }}>
//                       <Box sx={{ width: 32, height: 32, borderRadius: "50%", flexShrink: 0, background: "rgba(52,211,153,0.1)", border: `1px solid rgba(52,211,153,0.22)`, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 12, fontFamily: "'JetBrains Mono',monospace", color: C.green, fontWeight: 600 }}>AI</Box>
//                       <Box sx={{ px: 2.25, py: 1.75, background: "rgba(255,255,255,0.03)", border: `1px solid ${C.border}`, borderRadius: "12px", borderTopLeftRadius: "4px" }}>
//                         <Stack direction="row" spacing={0.6} alignItems="center">
//                           {[0, 1, 2].map(i => (
//                             <Box key={i} sx={{ width: 6, height: 6, borderRadius: "50%", background: C.green, animation: `bounce 1.2s ease-in-out ${i * 0.2}s infinite`, "@keyframes bounce": { "0%,100%": { transform: "translateY(0)" }, "50%": { transform: "translateY(-5px)" } } }} />
//                           ))}
//                         </Stack>
//                       </Box>
//                     </Box>
//                   )}
//                   <div ref={chatEndRef} />
//                 </Box>

//                 {/* Input area */}
//                 <Box component="form" onSubmit={handleChatSubmit} sx={{ p: 2.5, pt: 2, borderTop: `1px solid ${C.border}`, background: "rgba(0,0,0,0.15)" }}>
//                   <Box sx={{ display: "flex", gap: 1.5, alignItems: "flex-end" }}>
//                     <TextField
//                       placeholder="Ask anything about your codebase..."
//                       value={chatInput} onChange={e => setChatInput(e.target.value)}
//                       disabled={chatLoading} multiline maxRows={4} fullWidth
//                       onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleChatSubmit(e); } }}
//                       sx={{
//                         "& .MuiOutlinedInput-root": {
//                           borderRadius: "10px", background: "rgba(0,0,0,0.25)",
//                           fontSize: 13.5, lineHeight: 1.6,
//                           "& fieldset": { borderColor: C.border2 },
//                           "&:hover fieldset": { borderColor: "rgba(52,211,153,0.35)" },
//                           "&.Mui-focused fieldset": { borderColor: C.green },
//                         }
//                       }}
//                     />
//                     <Button type="submit" variant="contained" disabled={chatLoading || !chatInput.trim() || !canSubmit}
//                       sx={{ minWidth: 52, width: 52, height: 44, p: 0, borderRadius: "10px", background: `linear-gradient(135deg, ${C.green}, #059669)`, color: "#000", flexShrink: 0, "&:hover": { background: "#10b981" }, "&:disabled": { opacity: 0.25 } }}>
//                       <ArrowIcon sx={{ fontSize: 18 }} />
//                     </Button>
//                   </Box>
//                   <Typography sx={{ fontSize: 10, color: C.text2, mt: 1, fontFamily: "'JetBrains Mono',monospace" }}>
//                     Enter to send · Shift+Enter for new line
//                   </Typography>
//                 </Box>
//               </Card>
//             </Box>
//           </motion.div>
//         )}

//         {/* ══════════════════════════════════════════
//             README MODE: two-column grid
//         ══════════════════════════════════════════ */}
//         {appTab === "readme" && (
//           <motion.div key="readme-layout" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} transition={{ duration: 0.25 }}>
//         <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", md: "400px 1fr" }, gap: 2.5, alignItems: "start" }}>

//           {/* ════════════════════
//                LEFT: FORM
//           ════════════════════ */}
//           <motion.div initial={{ opacity: 0, x: -24 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.5, delay: 0.15, ease: [0.22, 1, 0.36, 1] }}>
//             <Card accentColor={C.cyan}>
//               <Chrome title="readme.generator — ssh" />
//               <Box sx={{ p: 2.75 }}>


//                 {/* Source toggle */}
//                 <SectionLabel n="01">Source</SectionLabel>
//                 <ToggleButtonGroup value={mode} exclusive onChange={(_, v) => v && setMode(v)} fullWidth
//                   sx={{ mb: 3, gap: "4px", "& .MuiToggleButtonGroup-grouped": { border: `1px solid ${C.border} !important`, borderRadius: "8px !important" } }}>
//                   <ToggleButton value="github" sx={{ flex: 1, gap: 0.75 }}><GitHubIcon sx={{ fontSize: 13 }} /> GitHub</ToggleButton>
//                   <ToggleButton value="local"  sx={{ flex: 1, gap: 0.75 }}><FolderIcon  sx={{ fontSize: 13 }} /> Local</ToggleButton>
//                 </ToggleButtonGroup>

//                 {/* Source fields */}
//                 <AnimatePresence mode="wait">
//                   {mode === "github" ? (
//                     <motion.div key="gh" initial={{ opacity: 0, y: 5 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -5 }} transition={{ duration: 0.18 }}>
//                       <Stack spacing={2} sx={{ mb: 3 }}>
//                         <TextField label="Repository" placeholder="owner/repository" value={repo} onChange={e => setRepo(e.target.value)} disabled={loading} fullWidth InputProps={{ startAdornment: <GitHubIcon sx={{ fontSize: 14, mr: 1, color: C.text2 }} /> }} />
//                         <Box>
//                           <TextField label="GitHub Access Token" type="password" placeholder="ghp_••••••••••••••••" value={token} onChange={e => setToken(e.target.value)} disabled={loading} fullWidth
//                             sx={{ "& .MuiOutlinedInput-root fieldset": { borderColor: "rgba(245,159,11,0.2)" }, "& .MuiOutlinedInput-root:hover fieldset": { borderColor: "rgba(245,159,11,0.4)" }, "& .MuiOutlinedInput-root.Mui-focused fieldset": { borderColor: C.amber }, "& .MuiInputLabel-root.Mui-focused": { color: C.amber } }} />
//                           <Typography sx={{ fontSize: 10, color: C.text2, mt: 0.75, fontFamily: "'JetBrains Mono',monospace" }}>// required for read access &amp; pushing</Typography>
//                         </Box>
//                       </Stack>
//                     </motion.div>
//                   ) : (
//                     <motion.div key="local" initial={{ opacity: 0, y: 5 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -5 }} transition={{ duration: 0.18 }}>
//                       <Box sx={{ mb: 3 }}>
//                         <TextField label="Absolute Local Path" placeholder="/home/user/my-project" value={localPath} onChange={e => setLocalPath(e.target.value)} disabled={loading} fullWidth InputProps={{ startAdornment: <FolderIcon sx={{ fontSize: 14, mr: 1, color: C.text2 }} /> }} />
//                         <Typography sx={{ fontSize: 10, color: C.text2, mt: 0.75, fontFamily: "'JetBrains Mono',monospace" }}>// README.md will be written to this directory</Typography>
//                       </Box>
//                     </motion.div>
//                   )}
//                 </AnimatePresence>

//                 <Divider sx={{ mb: 3 }} />

//                 {/* ── Options ── */}
//                     <SectionLabel n="02">Options</SectionLabel>

//                     <FormControl fullWidth size="small" sx={{ mb: 2.5 }}>
//                       <InputLabel sx={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 12, color: `${C.amber} !important`, "&.Mui-focused": { color: `${C.amber} !important` } }}>Target Audience</InputLabel>
//                       <Select value={targetAudience} label="Target Audience" onChange={e => setTargetAudience(e.target.value)} disabled={loading}
//                         sx={{ "& .MuiOutlinedInput-notchedOutline": { borderColor: "rgba(245,159,11,0.2)" }, "&:hover .MuiOutlinedInput-notchedOutline": { borderColor: "rgba(245,159,11,0.4)" }, "&.Mui-focused .MuiOutlinedInput-notchedOutline": { borderColor: C.amber } }}>
//                         <MenuItem value="Mixed">Mixed — Default</MenuItem>
//                         <MenuItem value="Beginner Developers">Beginner Developers</MenuItem>
//                         <MenuItem value="Advanced Engineers">Advanced Engineers</MenuItem>
//                         <MenuItem value="End Users">End Users (No Code)</MenuItem>
//                       </Select>
//                     </FormControl>

//                     <TextField label="Additional Instructions — optional" placeholder="e.g., Focus on API endpoints. Use a casual tone..." value={customInstructions} onChange={e => setCustomInstructions(e.target.value)} disabled={loading} multiline minRows={2} maxRows={5} fullWidth sx={{ mb: 2.5 }} />

//                     {/* Toggle */}
//                     <Box sx={{ display: "flex", alignItems: "flex-start", gap: 1.5, p: 1.75, mb: 3, borderRadius: "8px", border: `1px solid ${C.border}`, background: "rgba(0,0,0,0.15)", transition: "border-color 0.2s", "&:hover": { borderColor: "rgba(34,211,238,0.18)" } }}>
//                       <Switch checked={autoGenerate} onChange={e => setAutoGenerate(e.target.checked)} size="small" sx={{ mt: "1px", "& .MuiSwitch-switchBase.Mui-checked": { color: C.cyan }, "& .MuiSwitch-switchBase.Mui-checked + .MuiSwitch-track": { backgroundColor: "rgba(34,211,238,0.3)" }, "& .MuiSwitch-track": { backgroundColor: "rgba(255,255,255,0.08)" } }} />
//                       <Box>
//                         <Typography sx={{ fontSize: 13, color: C.text, fontWeight: 500, mb: 0.25 }}>Auto-regenerate on push</Typography>
//                         <Typography sx={{ fontSize: 11, color: C.text2, lineHeight: 1.6 }}>Webhooks trigger README updates on git push</Typography>
//                       </Box>
//                     </Box>

//                     {/* Generate button */}
//                     <Button fullWidth variant="contained" disabled={!canSubmit} onClick={handleSubmit} sx={{
//                       background: loading ? "linear-gradient(135deg,rgba(34,211,238,0.18),rgba(245,159,11,0.18))" : `linear-gradient(135deg, ${C.cyan}, #0ea5e9)`,
//                       color: loading ? C.cyan : "#000",
//                       boxShadow: loading ? "none" : `0 0 28px rgba(34,211,238,0.22), 0 1px 0 rgba(255,255,255,0.08) inset`,
//                       fontFamily: "'Syne',sans-serif", fontWeight: 700, fontSize: 13,
//                       py: 1.6, letterSpacing: 1.5, transition: "all 0.25s",
//                       "&:hover:not(:disabled)": { background: "linear-gradient(135deg,#67e8f9,#22d3ee)", boxShadow: "0 0 40px rgba(34,211,238,0.38)", transform: "translateY(-1px)" },
//                       "&:active:not(:disabled)": { transform: "translateY(0)" },
//                       "&:disabled": { opacity: 0.22, color: "#fff" },
//                     }}>
//                       {loading ? (
//                         <Stack direction="row" spacing={1.5} alignItems="center">
//                           <CircularProgress size={14} thickness={5} sx={{ color: C.cyan }} />
//                           <Box component="span" sx={{ color: C.cyan }}>Analyzing codebase...</Box>
//                         </Stack>
//                       ) : (
//                         <Stack direction="row" spacing={1} alignItems="center">
//                           <BoltIcon sx={{ fontSize: 16 }} />
//                           <span>Generate README</span>
//                           <ArrowIcon sx={{ fontSize: 14 }} />
//                         </Stack>
//                       )}
//                     </Button>
//                 </Box>
//             </Card>
//           </motion.div>

//           {/* ════════════════════
//                RIGHT: PIPELINE + PREVIEW
//           ════════════════════ */}
//           <Box sx={{ display: "flex", flexDirection: "column", gap: 2.5 }}>

//             {/* Pipeline */}
//             <AnimatePresence>
//               {showRight && (
//                 <motion.div key="pipeline" initial={{ opacity: 0, y: 18 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -12 }} transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}>
//                   <Card accentColor={C.violet}>
//                     <Chrome title="agent pipeline"
//                       right={loading ? (
//                         <Box sx={{ display: "flex", alignItems: "center", gap: 0.9, background: "rgba(34,211,238,0.06)", border: `1px solid rgba(34,211,238,0.18)`, borderRadius: "6px", px: 1.2, py: 0.4 }}>
//                           <CircularProgress size={7} sx={{ color: C.cyan }} />
//                           <Typography sx={{ fontSize: 9, color: C.cyan, fontFamily: "'JetBrains Mono',monospace", letterSpacing: 2, textTransform: "uppercase" }}>running</Typography>
//                         </Box>
//                       ) : undefined}
//                     />
//                     {loading && <LinearProgress variant="determinate" value={progress} />}

//                     <Box sx={{ p: 3, pb: 2.5 }}>
//                       {steps.map((step, idx) => (
//                         <motion.div key={step.id} initial={{ opacity: 0, x: -12 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: idx * 0.07, duration: 0.3 }}>
//                           <Box sx={{ display: "flex", gap: 2, alignItems: "stretch" }}>
//                             <Box sx={{ display: "flex", flexDirection: "column", alignItems: "center", width: 34, flexShrink: 0 }}>
//                               <motion.div animate={step.status === "running" ? { boxShadow: ["0 0 0px rgba(34,211,238,0)", "0 0 20px rgba(34,211,238,0.5)", "0 0 0px rgba(34,211,238,0)"] } : {}} transition={{ duration: 1.4, repeat: Infinity }}>
//                                 <Box sx={{
//                                   width: 34, height: 34, borderRadius: "50%",
//                                   display: "flex", alignItems: "center", justifyContent: "center",
//                                   fontSize: 11, fontWeight: 600, fontFamily: "'JetBrains Mono',monospace",
//                                   border: `1.5px solid ${stepBorderColor(step.status)}`,
//                                   background: stepBg(step.status), color: stepBorderColor(step.status), transition: "all 0.4s",
//                                 }}>
//                                   {step.status === "done" ? "✓" : step.status === "error" ? "✗" : step.icon}
//                                 </Box>
//                               </motion.div>
//                               {idx < steps.length - 1 && (
//                                 <Box sx={{ width: "1px", flex: 1, minHeight: 18, mt: "4px", background: step.status === "done" ? `linear-gradient(to bottom, ${C.green}, rgba(52,211,153,0.06))` : "rgba(255,255,255,0.07)", transition: "background 0.5s" }} />
//                               )}
//                             </Box>
//                             <Box sx={{ flex: 1, pb: idx < steps.length - 1 ? 2.5 : 0, pt: "5px" }}>
//                               <Typography sx={{ fontSize: 13, fontWeight: 500, mb: 0.4, color: stepLabelColor(step.status), transition: "color 0.3s" }}>{step.label}</Typography>
//                               <Typography sx={{ fontSize: 11, color: stepMsgColor(step.status), lineHeight: 1.5, fontFamily: "'JetBrains Mono',monospace" }}>
//                                 {step.message}
//                                 {step.status === "running" && <Box component="span" sx={{ display: "inline-block", width: 6, height: 10, background: C.cyan, ml: "3px", verticalAlign: "middle", animation: "blink .8s step-end infinite", "@keyframes blink": { "0%,100%": { opacity: 1 }, "50%": { opacity: 0 } } }} />}
//                               </Typography>
//                             </Box>
//                           </Box>
//                         </motion.div>
//                       ))}
//                     </Box>
//                   </Card>
//                 </motion.div>
//               )}
//             </AnimatePresence>

//             {/* Preview */}
//             <motion.div initial={{ opacity: 0, y: 22 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, delay: 0.22, ease: [0.22, 1, 0.36, 1] }}>
//               <Card accentColor={C.green}>
//                 {/* Header */}
//                 <Box sx={{ display: "flex", alignItems: "center", gap: 1, px: 2.5, py: 1.25, borderBottom: `1px solid ${C.border}`, background: "rgba(0,0,0,0.18)" }}>
//                   <Stack direction="row" spacing={0.6}>
//                     {["#ff5f57","#febc2e","#28c840"].map((c, i) => <Box key={i} sx={{ width: 9, height: 9, borderRadius: "50%", background: c, opacity: 0.85 }} />)}
//                   </Stack>
//                   <Box sx={{ display: "flex", alignItems: "center", gap: 0.75, ml: 1, flex: 1 }}>
//                     <Box sx={{ width: 6, height: 6, borderRadius: "50%", background: "#38bdf8", boxShadow: "0 0 6px rgba(56,189,248,0.8)" }} />
//                     <Typography sx={{ fontSize: 10, color: C.text2, letterSpacing: 2, textTransform: "uppercase", fontFamily: "'JetBrains Mono',monospace" }}>Live Preview — README.md</Typography>
//                   </Box>
//                   {success && (
//                     <Stack direction="row" spacing={0.75}>
//                       <Tooltip title="Copy markdown">
//                         <Button size="small" variant="outlined" onClick={copyToClipboard} startIcon={<CopyIcon sx={{ fontSize: "12px !important" }} />}
//                           sx={{ fontSize: 10, py: 0.4, px: 1.1, borderColor: C.border2, color: C.text2, fontFamily: "'JetBrains Mono',monospace", "&:hover": { borderColor: C.text3, color: C.text } }}>Copy</Button>
//                       </Tooltip>
//                       <Tooltip title="Download README.md">
//                         <Button size="small" variant="outlined" onClick={downloadFile} startIcon={<DownloadIcon sx={{ fontSize: "12px !important" }} />}
//                           sx={{ fontSize: 10, py: 0.4, px: 1.1, borderColor: "rgba(52,211,153,0.28)", color: C.green, fontFamily: "'JetBrains Mono',monospace", "&:hover": { borderColor: "rgba(52,211,153,0.55)", background: "rgba(52,211,153,0.05)" } }}>.md</Button>
//                       </Tooltip>
//                     </Stack>
//                   )}
//                 </Box>

//                 {/* Body */}
//                 <Box ref={previewRef} sx={{
//                   height: 440, overflowY: "auto", p: 3.5,
//                   fontFamily: "'JetBrains Mono',monospace", fontSize: 13, lineHeight: 1.85, color: C.text,
//                   "& h1": { fontFamily: "'Syne',sans-serif", fontWeight: 800, color: "#fff", fontSize: "1.6em", mt: "1.3em", mb: "0.5em", letterSpacing: -0.8 },
//                   "& h2": { fontFamily: "'Syne',sans-serif", fontWeight: 700, color: C.cyan, fontSize: "1.18em", mt: "1.3em", mb: "0.4em" },
//                   "& h3": { fontFamily: "'Syne',sans-serif", fontWeight: 600, color: C.text3, fontSize: "1em", mt: "1.1em", mb: "0.35em" },
//                   "& p": { color: "rgba(221,225,240,0.82)", mb: "0.85em" },
//                   "& ul,& ol": { pl: "1.5em", mb: "0.85em", color: "rgba(221,225,240,0.75)" },
//                   "& li": { mb: "4px" },
//                   "& strong": { color: "#fff", fontWeight: 600 },
//                   "& code": { background: "rgba(34,211,238,0.08)", border: `1px solid rgba(34,211,238,0.17)`, borderRadius: "4px", px: "5px", py: "1px", color: C.cyan, fontSize: "0.88em" },
//                   "& pre": { background: "rgba(0,0,0,0.45)", border: `1px solid ${C.border2}`, borderRadius: "8px", p: 2, overflowX: "auto", my: "14px" },
//                   "& pre code": { background: "none", border: "none", color: C.green, p: 0, fontSize: "0.9em" },
//                   "& blockquote": { borderLeft: `3px solid ${C.amber}`, pl: 2, color: C.text2, my: "14px", background: "rgba(245,159,11,0.04)", py: 0.5, borderRadius: "0 6px 6px 0" },
//                   "& a": { color: "#38bdf8", textDecoration: "none", "&:hover": { color: C.cyan } },
//                   "& table": { width: "100%", borderCollapse: "collapse", my: "14px", fontSize: "0.88em" },
//                   "& th": { background: "rgba(34,211,238,0.07)", border: `1px solid ${C.border2}`, p: "8px 12px", color: C.cyan, textAlign: "left", fontFamily: "'Syne',sans-serif" },
//                   "& td": { border: `1px solid ${C.border}`, p: "7px 12px", color: "rgba(221,225,240,0.72)" },
//                   "& hr": { border: "none", borderTop: `1px solid ${C.border}`, my: "18px" },
//                 }}>
//                   {generatedMarkdown ? (
//                     <ReactMarkdown remarkPlugins={[remarkGfm]}>{generatedMarkdown}</ReactMarkdown>
//                   ) : (
//                     <Box sx={{ height: "100%", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 2.5 }}>
//                       {/* ASCII frame */}
//                       <Box sx={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 11, color: "rgba(255,255,255,0.07)", lineHeight: 1.75, userSelect: "none", textAlign: "left" }}>
//                         {["┌──────────────────────────┐",
//                           "│                          │",
//                           "│   README.md preview      │",
//                           "│   streams here...        │",
//                           "│                          │",
//                           "└──────────────────────────┘"].map((line, i) => (
//                           <Box key={i} component="div">{line}</Box>
//                         ))}
//                       </Box>
//                       <Typography sx={{ fontSize: 12, color: C.text2, textAlign: "center", lineHeight: 1.8, fontFamily: "'JetBrains Mono',monospace" }}>
//                         Your generated README<br />will appear here in real time
//                       </Typography>
//                     </Box>
//                   )}
//                 </Box>

//                 {/* Success banner */}
//                 <AnimatePresence>
//                   {success && readmeUrl && (
//                     <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} exit={{ opacity: 0, height: 0 }} transition={{ duration: 0.3 }}>
//                       <Box sx={{ display: "flex", alignItems: "center", gap: 2, px: 3, py: 2, borderTop: `1px solid rgba(52,211,153,0.16)`, background: "rgba(52,211,153,0.04)" }}>
//                         <Box sx={{ width: 34, height: 34, borderRadius: "50%", flexShrink: 0, background: "rgba(52,211,153,0.09)", border: `1.5px solid rgba(52,211,153,0.32)`, display: "flex", alignItems: "center", justifyContent: "center", boxShadow: "0 0 16px rgba(52,211,153,0.16)" }}>
//                           <CheckCircleIcon sx={{ fontSize: 16, color: C.green }} />
//                         </Box>
//                         <Box sx={{ flex: 1 }}>
//                           <Typography sx={{ fontSize: 12, fontWeight: 600, color: C.green, mb: 0.25, fontFamily: "'JetBrains Mono',monospace" }}>
//                             {mode === "local" ? "README saved locally" : "README pushed to GitHub"}
//                           </Typography>
//                           <Typography component="a" href={readmeUrl} target="_blank" rel="noopener noreferrer" sx={{ fontSize: 11, color: C.cyan, textDecoration: "none", fontFamily: "'JetBrains Mono',monospace", borderBottom: `1px solid rgba(34,211,238,0.28)`, pb: "1px", "&:hover": { color: C.green } }}>
//                             {mode === "local" ? "open file →" : "view on github →"}
//                           </Typography>
//                         </Box>
//                       </Box>
//                     </motion.div>
//                   )}
//                 </AnimatePresence>

//                 {/* Refine / Commit bar */}
//                 <AnimatePresence>
//                   {(commitReady || success) && (
//                     <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} exit={{ opacity: 0, height: 0 }} transition={{ duration: 0.3 }}>
//                       <Box sx={{ display: "flex", gap: 1, p: 2, borderTop: `1px solid ${C.border}`, background: "rgba(0,0,0,0.1)" }}>
//                         <TextField placeholder="Not perfect? Describe what to change..." value={refineText} onChange={e => setRefineText(e.target.value)} disabled={loading || committing} onKeyDown={e => e.key === "Enter" && handleRefine(e)} size="small" sx={{ flex: 1 }} />
//                         <Button variant="outlined" onClick={handleRefine} disabled={loading || committing || !refineText.trim()} startIcon={<RefineIcon sx={{ fontSize: "13px !important" }} />}
//                           sx={{ fontSize: 10, px: 1.5, whiteSpace: "nowrap", fontFamily: "'JetBrains Mono',monospace", borderColor: "rgba(129,140,248,0.28)", color: C.violet, "&:hover": { borderColor: C.violet, background: "rgba(129,140,248,0.07)" } }}>
//                           Refine
//                         </Button>
//                         {commitReady && (
//                           <Button variant="contained" onClick={handleCommit} disabled={committing} startIcon={committing ? <CircularProgress size={11} sx={{ color: "#000" }} /> : mode === "github" ? <PushIcon sx={{ fontSize: "13px !important" }} /> : <SaveIcon sx={{ fontSize: "13px !important" }} />}
//                             sx={{ fontSize: 10, px: 1.5, whiteSpace: "nowrap", background: `linear-gradient(135deg, ${C.green}, #059669)`, color: "#000", fontFamily: "'Syne',sans-serif", fontWeight: 700, "&:hover": { background: "linear-gradient(135deg,#6ee7b7,#34d399)" } }}>
//                             {mode === "github" ? "Push" : "Save"}
//                           </Button>
//                         )}
//                       </Box>
//                     </motion.div>
//                   )}
//                 </AnimatePresence>
//               </Card>
//             </motion.div>
//           </Box>
//         </Box>
//           </motion.div>
//         )}

//         </AnimatePresence>

//         {/* ── Footer ── */}
//         <Box sx={{ textAlign: "center", pt: 10 }}>
//           <Box sx={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 2, mb: 1.5 }}>
//             <Box sx={{ width: 48, height: "1px", background: `linear-gradient(90deg, transparent, ${C.border2})` }} />
//             <Typography sx={{ fontSize: 9, color: C.text2, fontFamily: "'JetBrains Mono',monospace", letterSpacing: 3.5, textTransform: "uppercase" }}>DocuGenius AI</Typography>
//             <Box sx={{ width: 48, height: "1px", background: `linear-gradient(90deg, ${C.border2}, transparent)` }} />
//           </Box>
//           {/* <Typography sx={{ fontSize: 10, color: C.text2, fontFamily: "'JetBrains Mono',monospace", letterSpacing: 2 }}>
//             Powered by <Box component="span" sx={{ color: C.cyan }}>Claude</Box> · <Box component="span" sx={{ color: C.amber }}>{new Date().getFullYear()}</Box>
//           </Typography> */}
//         </Box>
//       </Box>

//       {/* Snackbars */}
//       <Snackbar open={!!error} anchorOrigin={{ vertical: "bottom", horizontal: "center" }} onClose={() => setError("")}>
//         <Alert severity="error" onClose={() => setError("")} sx={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 12, background: "#160a0a", border: "1px solid rgba(248,113,113,0.22)" }} icon={<ErrorIcon />}>{error}</Alert>
//       </Snackbar>
//       <Snackbar open={snackOpen} autoHideDuration={2200} onClose={() => setSnackOpen(false)} anchorOrigin={{ vertical: "bottom", horizontal: "center" }}>
//         <Alert severity="success" sx={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 12, background: "#081410", border: "1px solid rgba(52,211,153,0.22)" }}>Markdown copied!</Alert>
//       </Snackbar>
//     </ThemeProvider>
//   );
// }

'use client';

import { useState, useEffect, useRef, useMemo, createContext, useContext } from "react";
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { motion, AnimatePresence } from "framer-motion";

import {
  ThemeProvider, createTheme, CssBaseline,
  Box, Stack, Typography, TextField, Button,
  ToggleButtonGroup, ToggleButton, Select, MenuItem,
  FormControl, InputLabel, Switch,
  Chip, Tooltip, LinearProgress, Divider,
  Paper, Alert, Snackbar, CircularProgress, IconButton,
} from "@mui/material";

import BoltIcon from "@mui/icons-material/Bolt";
import GitHubIcon from "@mui/icons-material/GitHub";
import FolderIcon from "@mui/icons-material/FolderOpen";
import CopyIcon from "@mui/icons-material/ContentCopy";
import DownloadIcon from "@mui/icons-material/Download";
import RefineIcon from "@mui/icons-material/Autorenew";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import ErrorIcon from "@mui/icons-material/ErrorOutline";
import ArrowIcon from "@mui/icons-material/ArrowForward";
import DocumentIcon from "@mui/icons-material/Description";
import ChatIcon from "@mui/icons-material/ChatBubbleOutline";
import PushIcon from "@mui/icons-material/CloudUpload";
import SaveIcon from "@mui/icons-material/SaveAlt";
import TerminalIcon from "@mui/icons-material/Terminal";
import LightModeIcon from "@mui/icons-material/LightMode";
import DarkModeIcon from "@mui/icons-material/DarkMode";

const DOC_API_BASE = process.env.NEXT_PUBLIC_DOC_FIRST_API_BASE_URL || "http://localhost:18100";
const SIMPLE_API_BASE = process.env.NEXT_PUBLIC_DOC_SIMPLE_API_BASE_URL || "http://localhost:18101";

/* ─── SLEEK SAAS DESIGN TOKENS ───────────────────────────────────────────── */
export const getColors = (tMode: 'light' | 'dark') => ({
  bg: tMode === 'dark' ? "#000000" : "#ffffff",
  surface: tMode === 'dark' ? "#09090b" : "#f4f4f5",
  card: tMode === 'dark' ? "rgba(14, 14, 17, 0.5)" : "rgba(255, 255, 255, 0.8)", // Transparent for glassmorphism
  border: tMode === 'dark' ? "rgba(255,255,255,0.08)" : "rgba(0,0,0,0.1)",
  border2: tMode === 'dark' ? "rgba(255,255,255,0.15)" : "rgba(0,0,0,0.2)",
  primary: "#3b82f6", // Clean Electric Blue
  accent: "#8b5cf6", // Deep Violet
  teal: "#14b8a6", // Muted Teal for gradient
  green: "#10b981", // Success green
  red: "#ef4444", // Error red
  amber: "#f59e0b", // Warning amber
  text: tMode === 'dark' ? "#f4f4f5" : "#18181b", // Bright text or dark text
  text2: tMode === 'dark' ? "#a1a1aa" : "#52525b", // Muted text
  text3: tMode === 'dark' ? "#71717a" : "#a1a1aa", // Heavily muted
});

/* ─── MUI THEME BUILDER ───────────────────────────────────────────────────────────── */
export const buildTheme = (tMode: 'light' | 'dark', C: ReturnType<typeof getColors>) => createTheme({
  palette: {
    mode: tMode,
    primary: { main: C.primary },
    secondary: { main: C.accent },
    error: { main: C.red },
    warning: { main: C.amber },
    info: { main: C.primary },
    success: { main: C.green },
    background: { default: C.bg, paper: "transparent" },
    text: { primary: C.text, secondary: C.text2 },
  },
  typography: {
    fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
    h1: { fontWeight: 800, letterSpacing: "-0.04em" },
    h2: { fontWeight: 700, letterSpacing: "-0.02em" },
    h3: { fontWeight: 600, letterSpacing: "-0.01em" },
    button: { fontWeight: 500, textTransform: "none", letterSpacing: 0.3 },
  },
  shape: { borderRadius: 10 },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 8,
          padding: "10px 20px",
          boxShadow: "none",
          backdropFilter: "blur(8px)",
          "&:hover": { boxShadow: "none" }
        }
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundImage: "none",
          border: `1px solid ${C.border}`,
          background: C.card,
          backdropFilter: "blur(24px)",
          WebkitBackdropFilter: "blur(24px)",
          boxShadow: "0 8px 32px rgba(0,0,0,0.4)",
        },
      },
    },
    MuiTextField: {
      defaultProps: { variant: "outlined", size: "small" },
      styleOverrides: {
        root: {
          "& .MuiOutlinedInput-root": {
            fontFamily: "'JetBrains Mono', monospace", fontSize: 13,
            backgroundColor: "rgba(255,255,255,0.02)", borderRadius: 8,
            transition: "all 0.2s ease",
            "& fieldset": { borderColor: C.border },
            "&:hover fieldset": { borderColor: C.border2, backgroundColor: "rgba(255,255,255,0.04)" },
            "&.Mui-focused fieldset": { borderColor: C.primary, borderWidth: "1px", boxShadow: `0 0 0 2px rgba(59, 130, 246, 0.15)` },
          },
          "& .MuiInputLabel-root": { fontSize: 13, color: C.text2 },
          "& .MuiInputLabel-root.Mui-focused": { color: C.text },
        },
      },
    },
    MuiSelect: {
      styleOverrides: {
        root: { fontFamily: "'JetBrains Mono', monospace", fontSize: 13, backgroundColor: "rgba(255,255,255,0.02)", borderRadius: 8 },
      },
    },
    MuiToggleButton: {
      styleOverrides: {
        root: {
          fontFamily: "'Inter', sans-serif", fontSize: 13, fontWeight: 500,
          textTransform: "none",
          color: C.text2, borderColor: C.border, borderRadius: "8px !important", padding: "8px 18px",
          transition: "all 0.2s",
          "&.Mui-selected": { color: tMode === 'dark' ? "#fff" : "#000", backgroundColor: tMode === 'dark' ? "rgba(255,255,255,0.1)" : "rgba(0,0,0,0.05)", borderColor: C.border2, "&:hover": { backgroundColor: tMode === 'dark' ? "rgba(255,255,255,0.15)" : "rgba(0,0,0,0.1)" } },
          "&:hover": { backgroundColor: "rgba(255,255,255,0.05)", borderColor: C.border2 },
        },
      },
    },
    MuiChip: { styleOverrides: { root: { fontFamily: "'JetBrains Mono', monospace", fontWeight: 500 } } },
    MuiDivider: { styleOverrides: { root: { borderColor: C.border } } },
    MuiMenuItem: { styleOverrides: { root: { fontFamily: "'Inter', sans-serif", fontSize: 14 } } },
    MuiLinearProgress: {
      styleOverrides: {
        root: { borderRadius: 4, height: 4, backgroundColor: "rgba(255,255,255,0.05)" },
        bar: { borderRadius: 4, background: `linear-gradient(90deg, ${C.primary}, ${C.accent})` },
      },
    },
  },
});

/* ─── PIPELINE STEPS ─────────────────────────────────────────────────────── */
const STEP_DEFS = [
  { id: "fetching", label: "Fetch Repository", icon: "01" },
  { id: "parsing", label: "Parse & Rank Files", icon: "02" },
  { id: "caching", label: "Extract Metadata", icon: "03" },
  { id: "generating", label: "Generate via AI", icon: "04" },
  { id: "pushing", label: "Push to GitHub", icon: "05" },
];
const makeSteps = () => STEP_DEFS.map(s => ({ ...s, status: "waiting", message: "Waiting to start" }));

const stepBorderColor = (s: string, C: any) => s === "running" ? C.primary : s === "done" ? C.green : s === "error" ? C.red : "transparent";
const stepBg = (s: string, C: any) => s === "running" ? "rgba(59,130,246,0.1)" : s === "done" ? "rgba(16, 185, 129, 0.1)" : s === "error" ? "rgba(239,68,68,0.1)" : "transparent";
const stepLabelColor = (s: string, C: any) => s === "running" ? C.primary : s === "done" ? C.green : s === "error" ? C.red : C.text3;

/* ─── THEME CONTEXT ───────────────────────────────────────────────────────── */
export const ThemeColorsContext = createContext<ReturnType<typeof getColors> | null>(null);
export const useThemeColors = () => {
  const ctx = useContext(ThemeColorsContext);
  if (!ctx) throw new Error("useThemeColors must be used inside Provider");
  return ctx;
};

/* ─── CONFETTI ────────────────────────────────────────────────────────────── */
function Confetti({ active }: { active: boolean }) {
  const C = useThemeColors();
  const canvasRef = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    if (!active) return;
    const canvas = canvasRef.current; if (!canvas) return;
    canvas.width = window.innerWidth; canvas.height = window.innerHeight;
    const ctx = canvas.getContext("2d"); if (!ctx) return;
    const pieces = Array.from({ length: 150 }, () => ({
      x: Math.random() * canvas.width, y: Math.random() * -canvas.height,
      w: 6 + Math.random() * 6, h: 6 + Math.random() * 6,
      color: [C.primary, C.accent, C.text, C.text2][Math.floor(Math.random() * 4)],
      rot: Math.random() * 360, vx: (Math.random() - .5) * 2,
      vy: 1.5 + Math.random() * 3, vr: (Math.random() - .5) * 5, alpha: 1,
    }));
    let raf: number;
    const draw = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      let alive = false;
      pieces.forEach(p => {
        p.x += p.vx; p.y += p.vy; p.rot += p.vr;
        if (p.y < canvas.height + 20) alive = true; else p.alpha -= 0.02;
        ctx.save(); ctx.globalAlpha = Math.max(0, p.alpha);
        ctx.translate(p.x, p.y); ctx.rotate((p.rot * Math.PI) / 180);
        ctx.fillStyle = p.color;
        ctx.beginPath(); ctx.roundRect(-p.w / 2, -p.h / 2, p.w, p.h, 2); ctx.fill();
        ctx.restore();
      });
      if (alive) raf = requestAnimationFrame(draw);
    };
    raf = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(raf);
  }, [active]);
  if (!active) return null;
  return <canvas ref={canvasRef} style={{ position: "fixed", inset: 0, zIndex: 99999, pointerEvents: "none" }} />;
}

/* ─── CARD SHELL ─────────────────────────────────────────────────────────── */
function Card({ children, sx = {}, ...props }: any) {
  const C = useThemeColors();
  return (
    <Paper elevation={0} sx={{
      borderRadius: "14px", overflow: "hidden", position: "relative",
      ...sx,
    }} {...props}>
      {/* Subtle inner highlight to make it pop from background */}
      <Box sx={{ position: "absolute", inset: 0, borderRadius: "14px", border: `1px solid ${C.border}`, pointerEvents: "none", zIndex: 10 }} />
      {children}
    </Paper>
  );
}

/* ─── WINDOW CHROME ──────────────────────────────────────────────────────── */
function Chrome({ title, right }: { title: string; right?: React.ReactNode }) {
  const C = useThemeColors();
  return (
    <Box sx={{ display: "flex", alignItems: "center", gap: 1.5, px: 2, py: 1.5, borderBottom: `1px solid ${C.border}`, background: C.border }}>
      <Stack direction="row" spacing={0.75}>
        {["#4b4b4b", "#4b4b4b", "#4b4b4b"].map((c, i) => (
          <Box key={i} sx={{ width: 10, height: 10, borderRadius: "50%", background: c, transition: "background 0.2s", "&:hover": { background: i === 0 ? "#ff5f57" : i === 1 ? "#febc2e" : "#28c840" } }} />
        ))}
      </Stack>
      <Box sx={{ display: "flex", alignItems: "center", gap: 0.75, flex: 1, justifyContent: "center" }}>
        <Typography sx={{ fontSize: 12, color: C.text3, fontWeight: 500, fontFamily: "'Inter', sans-serif" }}>
          {title}
        </Typography>
      </Box>
      <Box sx={{ minWidth: 40, display: "flex", justifyContent: "flex-end" }}>
        {right}
      </Box>
    </Box>
  );
}

/* ─── SECTION LABEL ──────────────────────────────────────────────────────── */
function SectionLabel({ children }: { children: React.ReactNode }) {
  const C = useThemeColors();
  return (
    <Box sx={{ mb: 2 }}>
      <Typography sx={{ fontSize: 13, color: C.text, fontWeight: 600 }}>{children}</Typography>
    </Box>
  );
}

/* ─── MAIN COMPONENT ─────────────────────────────────────────────────────── */
export default function DocuGenius() {
  const [themeMode, setThemeMode] = useState<'light' | 'dark'>('dark');
  const C = useMemo(() => getColors(themeMode), [themeMode]);
  const theme = useMemo(() => buildTheme(themeMode, C), [themeMode, C]);

  useEffect(() => {
    const saved = localStorage.getItem('themeMode');
    if (saved === 'light' || saved === 'dark') setThemeMode(saved);
  }, []);

  const toggleTheme = () => {
    setThemeMode((prev) => {
      const next = prev === 'dark' ? 'light' : 'dark';
      localStorage.setItem('themeMode', next);
      return next;
    });
  };

  const [repo, setRepo] = useState("");
  const [token, setToken] = useState("");
  const [mode, setMode] = useState("github");
  const [localPath, setLocalPath] = useState("");
  const [targetAudience, setTargetAudience] = useState("Mixed");
  const [customInstructions, setCustomInstructions] = useState("");
  const [autoGenerate, setAutoGenerate] = useState(true);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState("");
  const [readmeUrl, setReadmeUrl] = useState("");
  const [generatedMarkdown, setGeneratedMarkdown] = useState("");
  const [refineText, setRefineText] = useState("");
  const [steps, setSteps] = useState(makeSteps());
  const [showRight, setShowRight] = useState(false);
  const [confettiActive, setConfettiActive] = useState(false);
  const [commitReady, setCommitReady] = useState(false);
  const [committing, setCommitting] = useState(false);
  const [snackOpen, setSnackOpen] = useState(false);
  const [appTab, setAppTab] = useState("readme");

  // -- Code Chat Tab State (Legacy 1st Agent) --
  const [chatMessages, setChatMessages] = useState<{ role: string; text: string; contextFiles?: string[] }[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const [chatOnboardingStep, setChatOnboardingStep] = useState<"none" | "repo" | "token" | "localPath">("none");
  const [chatPendingTask, setChatPendingTask] = useState("");

  // -- Agent Operations Tab State (New Multiagentic System) --
  const [opsMessages, setOpsMessages] = useState<{ role: string; text: string; }[]>([]);
  const [opsInput, setOpsInput] = useState("");
  const [opsLoading, setOpsLoading] = useState(false);
  const [opsWorkflowId, setOpsWorkflowId] = useState<string | null>(null);
  const [opsSelectedAgent, setOpsSelectedAgent] = useState("reviewer");
  const [opsAvailableAgents, setOpsAvailableAgents] = useState<{ id: string, name: string }[]>([]);
  const [lastOpsPollResponse, setLastOpsPollResponse] = useState("");
  const [opsOnboardingStep, setOpsOnboardingStep] = useState<"none" | "repo" | "token" | "localPath">("none");
  const [opsPendingTask, setOpsPendingTask] = useState("");

  const chatEndRef = useRef<HTMLDivElement>(null);
  const opsEndRef = useRef<HTMLDivElement>(null);
  const previewRef = useRef<HTMLDivElement>(null);

  useEffect(() => { if (previewRef.current) previewRef.current.scrollTop = previewRef.current.scrollHeight; }, [generatedMarkdown]);
  useEffect(() => { if (chatEndRef.current) chatEndRef.current.scrollIntoView({ behavior: "smooth" }); }, [chatMessages]);
  useEffect(() => { if (opsEndRef.current) opsEndRef.current.scrollIntoView({ behavior: "smooth" }); }, [opsMessages]);

  useEffect(() => {
    fetch(`${SIMPLE_API_BASE}/api/agents`)
      .then(r => r.json())
      .then(data => {
        if (data && data.agents) {
          setOpsAvailableAgents(data.agents);
        }
      })
      .catch(err => console.error("Failed to load agents", err));
  }, []);

  const updateStep = (id: string, patch: any) => setSteps(prev => prev.map(s => s.id === id ? { ...s, ...patch } : s));

  /* ── Chat ── */
  const handleChatSubmit = async (e: any) => {
    e.preventDefault();
    if (!chatInput.trim() || chatLoading) return;

    const isValidRepo = (value: string) => /^[^\s/]+\/[^\s/]+$/.test(value.trim());
    let effectiveRepo = repo;
    let effectiveToken = token;
    let effectiveLocalPath = localPath;

    let messageToProcess = chatInput.trim();
    setChatInput("");
    setChatMessages(prev => [...prev, { role: "user", text: messageToProcess }]);
    setChatLoading(true);

    if (mode === "github") {
      if (chatOnboardingStep === "repo") {
        if (!isValidRepo(messageToProcess)) {
          setChatMessages(prev => [...prev, { role: "ai", text: "Please give repo in this format: owner/repo" }]);
          setChatLoading(false);
          return;
        }
        effectiveRepo = messageToProcess;
        setRepo(messageToProcess);
        setChatOnboardingStep("token");
        setChatMessages(prev => [...prev, { role: "ai", text: "Great. Now please give me your GitHub access token." }]);
        setChatLoading(false);
        return;
      }

      if (chatOnboardingStep === "token") {
        effectiveToken = messageToProcess;
        setToken(messageToProcess);
        const pending = chatPendingTask;
        setChatPendingTask("");
        setChatOnboardingStep("none");
        if (pending) {
          setChatMessages(prev => [...prev, { role: "ai", text: "Thanks! Starting your request now..." }]);
          messageToProcess = pending;
        } else {
          setChatMessages(prev => [...prev, { role: "ai", text: "Thanks! Now tell me what you want me to do with this repo." }]);
          setChatLoading(false);
          return;
        }
      }

      if (!effectiveRepo || !effectiveToken) {
        setChatPendingTask(messageToProcess);
        if (!effectiveRepo) {
          setChatOnboardingStep("repo");
          setChatMessages(prev => [...prev, { role: "ai", text: "Please give me your GitHub repo first (owner/repo)." }]);
        } else {
          setChatOnboardingStep("token");
          setChatMessages(prev => [...prev, { role: "ai", text: "Please give me your GitHub access token so I can continue." }]);
        }
        setChatLoading(false);
        return;
      }
    }

    if (mode === "local") {
      if (chatOnboardingStep === "localPath") {
        effectiveLocalPath = messageToProcess;
        setLocalPath(messageToProcess);
        const pending = chatPendingTask;
        setChatPendingTask("");
        setChatOnboardingStep("none");
        if (pending) {
          setChatMessages(prev => [...prev, { role: "ai", text: "Thanks! Starting your request now..." }]);
          messageToProcess = pending;
        } else {
          setChatMessages(prev => [...prev, { role: "ai", text: "Thanks! Now tell me what you want me to do with this local repo." }]);
          setChatLoading(false);
          return;
        }
      }

      if (!effectiveLocalPath) {
        setChatPendingTask(messageToProcess);
        setChatOnboardingStep("localPath");
        setChatMessages(prev => [...prev, { role: "ai", text: "Please give me your local repository path first." }]);
        setChatLoading(false);
        return;
      }
    }

    try {
      const payload = mode === "github"
        ? { repo: effectiveRepo, access_token: effectiveToken, message: messageToProcess }
        : { local_path: effectiveLocalPath, repo: "", access_token: "", message: messageToProcess };
      const res = await fetch(`${DOC_API_BASE}/chat`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setChatMessages(prev => [...prev, { role: "ai", text: data.answer, contextFiles: data.context_files }]);
    } catch (_err: any) {
      setChatMessages(prev => [...prev, { role: "ai", text: "Sorry, some issue happened while processing your request. Please try again." }]);
    } finally { setChatLoading(false); }
  };

  /* ── Agent Operations ── */
  const handleOpsSubmit = async (e: any) => {
    e.preventDefault();
    if (!opsInput.trim() || opsLoading) return;

    const isValidRepo = (value: string) => /^[^\s/]+\/[^\s/]+$/.test(value.trim());
    let effectiveRepo = repo;
    let effectiveToken = token;
    let effectiveLocalPath = localPath;

    let message = opsInput.trim();
    setOpsInput("");
    setOpsMessages(prev => [...prev, { role: "user", text: message }]);
    setOpsLoading(true);

    if (mode === "github") {
      if (opsOnboardingStep === "repo") {
        if (!isValidRepo(message)) {
          setOpsMessages(prev => [...prev, { role: "ai", text: "Please give repo in this format: owner/repo" }]);
          setOpsLoading(false);
          return;
        }
        effectiveRepo = message;
        setRepo(message);
        setOpsOnboardingStep("token");
        setOpsMessages(prev => [...prev, { role: "ai", text: "Great. Now please give me your GitHub access token." }]);
        setOpsLoading(false);
        return;
      }

      if (opsOnboardingStep === "token") {
        effectiveToken = message;
        setToken(message);
        const pending = opsPendingTask;
        setOpsPendingTask("");
        setOpsOnboardingStep("none");
        if (pending) {
          setOpsMessages(prev => [...prev, { role: "ai", text: "Thanks! Starting your task now..." }]);
          message = pending;
        } else {
          setOpsMessages(prev => [...prev, { role: "ai", text: "Thanks! Now tell me what task you want me to run." }]);
          setOpsLoading(false);
          return;
        }
      }

      if (!effectiveRepo || !effectiveToken) {
        setOpsPendingTask(message);
        if (!effectiveRepo) {
          setOpsOnboardingStep("repo");
          setOpsMessages(prev => [...prev, { role: "ai", text: "Please give me your GitHub repo first (owner/repo)." }]);
        } else {
          setOpsOnboardingStep("token");
          setOpsMessages(prev => [...prev, { role: "ai", text: "Please give me your GitHub access token so I can continue." }]);
        }
        setOpsLoading(false);
        return;
      }
    }

    if (mode === "local") {
      if (opsOnboardingStep === "localPath") {
        effectiveLocalPath = message;
        setLocalPath(message);
        const pending = opsPendingTask;
        setOpsPendingTask("");
        setOpsOnboardingStep("none");
        if (pending) {
          setOpsMessages(prev => [...prev, { role: "ai", text: "Thanks! Starting your task now..." }]);
          message = pending;
        } else {
          setOpsMessages(prev => [...prev, { role: "ai", text: "Thanks! Now tell me what task you want me to run." }]);
          setOpsLoading(false);
          return;
        }
      }

      if (!effectiveLocalPath) {
        setOpsPendingTask(message);
        setOpsOnboardingStep("localPath");
        setOpsMessages(prev => [...prev, { role: "ai", text: "Please give me your local repository path first." }]);
        setOpsLoading(false);
        return;
      }
    }

    let currentWorkflowId = opsWorkflowId;
    const outboundMessage = mode === "github"
      ? [
          `GitHub repo context: ${effectiveRepo}`,
          effectiveToken ? `GitHub access token: ${effectiveToken}` : "",
          "When reading/summarizing/updating files from this repo, use github_inline_comment with source='github'.",
          `User request: ${message}`,
        ].filter(Boolean).join("\n")
      : message;

    try {
      if (!currentWorkflowId) {
        const workspacePath = mode === "local" ? effectiveLocalPath : ".";
        const res = await fetch(`${SIMPLE_API_BASE}/api/workflows`, {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ agent_id: opsSelectedAgent, workspace_path: workspacePath })
        });
        if (!res.ok) throw new Error("Failed to start workflow");
        const data = await res.json();
        currentWorkflowId = data.workflow_id;
        setOpsWorkflowId(currentWorkflowId);
      }

      // 1. Get current message count before sending
      const preStatusRes = await fetch(`${SIMPLE_API_BASE}/api/workflows/${currentWorkflowId}/status`);
      const preStatusData = await preStatusRes.json();
      const initialCount = preStatusData.status?.message_count || 0;

      // 2. Send the message
      const resMsg = await fetch(`${SIMPLE_API_BASE}/api/workflows/${currentWorkflowId}/messages`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: outboundMessage })
      });
      if (!resMsg.ok) throw new Error("Failed to send message");

      // 3. Poll until message_count increases (X + 2: one for user, one for AI)
      const poll = setInterval(async () => {
        try {
          const statusRes = await fetch(`${SIMPLE_API_BASE}/api/workflows/${currentWorkflowId}/status`);
          const statusData = await statusRes.json();
          const currentCount = statusData.status?.message_count || 0;

          // Wait for at least 2 new messages (User + AI)
          if (currentCount >= initialCount + 2 && statusData.status.last_response) {
            const newResponse = statusData.status.last_response;
            setOpsMessages(m => {
              const withoutTyping = m.filter(msg => !(msg.role === "ai" && msg.text === "working..."));
              // Check if already contains this exact response to be 100% sure
              if (withoutTyping.some(msg => msg.role === "ai" && msg.text === newResponse)) return withoutTyping;
              return [...withoutTyping, { role: "ai", text: newResponse }];
            });
            setOpsLoading(false);
            clearInterval(poll);
          }
        } catch (e) { console.error("Polling error", e); }
      }, 1500);

      setOpsMessages(prev => [...prev, { role: "ai", text: "working..." }]);

    } catch (_err: any) {
      setOpsMessages(prev => [...prev, { role: "ai", text: "Sorry, some issue happened while processing your request. Please try again." }]);
      setOpsLoading(false);
    }
  };

  const terminateOpsWorkflow = async () => {
    if (!opsWorkflowId) return;
    try {
      await fetch(`${SIMPLE_API_BASE}/api/workflows/${opsWorkflowId}`, { method: "DELETE" });
      setOpsWorkflowId(null);
      setOpsMessages([]);
      setLastOpsPollResponse("");
    } catch (err) { console.error(err); }
  };

  /* ── Generate ── */
  const handleSubmit = async (e: any, overrideInstructions: string | null = null) => {
    e?.preventDefault();
    if (mode === "github" && (!repo || !token)) { setError("Please provide both repository and access token"); return; }
    if (mode === "local" && !localPath) { setError("Please provide an absolute path"); return; }
    setLoading(true); setError(""); setSuccess(false); setCommitReady(false);
    setReadmeUrl(""); setGeneratedMarkdown(""); setSteps(makeSteps()); setShowRight(true);
    const finalInstructions = overrideInstructions !== null ? overrideInstructions : customInstructions;
    try {
      const payload = mode === "github"
        ? { repo, access_token: token, branch: "main", commit_message: "Update README", custom_instructions: finalInstructions, sections: [], target_audience: targetAudience, auto_commit: autoGenerate }
        : { local_path: localPath, repo: "", access_token: "", branch: "main", custom_instructions: finalInstructions, sections: [], target_audience: targetAudience, auto_commit: autoGenerate };
      const res = await fetch(`${DOC_API_BASE}/stream-readme`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
      if (!res.ok) { let d; try { d = await res.json(); } catch (_) { } throw new Error(d?.detail || res.statusText); }
      if (!res.body) throw new Error("No response body");
      const reader = res.body.getReader(); const decoder = new TextDecoder(); let buffer = "";
      while (true) {
        const { value, done } = await reader.read(); if (done) break;
        buffer += decoder.decode(value, { stream: true }); const parts = buffer.split("\n\n"); buffer = parts.pop() || "";
        for (const part of parts) {
          if (!part.startsWith("data: ")) continue;
          try {
            const data = JSON.parse(part.slice(6));
            if (data.step === "error") { setError(data.message); setSteps(prev => prev.map(s => s.status === "running" ? { ...s, status: "error", message: data.message } : s)); break; }
            if (data.step && data.step !== "done") updateStep(data.step, { status: data.status, message: data.message });
            if (data.step === "generating" && data.chunk) setGeneratedMarkdown(prev => prev + data.chunk);
            if (data.step === "done") {
              if (data.file_url) { setSuccess(true); setReadmeUrl(data.file_url); setConfettiActive(true); setTimeout(() => setConfettiActive(false), 5000); }
              else setCommitReady(true);
            }
          } catch (_) { }
        }
      }
    } catch (err: any) { setError(err.message || "An error occurred"); } finally { setLoading(false); }
  };

  /* ── Refine & Commit ── */
  const handleRefine = (e: any) => {
    e.preventDefault(); if (!refineText.trim()) return;
    const newInstr = customInstructions ? `${customInstructions}\n\nRefinement: ${refineText}` : `Refinement: ${refineText}`;
    setCustomInstructions(newInstr); setRefineText(""); handleSubmit(null, newInstr);
  };

  const handleCommit = async () => {
    setCommitting(true); setError("");
    try {
      const payload = { repo: mode === "github" ? repo : "", access_token: token, local_path: mode === "local" ? localPath : "", markdown_content: generatedMarkdown };
      const res = await fetch(`${DOC_API_BASE}/commit-readme`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
      if (!res.ok) { let d; try { d = await res.json(); } catch (_) { } throw new Error(d?.detail || res.statusText); }
      setCommitReady(false); setSuccess(true);
      if (mode === "github") { const [owner, rName] = repo.split("/"); setReadmeUrl(`https://github.com/${owner}/${rName}/blob/main/README.md`); }
      else setReadmeUrl(`file://${localPath}/README.md`);
      setConfettiActive(true); setTimeout(() => setConfettiActive(false), 5000);
    } catch (err: any) { setError(err.message || "Failed to commit README"); } finally { setCommitting(false); }
  };

  const copyToClipboard = () => { navigator.clipboard.writeText(generatedMarkdown); setSnackOpen(true); };
  const downloadFile = () => {
    const blob = new Blob([generatedMarkdown], { type: "text/markdown" }); const url = URL.createObjectURL(blob);
    const a = document.createElement("a"); a.href = url; a.download = "README.md";
    document.body.appendChild(a); a.click(); document.body.removeChild(a); URL.revokeObjectURL(url);
  };

  const canSubmit = !loading && (mode === "github" ? (repo && token) : localPath);

  /* ══════════════════════════════════════════════════════════════════════════
     RENDER
  ══════════════════════════════════════════════════════════════════════════ */
  return (
    <ThemeColorsContext.Provider value={C}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <style>{`
        body { background: ${C.bg}; overflow-x: hidden; }
        ::selection { background: rgba(59, 130, 246, 0.3); color: #fff; }
        ::-webkit-scrollbar { width: 6px; height: 6px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: ${themeMode === 'dark' ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)'}; border-radius: 6px; }
        ::-webkit-scrollbar-thumb:hover { background: ${themeMode === 'dark' ? 'rgba(255,255,255,0.2)' : 'rgba(0,0,0,0.2)'}; }
        
        /* Animated Mesh Gradient Keyframes */
        @keyframes blob1 {
          0% { transform: translate(0px, 0px) scale(1); }
          33% { transform: translate(150px, -100px) scale(1.2); }
          66% { transform: translate(-100px, 100px) scale(0.8); }
          100% { transform: translate(0px, 0px) scale(1); }
        }
        @keyframes blob2 {
          0% { transform: translate(0px, 0px) scale(1); }
          33% { transform: translate(-150px, 150px) scale(1.1); }
          66% { transform: translate(100px, -100px) scale(0.9); }
          100% { transform: translate(0px, 0px) scale(1); }
        }
      `}</style>

        <Confetti active={confettiActive} />

        {/* ── Animated Mesh Gradient Background ── */}
        <Box sx={{ position: "fixed", inset: 0, zIndex: 0, pointerEvents: "none" }}>
          {/* Subtle grid texture overlay */}
          <Box sx={{ position: "absolute", inset: 3, zIndex: 6, backgroundImage: `linear-gradient(${themeMode === 'dark' ? 'rgba(255, 255, 255, 0.08)' : 'rgba(0, 0, 0, 0.04)'} 2px, transparent 2px), linear-gradient(90deg, ${themeMode === 'dark' ? 'rgba(255, 255, 255, 0.08)' : 'rgba(0, 0, 0, 0.04)'} 2px, transparent 2px)`, backgroundSize: "40px 40px", maskImage: "radial-gradient(ellipse at center, black 40%, transparent 80%)" }} />

          {/* Blurred gradient blobs */}
          <Box sx={{ position: "absolute", inset: 0, zIndex: 6, filter: "blur(120px)", opacity: 0.6 }}>
            <Box sx={{ position: "absolute", top: "10%", left: "20%", width: "40vw", height: "40vw", borderRadius: "50%", background: "radial-gradient(circle, rgba(59,130,246,0.3) 0%, transparent 70%)", animation: "blob1 20s infinite ease-in-out" }} />
            <Box sx={{ position: "absolute", top: "30%", right: "10%", width: "35vw", height: "35vw", borderRadius: "50%", background: "radial-gradient(circle, rgba(139,92,246,0.2) 0%, transparent 70%)", animation: "blob2 25s infinite ease-in-out animation-delay-2s" }} />
            <Box sx={{ position: "absolute", bottom: "10%", left: "40%", width: "45vw", height: "45vw", borderRadius: "50%", background: "radial-gradient(circle, rgba(20,184,166,0.15) 0%, transparent 70%)", animation: "blob1 30s infinite ease-in-out animation-delay-4s" }} />
          </Box>
        </Box>

        {/* ── Page wrapper ── */}
        <Box sx={{ position: "relative", zIndex: 10, maxWidth: 1200, mx: "auto", px: { xs: 2, md: 4 }, pb: 14 }}>

          {/* ── Nav ── */}
          <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", py: 4 }}>
            <Stack direction="row" alignItems="center" spacing={1.5}>
              <Box sx={{
                width: 36, height: 36, borderRadius: "10px",
                background: themeMode === 'dark' ? "rgba(255,255,255,0.03)" : "rgba(0,0,0,0.03)",
                border: `1px solid ${C.border}`,
                display: "flex", alignItems: "center", justifyContent: "center",
                backdropFilter: "blur(10px)",
                boxShadow: "0 4px 12px rgba(0,0,0,0.2)"
              }}>
                <TerminalIcon sx={{ color: C.text, fontSize: 18 }} />
              </Box>
              <Typography sx={{ fontFamily: "'Inter', sans-serif", fontWeight: 700, fontSize: 18, color: C.text, letterSpacing: "-0.02em" }}>
                Documentation drafter
              </Typography>
            </Stack>

            <Stack direction="row" spacing={2} alignItems="center">
              <IconButton onClick={toggleTheme} sx={{ color: C.text2, border: `1px solid ${C.border}`, borderRadius: "12px", width: 36, height: 36, background: themeMode === 'dark' ? "rgba(255,255,255,0.03)" : "rgba(0,0,0,0.02)", backdropFilter: "blur(10px)", boxShadow: "0 4px 12px rgba(0,0,0,0.1)" }}>
                {themeMode === 'dark' ? <LightModeIcon fontSize="small" /> : <DarkModeIcon fontSize="small" />}
              </IconButton>
              <Box sx={{ display: "flex", alignItems: "center", gap: 1, px: 2, py: 0.75, border: `1px solid ${C.border}`, borderRadius: "99px", background: themeMode === 'dark' ? "rgba(255,255,255,0.02)" : "rgba(0,0,0,0.02)", backdropFilter: "blur(10px)", boxShadow: "0 4px 12px rgba(0,0,0,0.1)" }}>
                <Box sx={{ width: 8, height: 8, borderRadius: "50%", background: C.green, boxShadow: `0 0 10px ${C.green}` }} />
                <Typography sx={{ fontSize: 12, color: C.text2, fontWeight: 500 }}>System Online</Typography>
              </Box>
            </Stack>
          </Box>

          {/* ── Hero ── */}
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6, ease: "easeOut" }}>
            {/* <Box sx={{ textAlign: "center", pt: 6, pb: 10 }}> */}
            {/* Headline */}
            {/* <Typography variant="h1" sx={{ fontSize: "clamp(36px, 6vw, 56px)", lineHeight: 1.1, mb: 3 }}> */}
            {/* <Box component="span" sx={{ display: "block", color: C.text }}>Understand any codebase.</Box> */}
            {/* <Box component="span" sx={{
                display: "block", WebkitTextFillColor: "transparent",
                WebkitBackgroundClip: "text", backgroundClip: "text",
                background: `linear-gradient(to right, ${C.primary}, #60a5fa, ${C.accent})`,
              }}>Generate flawless docs.</Box> */}
            {/* </Typography> */}

            {/* <Typography sx={{ fontSize: 16, color: C.text2, maxWidth: 500, mx: "auto", lineHeight: 1.6 }}>
              Connect a repository and let AI analyze your code structure, generate a beautiful README, or answer questions instantly.
            </Typography> */}
            {/* </Box> */}
          </motion.div>

          {/* ── Mode tab switcher ── */}
          <Box sx={{ display: "flex", justifyContent: "center", mb: 4 }}>
            <Box sx={{ display: "inline-flex", p: "4px", background: themeMode === 'dark' ? "rgba(0,0,0,0.3)" : "rgba(0,0,0,0.05)", backdropFilter: "blur(12px)", border: `1px solid ${C.border}`, borderRadius: "12px" }}>
              {[
                { id: "readme", Icon: DocumentIcon, label: "Generator" },
                { id: "chat", Icon: ChatIcon, label: "Code Chat" },
                { id: "operations", Icon: TerminalIcon, label: "Agent Operations" },
              ].map(tab => (
                <Button key={tab.id} onClick={() => setAppTab(tab.id)} sx={{
                  color: appTab === tab.id ? C.text : C.text2,
                  background: appTab === tab.id ? (themeMode === 'dark' ? "rgba(255,255,255,0.1)" : "rgba(0,0,0,0.1)") : "transparent",
                  py: 1, px: 3, borderRadius: "8px",
                  fontWeight: 500, fontSize: 14, gap: 1,
                  "&:hover": { background: appTab === tab.id ? (themeMode === 'dark' ? "rgba(255,255,255,0.12)" : "rgba(0,0,0,0.12)") : (themeMode === 'dark' ? "rgba(255,255,255,0.04)" : "rgba(0,0,0,0.04)") }, transition: "all 0.2s"
                }}>
                  <tab.Icon sx={{ fontSize: 18 }} />{tab.label}
                </Button>
              ))}
            </Box>
          </Box>

          <AnimatePresence mode="wait">

            {/* ══════════════════════════════════════════
            CHAT MODE
        ══════════════════════════════════════════ */}
            {appTab === "chat" && (
              <motion.div key="chat-layout" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} transition={{ duration: 0.2 }}>
                <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", md: "320px 1fr" }, gap: 3, alignItems: "start" }}>

                  <Card>
                    <Chrome title="Context Setup" />
                    <Box sx={{ p: 3 }}>
                      <SectionLabel>Select Source</SectionLabel>
                      <ToggleButtonGroup value={mode} exclusive onChange={(_, v) => v && setMode(v)} fullWidth
                        sx={{ mb: 3, gap: "8px", "& .MuiToggleButtonGroup-grouped": { border: `1px solid ${C.border} !important` } }}>
                        <ToggleButton value="github" sx={{ flex: 1, gap: 1 }}><GitHubIcon sx={{ fontSize: 16 }} /> GitHub</ToggleButton>
                        <ToggleButton value="local" sx={{ flex: 1, gap: 1 }}><FolderIcon sx={{ fontSize: 16 }} /> Local</ToggleButton>
                      </ToggleButtonGroup>
                      <AnimatePresence mode="wait">
                        {mode === "github" ? (
                          <motion.div key="gh2" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.15 }}>
                            <Stack spacing={2.5}>
                              <TextField label="Repository Path" placeholder="owner/repo" value={repo} onChange={e => setRepo(e.target.value)} fullWidth />
                              <TextField label="Personal Access Token" type="password" placeholder="ghp_..." value={token} onChange={e => setToken(e.target.value)} fullWidth />
                            </Stack>
                          </motion.div>
                        ) : (
                          <motion.div key="local2" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.15 }}>
                            <TextField label="Absolute Path" placeholder="/Users/name/project" value={localPath} onChange={e => setLocalPath(e.target.value)} fullWidth />
                          </motion.div>
                        )}
                      </AnimatePresence>

                      <Divider sx={{ my: 3 }} />

                      <Typography sx={{ fontSize: 12, color: C.text2, fontWeight: 500, mb: 1.5 }}>Suggested Queries</Typography>
                      <Stack spacing={1}>
                        {["Where are the API routes defined?", "Explain the authentication flow", "List all external dependencies"].map((q, i) => (
                          <Box key={i} onClick={() => setChatInput(q)} sx={{
                            px: 1.5, py: 1, borderRadius: "6px", cursor: "pointer",
                            border: `1px solid ${C.border}`, background: "rgba(255,255,255,0.02)",
                            fontSize: 12, color: C.text2, transition: "all 0.15s",
                            "&:hover": { borderColor: C.border2, color: C.text, background: "rgba(255,255,255,0.05)" },
                          }}>
                            {q}
                          </Box>
                        ))}
                      </Stack>

                      {chatMessages.length > 0 && (
                        <Button fullWidth variant="outlined" onClick={() => setChatMessages([])} sx={{ mt: 3, fontSize: 13, borderColor: C.border, color: C.text2, "&:hover": { borderColor: C.text, color: C.text } }}>
                          Clear Conversation
                        </Button>
                      )}
                    </Box>
                  </Card>

                  <Card sx={{ display: "flex", flexDirection: "column", height: "calc(100vh - 250px)", minHeight: 600 }}>
                    <Chrome title="Conversation" />
                    <Box sx={{ flex: 1, overflowY: "auto", p: 4, display: "flex", flexDirection: "column", gap: 3 }}>
                      {chatMessages.length === 0 ? (
                        <Box sx={{ m: "auto", textAlign: "center", maxWidth: 300 }}>
                          <ChatIcon sx={{ fontSize: 48, color: C.border2, mb: 2 }} />
                          <Typography sx={{ fontSize: 18, color: C.text, fontWeight: 600, mb: 1 }}>Start Chatting</Typography>
                          <Typography sx={{ fontSize: 14, color: C.text2, lineHeight: 1.5 }}>Configure your codebase context on the left, then ask any question about the architecture or logic.</Typography>
                        </Box>
                      ) : chatMessages.map((msg, i) => (
                        <Box key={i} sx={{ display: "flex", gap: 2, alignItems: "flex-start", flexDirection: msg.role === "user" ? "row-reverse" : "row" }}>
                          <Box sx={{ width: 36, height: 36, borderRadius: "50%", flexShrink: 0, background: msg.role === "user" ? C.primary : "rgba(255,255,255,0.1)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 13, color: "#fff", fontWeight: 600 }}>
                            {msg.role === "user" ? "U" : "AI"}
                          </Box>
                          <Box sx={{ flex: 1, maxWidth: "85%" }}>
                            <Box sx={{
                              background: msg.role === "user" ? "rgba(59,130,246,0.15)" : "transparent",
                              px: msg.role === "user" ? 2.5 : 0, py: msg.role === "user" ? 1.5 : 0,
                              borderRadius: "12px", border: msg.role === "user" ? `1px solid rgba(59,130,246,0.25)` : "none",
                              fontSize: 14, lineHeight: 1.7, color: C.text,
                            }}>
                              <ReactMarkdown components={{
                                code({ node, inline, className, children, ...props }: any) {
                                  return inline
                                    ? <code style={{ background: "rgba(255,255,255,0.1)", padding: "2px 6px", borderRadius: 4, fontSize: 13, fontFamily: "'JetBrains Mono', monospace" }} {...props}>{children}</code>
                                    : <pre style={{ background: "rgba(0,0,0,0.6)", padding: "16px", borderRadius: 8, overflowX: "auto", marginTop: 12, fontSize: 13, border: `1px solid ${C.border}` }}><code style={{ fontFamily: "'JetBrains Mono', monospace" }} {...props}>{children}</code></pre>
                                }
                              }}>{msg.text}</ReactMarkdown>
                            </Box>
                            {msg.contextFiles && msg.contextFiles.length > 0 && (
                              <Box sx={{ mt: 1, display: "flex", flexWrap: "wrap", gap: 1 }}>
                                <Typography sx={{ fontSize: 11, color: C.text3, alignSelf: "center" }}>Referenced:</Typography>
                                {msg.contextFiles.map((file, idx) => (
                                  <Chip key={idx} label={file.split("/").pop()} size="small" sx={{ height: 20, fontSize: 11, background: "rgba(255,255,255,0.05)", color: C.text2, border: `1px solid ${C.border}` }} />
                                ))}
                              </Box>
                            )}
                          </Box>
                        </Box>
                      ))}
                      {chatLoading && (
                        <Box sx={{ display: "flex", gap: 2, alignItems: "flex-start" }}>
                          <Box sx={{ width: 36, height: 36, borderRadius: "50%", flexShrink: 0, background: "rgba(255,255,255,0.1)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 13, color: "#fff", fontWeight: 600 }}>AI</Box>
                          <Box sx={{ py: 1 }}><CircularProgress size={16} sx={{ color: C.text2 }} /></Box>
                        </Box>
                      )}
                      <div ref={chatEndRef} />
                    </Box>

                    <Box component="form" onSubmit={handleChatSubmit} sx={{ p: 3, borderTop: `1px solid ${C.border}`, background: "rgba(0,0,0,0.3)" }}>
                      <Box sx={{ display: "flex", gap: 2, alignItems: "flex-end" }}>
                        <TextField
                          placeholder="Message DocuGenius..."
                          value={chatInput} onChange={e => setChatInput(e.target.value)}
                          disabled={chatLoading} multiline maxRows={5} fullWidth
                          onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleChatSubmit(e); } }}
                        />
                        <Button type="submit" variant="contained" disabled={chatLoading || !chatInput.trim() || !canSubmit}
                          sx={{ minWidth: 44, width: 44, height: 40, p: 0, background: C.text, color: "#000", "&:hover": { background: "#fff" } }}>
                          <ArrowIcon sx={{ fontSize: 20 }} />
                        </Button>
                      </Box>
                    </Box>
                  </Card>
                </Box>
              </motion.div>
            )}

            {/* ══════════════════════════════════════════
            AGENT OPERATIONS MODE
        ══════════════════════════════════════════ */}
            {appTab === "operations" && (
              <motion.div key="ops-layout" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} transition={{ duration: 0.2 }}>
                <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", md: "320px 1fr" }, gap: 3, alignItems: "start" }}>

                  <Card>
                    <Chrome title="Agent Setup" />
                    <Box sx={{ p: 3 }}>
                      <SectionLabel>Select Source</SectionLabel>
                      <ToggleButtonGroup value={mode} exclusive onChange={(_, v) => v && setMode(v)} fullWidth
                        sx={{ mb: 3, gap: "8px", "& .MuiToggleButtonGroup-grouped": { border: `1px solid ${C.border} !important` } }}>
                        <ToggleButton value="github" sx={{ flex: 1, gap: 1 }}><GitHubIcon sx={{ fontSize: 16 }} /> GitHub</ToggleButton>
                        <ToggleButton value="local" sx={{ flex: 1, gap: 1 }}><FolderIcon sx={{ fontSize: 16 }} /> Local</ToggleButton>
                      </ToggleButtonGroup>

                      <AnimatePresence mode="wait">
                        {mode === "github" ? (
                          <motion.div key="gh-ops" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.15 }}>
                            <Stack spacing={2.5}>
                              <TextField label="Repository Path" placeholder="owner/repo" value={repo} onChange={e => setRepo(e.target.value)} fullWidth />
                              <TextField label="Personal Access Token" type="password" placeholder="ghp_..." value={token} onChange={e => setToken(e.target.value)} fullWidth />
                            </Stack>
                          </motion.div>
                        ) : (
                          <motion.div key="local-ops" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.15 }}>
                            <TextField label="Absolute Path" placeholder="/Users/name/project" value={localPath} onChange={e => setLocalPath(e.target.value)} fullWidth />
                          </motion.div>
                        )}
                      </AnimatePresence>

                      <Divider sx={{ my: 3 }} />

                      <SectionLabel>Active Agent</SectionLabel>
                      <Box sx={{ p: 2, mb: 3, border: `1px solid ${C.border}`, borderRadius: 1.5, bgcolor: C.surface, color: C.text2, fontSize: 13, fontFamily: "var(--font-mono)" }}>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <Box sx={{ width: 8, height: 8, borderRadius: '50%', bgcolor: C.teal }} />
                          <span style={{ color: '#fff' }}>Universal Agent</span>
                        </Box>
                        <Box sx={{ mt: 1, fontSize: 11, opacity: 0.8 }}>
                          Handles code review, documentation, file operations, and general repository tasks.
                        </Box>
                      </Box>

                      {(opsMessages.length > 0 || opsWorkflowId) && (
                        <Button fullWidth variant="outlined" onClick={terminateOpsWorkflow} sx={{ mt: 3, fontSize: 13, borderColor: C.border, color: C.text2, "&:hover": { borderColor: C.text, color: C.text } }}>
                          End Session
                        </Button>
                      )}
                    </Box>
                  </Card>

                  <Card sx={{ display: "flex", flexDirection: "column", height: "calc(100vh - 250px)", minHeight: 600 }}>
                    <Chrome title={`Talking to ${opsSelectedAgent}`} right={opsWorkflowId ? <Chip label="Session Active" size="small" sx={{ height: 20, fontSize: 10, background: "rgba(16, 185, 129, 0.1)", color: C.green }} /> : null} />
                    <Box sx={{ flex: 1, overflowY: "auto", p: 4, display: "flex", flexDirection: "column", gap: 3 }}>
                      {opsMessages.length === 0 ? (
                        <Box sx={{ m: "auto", textAlign: "center", maxWidth: 300 }}>
                          <TerminalIcon sx={{ fontSize: 48, color: C.border2, mb: 2 }} />
                          <Typography sx={{ fontSize: 18, color: C.text, fontWeight: 600, mb: 1 }}>Agent Operations</Typography>
                          <Typography sx={{ fontSize: 14, color: C.text2, lineHeight: 1.5 }}>
                            Chat with specialized agents to review code, apply refactoring, manage files, and execute Temporal workflows securely.
                          </Typography>
                        </Box>
                      ) : opsMessages.map((msg, i) => (
                        <Box key={i} sx={{ display: "flex", gap: 2, alignItems: "flex-start", flexDirection: msg.role === "user" ? "row-reverse" : "row" }}>
                          <Box sx={{ width: 36, height: 36, borderRadius: "50%", flexShrink: 0, background: msg.role === "user" ? C.primary : "rgba(255,255,255,0.1)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 13, color: "#fff", fontWeight: 600 }}>
                            {msg.role === "user" ? "U" : "AI"}
                          </Box>
                          <Box sx={{ flex: 1, maxWidth: "85%" }}>
                            <Box sx={{
                              background: msg.role === "user" ? "rgba(59,130,246,0.15)" : "transparent",
                              px: msg.role === "user" ? 2.5 : 0, py: msg.role === "user" ? 1.5 : 0,
                              borderRadius: "12px", border: msg.role === "user" ? `1px solid rgba(59,130,246,0.25)` : "none",
                              fontSize: 14, lineHeight: 1.7, color: C.text,
                            }}>
                              <ReactMarkdown components={{
                                code({ node, inline, className, children, ...props }: any) {
                                  return inline
                                    ? <code style={{ background: "rgba(255,255,255,0.1)", padding: "2px 6px", borderRadius: 4, fontSize: 13, fontFamily: "'JetBrains Mono', monospace" }} {...props}>{children}</code>
                                    : <pre style={{ background: "rgba(0,0,0,0.6)", padding: "16px", borderRadius: 8, overflowX: "auto", marginTop: 12, fontSize: 13, border: `1px solid ${C.border}` }}><code style={{ fontFamily: "'JetBrains Mono', monospace" }} {...props}>{children}</code></pre>
                                }
                              }}>{msg.text}</ReactMarkdown>
                            </Box>
                          </Box>
                        </Box>
                      ))}
                      <div ref={opsEndRef} />
                    </Box>

                    <Box component="form" onSubmit={handleOpsSubmit} sx={{ p: 3, borderTop: `1px solid ${C.border}`, background: "rgba(0,0,0,0.3)" }}>
                      <Box sx={{ display: "flex", gap: 2, alignItems: "flex-end" }}>
                        <TextField
                          placeholder={`Ask ${opsSelectedAgent} to do a task...`}
                          value={opsInput} onChange={e => setOpsInput(e.target.value)}
                          disabled={opsLoading} multiline maxRows={5} fullWidth
                          onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleOpsSubmit(e); } }}
                        />
                        <Button type="submit" variant="contained" disabled={opsLoading || !opsInput.trim() || !canSubmit}
                          sx={{ minWidth: 44, width: 44, height: 40, p: 0, background: C.text, color: "#000", "&:hover": { background: "#fff" } }}>
                          {opsLoading ? <CircularProgress size={16} sx={{ color: "#000" }} /> : <ArrowIcon sx={{ fontSize: 20 }} />}
                        </Button>
                      </Box>
                    </Box>
                  </Card>
                </Box>
              </motion.div>
            )}

            {/* ══════════════════════════════════════════
            README MODE
        ══════════════════════════════════════════ */}
            {appTab === "readme" && (
              <motion.div key="readme-layout" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} transition={{ duration: 0.2 }}>
                <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", md: "380px 1fr" }, gap: 3, alignItems: "start" }}>

                  <Card>
                    <Chrome title="Configuration" />
                    <Box sx={{ p: 3 }}>

                      <SectionLabel>Repository Source</SectionLabel>
                      <ToggleButtonGroup value={mode} exclusive onChange={(_, v) => v && setMode(v)} fullWidth
                        sx={{ mb: 3, gap: "8px", "& .MuiToggleButtonGroup-grouped": { border: `1px solid ${C.border} !important` } }}>
                        <ToggleButton value="github" sx={{ flex: 1, gap: 1 }}><GitHubIcon sx={{ fontSize: 16 }} /> GitHub</ToggleButton>
                        <ToggleButton value="local" sx={{ flex: 1, gap: 1 }}><FolderIcon sx={{ fontSize: 16 }} /> Local</ToggleButton>
                      </ToggleButtonGroup>

                      <AnimatePresence mode="wait">
                        {mode === "github" ? (
                          <motion.div key="gh" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.15 }}>
                            <Stack spacing={2.5} sx={{ mb: 4 }}>
                              <TextField label="Repository Name" placeholder="user/repo" value={repo} onChange={e => setRepo(e.target.value)} disabled={loading} fullWidth />
                              <TextField label="Access Token" type="password" placeholder="ghp_..." value={token} onChange={e => setToken(e.target.value)} disabled={loading} fullWidth />
                            </Stack>
                          </motion.div>
                        ) : (
                          <motion.div key="local" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.15 }}>
                            <Box sx={{ mb: 4 }}>
                              <TextField label="Directory Path" placeholder="/Users/name/repo" value={localPath} onChange={e => setLocalPath(e.target.value)} disabled={loading} fullWidth />
                            </Box>
                          </motion.div>
                        )}
                      </AnimatePresence>

                      <Divider sx={{ mb: 4 }} />

                      <SectionLabel>Generation Settings</SectionLabel>
                      <FormControl fullWidth size="small" sx={{ mb: 3 }}>
                        <InputLabel sx={{ fontSize: 13, color: C.text2 }}>Target Audience</InputLabel>
                        <Select value={targetAudience} label="Target Audience" onChange={e => setTargetAudience(e.target.value)} disabled={loading}>
                          <MenuItem value="Mixed">General / Mixed</MenuItem>
                          <MenuItem value="Beginner Developers">Beginner Developers</MenuItem>
                          <MenuItem value="Advanced Engineers">Advanced Engineers</MenuItem>
                          <MenuItem value="End Users">End Users</MenuItem>
                        </Select>
                      </FormControl>

                      <TextField label="Custom Instructions (Optional)" placeholder="e.g. Highlight the API architecture..." value={customInstructions} onChange={e => setCustomInstructions(e.target.value)} disabled={loading} multiline minRows={3} fullWidth sx={{ mb: 3 }} />

                      <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", mb: 4 }}>
                        <Box>
                          <Typography sx={{ fontSize: 14, color: C.text, fontWeight: 500 }}>Auto-Sync</Typography>
                          <Typography sx={{ fontSize: 12, color: C.text3 }}>Regenerate on git push</Typography>
                        </Box>
                        <Switch checked={autoGenerate} onChange={e => setAutoGenerate(e.target.checked)} size="small" sx={{ "& .MuiSwitch-switchBase.Mui-checked": { color: themeMode === 'dark' ? "#fff" : C.primary }, "& .MuiSwitch-track": { backgroundColor: themeMode === 'dark' ? "rgba(255,255,255,0.2)" : "rgba(0,0,0,0.2)" } }} />
                      </Box>

                      <Button fullWidth variant="contained" disabled={!canSubmit} onClick={handleSubmit} sx={{
                        background: loading ? (themeMode === 'dark' ? "rgba(255,255,255,0.1)" : "rgba(0,0,0,0.1)") : C.text, color: loading ? C.text2 : C.bg,
                        fontWeight: 600, fontSize: 14, py: 1.5,
                        "&:hover:not(:disabled)": { background: themeMode === 'dark' ? "#fff" : "#000", transform: "translateY(-1px)" },
                        "&:active:not(:disabled)": { transform: "translateY(0)" },
                      }}>
                        {loading ? (
                          <Stack direction="row" spacing={1.5} alignItems="center">
                            <CircularProgress size={16} sx={{ color: C.text }} />
                            <span>Processing Codebase...</span>
                          </Stack>
                        ) : "Generate Documentation"}
                      </Button>
                    </Box>
                  </Card>

                  {/* RIGHT: PIPELINE + PREVIEW */}
                  <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>

                    <AnimatePresence>
                      {showRight && (
                        <motion.div key="pipeline" initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} exit={{ opacity: 0, height: 0 }} style={{ overflow: "hidden" }}>
                          <Card sx={{ p: 2, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                            {steps.map((step, idx) => (
                              <Box key={step.id} sx={{ display: "flex", alignItems: "center", flex: 1 }}>
                                <Box sx={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 1 }}>
                                  <Box sx={{ width: 24, height: 24, borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center", border: `1px solid ${stepBorderColor(step.status, C)}`, background: stepBg(step.status, C), color: stepBorderColor(step.status, C), fontSize: 10, transition: "all 0.3s" }}>
                                    {step.status === "done" ? <CheckCircleIcon sx={{ fontSize: 14 }} /> : step.status === "error" ? "!" : idx + 1}
                                  </Box>
                                  <Typography sx={{ fontSize: 10, color: stepLabelColor(step.status, C), fontWeight: 500, display: { xs: "none", sm: "block" }, transition: "all 0.3s" }}>{step.label}</Typography>
                                </Box>
                                {idx < steps.length - 1 && <Box sx={{ flex: 1, height: "1px", background: step.status === "done" ? "rgba(16, 185, 129, 0.4)" : "rgba(255,255,255,0.1)", mx: 1.5, mt: { xs: 0, sm: "-16px" }, transition: "background 0.3s" }} />}
                              </Box>
                            ))}
                          </Card>
                        </motion.div>
                      )}
                    </AnimatePresence>

                    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.1 }}>
                      <Card>
                        <Chrome title="Preview: README.md" right={
                          success && (
                            <Stack direction="row" spacing={1}>
                              <Button size="small" onClick={copyToClipboard} sx={{ minWidth: 0, p: 0.5, color: C.text2, "&:hover": { color: C.text } }}><CopyIcon sx={{ fontSize: 16 }} /></Button>
                              <Button size="small" onClick={downloadFile} sx={{ minWidth: 0, p: 0.5, color: C.text2, "&:hover": { color: C.text } }}><DownloadIcon sx={{ fontSize: 16 }} /></Button>
                            </Stack>
                          )
                        } />

                        <Box ref={previewRef} sx={{
                          height: 520, overflowY: "auto", p: 4,
                          fontFamily: "'Inter', sans-serif", fontSize: 14, lineHeight: 1.7, color: C.text2,
                          "& h1": { fontWeight: 800, color: C.text, fontSize: "2em", mt: 1, mb: 2 },
                          "& h2": { fontWeight: 700, color: C.text, fontSize: "1.5em", mt: 4, mb: 2, borderBottom: `1px solid ${C.border}`, pb: 1 },
                          "& h3": { fontWeight: 600, color: C.text, fontSize: "1.2em", mt: 3, mb: 1.5 },
                          "& p": { mb: 2 },
                          "& strong": { color: C.text },
                          "& code": { fontFamily: "'JetBrains Mono', monospace", background: "rgba(255,255,255,0.08)", borderRadius: "4px", px: 1, py: 0.5, fontSize: "0.9em", color: C.text },
                          "& pre": { background: "rgba(0,0,0,0.6)", border: `1px solid ${C.border}`, borderRadius: "8px", p: 2, overflowX: "auto", mb: 2 },
                          "& pre code": { background: "none", p: 0, fontSize: "0.85em", color: C.text2 },
                          "& blockquote": { borderLeft: `3px solid ${C.border2}`, pl: 2, color: C.text3, my: 2 },
                          "& a": { color: C.primary, textDecoration: "none", "&:hover": { textDecoration: "underline" } },
                          "& ul, & ol": { pl: 3, mb: 2 },
                          "& li": { mb: 0.5 },
                        }}>
                          {generatedMarkdown ? (
                            <ReactMarkdown remarkPlugins={[remarkGfm]}>{generatedMarkdown}</ReactMarkdown>
                          ) : (
                            <Box sx={{ height: "100%", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", opacity: 0.5 }}>
                              <DocumentIcon sx={{ fontSize: 48, mb: 2 }} />
                              <Typography sx={{ fontSize: 14 }}>Generated output will appear here</Typography>
                            </Box>
                          )}
                        </Box>

                        <AnimatePresence>
                          {success && readmeUrl && (
                            <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} exit={{ opacity: 0, height: 0 }}>
                              <Box sx={{ display: "flex", alignItems: "center", gap: 2, px: 3, py: 2, borderTop: `1px solid ${C.border}`, background: "rgba(16, 185, 129, 0.05)" }}>
                                <CheckCircleIcon sx={{ color: C.green }} />
                                <Box sx={{ flex: 1 }}>
                                  <Typography sx={{ fontSize: 13, fontWeight: 600, color: C.green }}>Successfully Generated</Typography>
                                  <Typography component="a" href={readmeUrl} target="_blank" rel="noopener noreferrer" sx={{ fontSize: 12, color: C.text2, textDecoration: "underline" }}>View Source</Typography>
                                </Box>
                              </Box>
                            </motion.div>
                          )}
                        </AnimatePresence>

                        <AnimatePresence>
                          {(commitReady || success) && (
                            <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} exit={{ opacity: 0, height: 0 }}>
                              <Box sx={{ display: "flex", gap: 2, p: 2, borderTop: `1px solid ${C.border}`, background: "rgba(0,0,0,0.3)" }}>
                                <TextField placeholder="Request adjustments..." value={refineText} onChange={e => setRefineText(e.target.value)} disabled={loading || committing} onKeyDown={e => e.key === "Enter" && handleRefine(e)} size="small" sx={{ flex: 1 }} />
                                <Button variant="outlined" onClick={handleRefine} disabled={loading || committing || !refineText.trim()} sx={{ borderColor: C.border, color: C.text, "&:hover": { background: "rgba(255,255,255,0.05)" } }}>
                                  Refine
                                </Button>
                                {commitReady && (
                                  <Button variant="contained" onClick={handleCommit} disabled={committing} sx={{ background: C.text, color: "#000", "&:hover": { background: "#fff" } }}>
                                    {committing ? <CircularProgress size={16} sx={{ color: "#000" }} /> : mode === "github" ? "Push to Repo" : "Save Locally"}
                                  </Button>
                                )}
                              </Box>
                            </motion.div>
                          )}
                        </AnimatePresence>

                      </Card>
                    </motion.div>
                  </Box>
                </Box>
              </motion.div>
            )}
          </AnimatePresence>

          {/* ── Footer ── */}
          <Box sx={{ textAlign: "center", pt: 8, opacity: 0.5 }}>
            <Typography sx={{ fontSize: 12, color: C.text2 }}>DocuGenius AI</Typography>
          </Box>
        </Box>

        {/* Snackbars */}
        <Snackbar open={!!error} anchorOrigin={{ vertical: "bottom", horizontal: "center" }} onClose={() => setError("")}>
          <Alert severity="error" onClose={() => setError("")} sx={{ background: "#1a0b0b", border: `1px solid ${C.red}`, color: C.text }}>{error}</Alert>
        </Snackbar>
        <Snackbar open={snackOpen} autoHideDuration={2200} onClose={() => setSnackOpen(false)} anchorOrigin={{ vertical: "bottom", horizontal: "center" }}>
          <Alert severity="success" sx={{ background: "#061810", border: `1px solid ${C.green}`, color: C.text }}>Copied to clipboard</Alert>
        </Snackbar>
      </ThemeProvider>
    </ThemeColorsContext.Provider>
  );
}