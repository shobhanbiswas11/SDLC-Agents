# Frontend Setup & Integration Guide

## Overview

The frontend is a **Next.js + React + Redux Toolkit** application that provides a conversational UI for the Dependency Resolver Agent backend.

### Key Features

- 🎨 **Interactive Chat Interface** - Real-time communication with the resolver via WebSocket
- 🔄 **Live Status Updates** - Resolver progress tracking with visual indicators
- ✅ **HITL Approval Flow** - Review and approve/reject lockfile proposals
- 📊 **Ecosystem Auto-Detection** - Automatically detects manifest type (PyPI, npm, Maven, Cargo)
- 🌐 **Multi-ecosystem Support** - Works with Python, Node.js, Java, and Rust

---

## Architecture

### Technology Stack

| Layer | Technology |
|-------|-----------|
| **Framework** | Next.js 14+ (React 18+) |
| **State Management** | Redux Toolkit |
| **Styling** | Tailwind CSS |
| **HTTP Client** | Axios |
| **WebSocket** | Native Web API |
| **Language** | TypeScript |

### Folder Structure

```
frontend/
├── src/
│   ├── app/
│   │   ├── dependency-resolver/page.tsx    # Main app page
│   │   ├── layout.tsx
│   │   └── providers.tsx
│   │
│   ├── components/
│   │   ├── Layout/                         # Layout components
│   │   └── Agent/                          # Agent-related components
│   │
│   ├── services/
│   │   ├── dependencyResolverService.ts    # Backend API integration
│   │   ├── agentService.ts
│   │   └── api.ts
│   │
│   ├── store/
│   │   ├── index.ts                        # Redux store setup
│   │   └── slices/
│   │       ├── dependencyResolverSlice.ts  # Resolver state management
│   │       └── ...other slices
│   │
│   ├── types/
│   │   └── dependencyResolver.ts           # TypeScript types
│   │
│   └── hooks/
│       └── index.ts
│
├── package.json
├── tsconfig.json
├── tailwind.config.ts
├── next.config.js
└── .env.local                              # Local environment
```

---

## Setup Instructions

### Prerequisites

- Node.js 18+ and npm/yarn
- Backend running on `http://localhost:8000`

### Installation

```bash
cd frontend
npm install
```

### Environment Configuration

Create `.env.local`:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Or use the default (localhost:8000).

### Development Server

```bash
npm run dev
```

App will be available at: **http://localhost:3000**

### Production Build

```bash
npm run build
npm start
```

---

## API Integration

### REST Endpoints Used

The frontend communicates with these backend REST endpoints:

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `POST` | `/api/sessions` | Create new resolution session |
| `GET` | `/api/sessions/{session_id}` | Get session state |
| `POST` | `/api/sessions/{session_id}/resolve` | Trigger resolver |
| `POST` | `/api/sessions/{session_id}/resume` | Resume after HITL review |
| `POST` | `/api/sessions/{session_id}/tool` | Execute a tool |
| `GET` | `/api/tools` | List available tools |

### WebSocket Connection

- **URL**: `ws://localhost:8000/ws/sessions/{session_id}/chat`
- **Purpose**: Real-time chat and resolver progress updates
- **Message Format**: JSON-encoded WebSocket frames

### Message Types

| Type | Direction | Purpose |
|------|-----------|---------|
| `user_message` | Client → Server | User sends a message |
| `agent_message` | Server → Client | Agent responds (may stream) |
| `solver_event` | Server → Client | Resolver progress (parse, fetch, resolve, etc.) |
| `tool_call` | Server → Client | Tool is being executed |
| `tool_result` | Server → Client | Tool execution result |
| `clarify` | Server → Client | Agent needs clarification |
| `approval_request` | Server → Client | Lockfile ready for review |
| `approval_response` | Client → Server | User approves/rejects |
| `system` | Server → Client | System notices |
| `error` | Server → Client | Error messages |

---

## User Workflows

### Workflow 1: Basic Resolution

```
1. User pastes manifest + selects ecosystem
2. Frontend creates session (POST /api/sessions)
3. Frontend connects WebSocket
4. Resolver runs automatically
5. User sees progress updates (solver_event)
6. User reviews lockfile (approval_request)
7. User clicks Approve/Reject
8. Lockfile delivered or resolution retried
```

### Workflow 2: Interactive Chat During Resolution

```
1. Manifest is being resolved
2. User types in chat: "show me the changelog for fastapi"
3. Frontend detects intent (changelog request)
4. Backend executes tool_call (fetch_changelog)
5. Frontend shows tool_call + tool_result frames
6. Agent provides human-readable response
```

### Workflow 3: GitHub URL Paste

```
1. User pastes: https://github.com/fastapi/fastapi
2. Frontend detects URL (deterministic router)
3. Backend fetches manifest from repo
4. Resolver re-runs with real manifest
5. Same flow as Workflow 1 from here
```

---

## Key Components

### `dependency-resolver/page.tsx` (Main App)

The main application page with:
- **SetupScreen**: Initial manifest input + ecosystem selection
- **ChatView**: Real-time chat interface with resolver progress
- **ProgressStrip**: Visual progress bar for resolver stages
- **Bubble**: Individual chat message renderer
- **ApprovalCard**: Lockfile review and decision interface

Key states managed via Redux:
- `sessionId`: Current session UUID
- `status`: Session state (created, active, pending_approval, etc.)
- `entries`: Chat message history
- `isConnected`: WebSocket connection status
- `finalLockfile`: Approved lockfile content

### `dependencyResolverService.ts` (API Layer)

Handles all communication with the backend:
- `createSession()` - Create new session
- `connectWS()` - Establish WebSocket connection
- `sendMessage()` - Send user message
- `sendApproval()` - Send approval decision
- `executeTool()` - Trigger tool execution
- `resumeSession()` - Resume after HITL

### `dependencyResolverSlice.ts` (Redux State)

Redux Toolkit slice managing:
- Session creation and connection
- Incoming WebSocket frames
- Chat entry history
- Approval state
- Error handling

---

## Features Implemented

### ✅ Implemented

- [x] Session creation and management
- [x] WebSocket chat connection
- [x] User message sending
- [x] Real-time message streaming
- [x] Resolver progress visualization
- [x] Approval/rejection flow
- [x] Ecosystem auto-detection (PyPI, npm, Maven, Cargo)
- [x] Error handling and display
- [x] Lockfile preview and download
- [x] New message types (tool_call, tool_result, clarify)

### 🚀 Future Enhancements

- [ ] Tool log panel (track all tool calls)
- [ ] Conflict visualization (graph view)
- [ ] CVE badge display
- [ ] Release notes embeds
- [ ] Session history/recovery
- [ ] Dark mode
- [ ] Mobile-responsive improvements
- [ ] Offline support (service worker)

---

## Troubleshooting

### WebSocket Connection Issues

**Error**: `WebSocket connection error`

**Solution**:
1. Verify backend is running on `http://localhost:8000`
2. Check CORS configuration in `app/main.py`
3. Verify WebSocket URL: `ws://localhost:8000/ws/sessions/{id}/chat`

### API Timeout

**Error**: `Failed to create session` or request timeouts

**Solution**:
1. Ensure backend is running
2. Check network tab in DevTools
3. Verify `NEXT_PUBLIC_API_URL` is set correctly

### Messages Not Sending

**Error**: `WebSocket not connected`

**Solution**:
1. Check connection status (live indicator in header)
2. Try reconnecting by creating new session
3. Check browser console for errors

---

## Development Tips

### Redux DevTools

Install [Redux DevTools Extension](https://github.com/reduxjs/redux-devtools-extension) for Chrome/Firefox to inspect Redux state.

### Hot Module Replacement

Next.js supports HMR out of the box. Changes to React components hot-reload without losing state.

### TypeScript Checking

```bash
npm run type-check
```

### Linting

```bash
npm run lint
```

---

## Performance Considerations

- **Message Streaming**: Agent responses are streamed token-by-token to provide real-time feedback
- **Redux Memoization**: Chat bubbles are memoized to prevent unnecessary re-renders
- **WebSocket**: Binary messages could be used for bandwidth optimization in the future

---

## Security Notes

- ✅ User input is validated on both frontend and backend
- ✅ No sensitive data stored in localStorage
- ✅ CORS is configured to restrict cross-origin requests
- ✅ WebSocket messages are JSON (not vulnerable to injection if properly escaped)

---

## Related Documentation

- **project.md** - Backend specification
- **claude.md** - Codebase reference
- **RUNNING.md** - Full stack setup

---

**Last Updated**: 2026-04-30  
**Version**: v0.0  
