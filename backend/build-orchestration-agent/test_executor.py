from app.executor.podman_runner import PodmanExecutor
from app.analyzer.log_parser import LogAnalyzer
from app.reasoner.azure_llm import AzureReasoner
from app.controller.agent_loop import BuildAgent

executor = PodmanExecutor()
analyzer = LogAnalyzer()
reasoner = AzureReasoner()

agent = BuildAgent(executor, analyzer, reasoner)

result = agent.run("./sample-node-project")

print("\n=== FINAL RESULT ===")
print(result)