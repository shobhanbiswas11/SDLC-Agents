#!/bin/bash
WF_ID=$(curl -s -X POST http://localhost:8001/api/workflows \
  -H "Content-Type: application/json" \
  -d '{"agent_id": "reviewer", "workspace_path": "ArifRahaman/blog-website"}' | jq -r '.workflow_id')

curl -s -X POST "http://localhost:8001/api/workflows/$WF_ID/messages" \
  -H "Content-Type: application/json" \
  -d '{"message": "find App.jsx and give me the short summary and comments"}' > /dev/null

echo "Checking WF $WF_ID..."
for i in {1..8}; do
   curl -s http://localhost:8001/api/workflows/$WF_ID/status | jq '.status | {status, message_count, last: .last_response[0:60]}'
   sleep 4
done
