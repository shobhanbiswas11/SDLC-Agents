# SDLC Agents

We'll build all the SDLC agents here. This repository contains multiple autonomous agents designed to assist with various stages of the Software Development Life Cycle.

## Running with Docker

Each agent is fully containerized with its own frontend and backend. Their deployment configurations are located in the `infra/` directory.

### Prerequisites
Before running an agent for the first time, you must set up its environment variables:

1. Navigate to the agent's folder inside `infra/` (e.g., `infra/Architecture Design Agent`)
2. Make a copy of the `.env.example` file and rename it to `.env`.
3. Open the new `.env` file and insert your LLM API keys (e.g., Gemini, OpenAI, or Azure).

---

### 1. Architecture Design Agent

**Start the agent:**
```bash
cd "infra/Architecture Design Agent"
docker compose up --build
```
*(To run in the background, append `-d`)*

**Access URLs:**
* **Frontend UI:** [http://localhost:5173](http://localhost:5173)
* **Backend API:** [http://localhost:8000](http://localhost:8000)

---

### 2. Infrastructure as Code (IaC) Agent

**Start the agent:**
```bash
cd "infra/Infrastructure as Code Agent"
docker compose up --build
```
*(To run in the background, append `-d`)*

**Access URLs:**
* **Frontend UI:** [http://localhost:5174](http://localhost:5174)
* **Backend API:** [http://localhost:8001](http://localhost:8001)

---

### Useful Docker Commands

If you are using Windows `cmd`, remember these helpful commands while inside the agent's `infra/` folder:

* **Stop the agent:** `docker compose down`
* **Stop and wipe databases/volumes:** `docker compose down -v`
* **View logs (if running in `-d` background mode):** `docker compose logs -f`
* **Force a clean rebuild (bypassing cache):** `docker compose build --no-cache`

---

### Troubleshooting

**Problem: "Nothing is showing up on localhost" or "Failed to fetch"**

* **Cause:** The Docker containers might be completely stopped or shut down (e.g., if you previously ran `docker compose down` or restarted your computer).
* **Fix:** You must ensure the containers are actively running. Open your terminal in the agent's `infra/` folder and start them in the background by running:
  ```bash
  docker compose up -d
  ```
* **Verify:** Run `docker ps -a` in the terminal to see a list of running containers and their active ports.