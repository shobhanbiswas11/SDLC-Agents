import { useState, useRef, useCallback, useEffect } from "react";
import axios from "axios";
import { Message } from "../types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8002";
const POLL_INTERVAL = 3000;

export function useAgentWorkflow() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [workflowId, setWorkflowId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [waitingForUser, setWaitingForUser] = useState(false);
  const [sessionMeta, setSessionMeta] = useState<{ id: string; source: string; workspace: string } | null>(null);

  const pollRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => () => {
    if (pollRef.current) clearTimeout(pollRef.current);
  }, []);

  const startPolling = useCallback((wfId: string) => {
    if (pollRef.current) clearTimeout(pollRef.current);
    let pollCount = 0;
    let currentInterval = POLL_INTERVAL;

    const poll = async () => {
      pollCount++;
      if (pollCount > 60) {
        setIsLoading(false);
        setMessages(prev => [...prev, {
          role: "system",
          content: "Request timed out. Try a smaller file or more specific query.",
          timestamp: new Date(),
        }]);
        return;
      }
      try {
        const res = await axios.get(`${API_BASE}/sessions/${wfId}/status`, { timeout: 10000 });
        const data = res.data;
        currentInterval = POLL_INTERVAL;

        if (data.waiting_for_user) {
          setWaitingForUser(true);
          setIsLoading(false);
          if (data.last_response) {
            setMessages(prev => {
              if (prev[prev.length - 1]?.content === data.last_response) return prev;
              return [...prev, { role: "assistant", content: data.last_response, timestamp: new Date() }];
            });
          }
          return;
        }

        if (data.status === "idle" && data.last_response) {
          setMessages(prev => {
            if (prev[prev.length - 1]?.content === data.last_response) return prev;
            return [...prev, { role: "assistant", content: data.last_response, timestamp: new Date() }];
          });
          setIsLoading(false);
          setWaitingForUser(false);
          return;
        }

        pollRef.current = setTimeout(poll, currentInterval);
      } catch {
        currentInterval = Math.min(currentInterval * 1.5, 8000);
        pollRef.current = setTimeout(poll, currentInterval);
      }
    };
    pollRef.current = setTimeout(poll, currentInterval);
  }, []);

  const startSession = useCallback(async (
    workspacePath: string,
    sourceType: "local" | "github",
    githubUrl: string,
    githubBranch: string
  ) => {
    try {
      const res = await axios.post(`${API_BASE}/sessions`, {
        workspace_path: workspacePath,
        source_type: sourceType,
        github_url: sourceType === "github" ? githubUrl.trim() : null,
        github_branch: sourceType === "github" && githubBranch.trim() ? githubBranch.trim() : "main",
      });
      const wfId = res.data.session_id;
      const resolvedWorkspace = res.data.workspace_path || (sourceType === "github" ? githubUrl : workspacePath);
      const sourceLabel = sourceType === "github" ? "GitHub" : "Local";
      
      setWorkflowId(wfId);
      setIsConnected(true);
      setSessionMeta({ id: wfId, source: sourceLabel, workspace: resolvedWorkspace });
      setMessages([{
        role: "system",
        content: `Session initialized · ${wfId.slice(0, 16)}…\nSource: ${sourceLabel}\nWorkspace: ${resolvedWorkspace}\n\nReady to analyze. Send me a file path and I'll detect code smells, generate diffs, and apply refactors with your approval.`,
        timestamp: new Date(),
      }]);
      return true;
    } catch (err: any) {
      setMessages([{
        role: "system",
        content: `Connection failed: ${err.message}\n\nEnsure the backend API URL is reachable and the LangGraph server is running.`,
        timestamp: new Date(),
      }]);
      return false;
    }
  }, []);

  const sendMessage = useCallback(async (userMsg: string) => {
    if (!workflowId) return;
    setMessages(prev => [...prev, { role: "user", content: userMsg, timestamp: new Date() }]);
    setIsLoading(true);
    
    const isAnswer = waitingForUser;
    setWaitingForUser(false);
    
    try {
      if (isAnswer) {
        await axios.post(`${API_BASE}/sessions/${workflowId}/answer`, { answer: userMsg });
      } else {
        await axios.post(`${API_BASE}/sessions/${workflowId}/message`, { message: userMsg });
      }
      startPolling(workflowId);
    } catch (err: any) {
      setMessages(prev => [...prev, { role: "system", content: `Send error: ${err.message}`, timestamp: new Date() }]);
      setIsLoading(false);
    }
  }, [workflowId, waitingForUser, startPolling]);

  const stopSession = useCallback(async () => {
    if (!workflowId) return;
    try { await axios.delete(`${API_BASE}/sessions/${workflowId}`); } catch {}
    if (pollRef.current) clearTimeout(pollRef.current);
    setWorkflowId(null); setIsConnected(false);
    setIsLoading(false); setWaitingForUser(false);
    setMessages([]); setSessionMeta(null);
  }, [workflowId]);

  return {
    messages,
    workflowId,
    isLoading,
    isConnected,
    waitingForUser,
    sessionMeta,
    startSession,
    sendMessage,
    stopSession
  };
}
