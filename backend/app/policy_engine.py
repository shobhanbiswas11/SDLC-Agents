import re
from typing import Any

# ─────────────────────────────────────────────
# CONFIGURATION — tweak these for your org
# ─────────────────────────────────────────────

ALLOWED_REGIONS = [
    "ap-south-1", "us-east-1", "us-west-2", "eu-west-1"
]

BLOCKED_INSTANCE_TYPES = [
    "m5.2xlarge", "m5.4xlarge", "m5.8xlarge", "m5.12xlarge",
    "c5.4xlarge", "c5.9xlarge", "r5.4xlarge", "r5.8xlarge",
    "p3.2xlarge", "p3.8xlarge"  # GPU instances need approval
]

REQUIRED_TAGS = ["environment", "team", "project", "owner"]

MAX_NODE_REPLICAS = 10
MAX_CPU_REQUEST = "4"       # cores
MAX_MEMORY_REQUEST = "8Gi"

BLOCKED_DOCKER_IMAGES = ["latest"]  # force pinned versions


# ─────────────────────────────────────────────
# MAIN ENTRY POINT
# ─────────────────────────────────────────────

def evaluate_policies(content: Any, iac_type: str = "terraform") -> dict:
    """
    Evaluate IaC content against org-wide best practices.
    Accepts Terraform plan JSON, raw HCL string, YAML string, etc.
    """
    violations = []
    warnings = []

    if iac_type == "terraform":
        if isinstance(content, dict):
            # Terraform plan JSON
            v, w = evaluate_terraform_plan(content)
        else:
            # Raw HCL string
            v, w = evaluate_terraform_hcl(str(content))
        violations.extend(v)
        warnings.extend(w)

    elif iac_type == "kubernetes":
        v, w = evaluate_kubernetes(str(content))
        violations.extend(v)
        warnings.extend(w)

    elif iac_type == "ansible":
        v, w = evaluate_ansible(str(content))
        violations.extend(v)
        warnings.extend(w)

    elif iac_type == "docker-compose":
        v, w = evaluate_docker_compose(str(content))
        violations.extend(v)
        warnings.extend(w)

    # Universal checks (apply to all IaC types)
    v, w = evaluate_universal(str(content))
    violations.extend(v)
    warnings.extend(w)

    return {
        "status": "FAIL" if violations else "PASS",
        "violations": violations,
        "warnings": warnings,
        "summary": build_summary(violations, warnings)
    }


# ─────────────────────────────────────────────
# UNIVERSAL CHECKS (all IaC types)
# ─────────────────────────────────────────────

def evaluate_universal(content: str) -> tuple:
    violations = []
    warnings = []

    # Hardcoded secrets
    secret_patterns = [
        (r'(?i)(password|passwd|pwd)\s*=\s*"[^"]+"', "Hardcoded password detected"),
        (r'(?i)(secret_key|secret)\s*=\s*"[^"]+"', "Hardcoded secret key detected"),
        (r'(?i)(api_key|apikey)\s*=\s*"[^"]+"', "Hardcoded API key detected"),
        (r'(?i)(access_key|aws_access_key_id)\s*=\s*"[^"]+"', "Hardcoded AWS access key detected"),
        (r'(?i)(token)\s*=\s*"[^"]+"', "Hardcoded token detected"),
        (r'AKIA[0-9A-Z]{16}', "AWS Access Key ID pattern detected in plaintext"),
    ]
    for pattern, message in secret_patterns:
        if re.search(pattern, content):
            violations.append(f"[SECRETS] {message}")

    # Overly permissive wildcards
    if re.search(r'"Action":\s*"\*"', content) or re.search(r"action:\s*'\*'", content):
        violations.append("[IAM] Wildcard Action '*' found — overly permissive policy")

    if re.search(r'"Resource":\s*"\*"', content):
        warnings.append("[IAM] Wildcard Resource '*' found — scope down if possible")

    # Blocked regions
    for region in re.findall(r'(?:region|location)\s*=\s*"([^"]+)"', content, re.IGNORECASE):
        if region not in ALLOWED_REGIONS:
            violations.append(f"[REGION] Region '{region}' is not in the approved list: {ALLOWED_REGIONS}")

    return violations, warnings


# ─────────────────────────────────────────────
# TERRAFORM CHECKS
# ─────────────────────────────────────────────

def evaluate_terraform_plan(plan_json: dict) -> tuple:
    violations = []
    warnings = []

    for resource in plan_json.get("resource_changes", []):
        r_type = resource.get("type", "")
        r_name = resource.get("name", "unknown")
        change = resource.get("change", {})
        after = change.get("after") or {}

        # ── EC2 / Compute ──
        if r_type == "aws_instance":
            instance_type = after.get("instance_type", "")
            if instance_type in BLOCKED_INSTANCE_TYPES:
                violations.append(f"[COST] EC2 '{r_name}': instance type '{instance_type}' requires approval")

            if not after.get("monitoring", False):
                warnings.append(f"[OBSERVABILITY] EC2 '{r_name}': detailed monitoring is disabled")

            if not after.get("ebs_optimized", False):
                warnings.append(f"[PERFORMANCE] EC2 '{r_name}': EBS optimization is disabled")

            tags = after.get("tags") or {}
            missing_tags = [t for t in REQUIRED_TAGS if t not in {k.lower() for k in tags}]
            if missing_tags:
                violations.append(f"[TAGGING] EC2 '{r_name}': missing required tags: {missing_tags}")

        # ── Security Groups ──
        if r_type == "aws_security_group":
            for rule in after.get("ingress", []):
                cidrs = rule.get("cidr_blocks", [])
                port = rule.get("from_port")
                if "0.0.0.0/0" in cidrs:
                    if port in [22, 3389]:
                        violations.append(f"[SECURITY] Security group '{r_name}': SSH/RDP open to the world (port {port})")
                    elif port == 0 and rule.get("protocol") == "-1":
                        violations.append(f"[SECURITY] Security group '{r_name}': ALL traffic open to 0.0.0.0/0")
                    else:
                        warnings.append(f"[SECURITY] Security group '{r_name}': port {port} open to 0.0.0.0/0")

            for rule in after.get("egress", []):
                if "0.0.0.0/0" in rule.get("cidr_blocks", []) and rule.get("protocol") == "-1":
                    warnings.append(f"[SECURITY] Security group '{r_name}': unrestricted outbound traffic")

        # ── S3 ──
        if r_type == "aws_s3_bucket":
            if after.get("acl") in ["public-read", "public-read-write"]:
                violations.append(f"[SECURITY] S3 bucket '{r_name}': public ACL '{after.get('acl')}' is not allowed")

            tags = after.get("tags") or {}
            missing_tags = [t for t in REQUIRED_TAGS if t not in {k.lower() for k in tags}]
            if missing_tags:
                violations.append(f"[TAGGING] S3 '{r_name}': missing required tags: {missing_tags}")

        if r_type == "aws_s3_bucket_server_side_encryption_configuration":
            rules = after.get("rule", [])
            if not rules:
                violations.append(f"[ENCRYPTION] S3 bucket '{r_name}': server-side encryption not configured")

        if r_type == "aws_s3_bucket_public_access_block":
            for field in ["block_public_acls", "block_public_policy", "ignore_public_acls", "restrict_public_buckets"]:
                if not after.get(field, False):
                    violations.append(f"[SECURITY] S3 '{r_name}': '{field}' is not enabled")

        # ── RDS ──
        if r_type == "aws_db_instance":
            if not after.get("storage_encrypted", False):
                violations.append(f"[ENCRYPTION] RDS '{r_name}': storage encryption is disabled")

            if after.get("publicly_accessible", False):
                violations.append(f"[SECURITY] RDS '{r_name}': database is publicly accessible")

            if not after.get("deletion_protection", False):
                warnings.append(f"[RELIABILITY] RDS '{r_name}': deletion protection is disabled")

            if not after.get("backup_retention_period", 0):
                violations.append(f"[BACKUP] RDS '{r_name}': automated backups are disabled")

            if not after.get("multi_az", False):
                warnings.append(f"[RELIABILITY] RDS '{r_name}': Multi-AZ is disabled")

        # ── IAM ──
        if r_type == "aws_iam_policy":
            policy_doc = str(after.get("policy", ""))
            if '"Effect": "Allow"' in policy_doc and '"Action": "*"' in policy_doc:
                violations.append(f"[IAM] IAM policy '{r_name}': grants Allow on all actions (*)")

        if r_type == "aws_iam_role":
            tags = after.get("tags") or {}
            missing_tags = [t for t in REQUIRED_TAGS if t not in {k.lower() for k in tags}]
            if missing_tags:
                warnings.append(f"[TAGGING] IAM role '{r_name}': missing recommended tags: {missing_tags}")

        # ── EKS ──
        if r_type == "aws_eks_cluster":
            if not after.get("encryption_config"):
                violations.append(f"[ENCRYPTION] EKS cluster '{r_name}': secrets encryption is not configured")

            logs = after.get("enabled_cluster_log_types", [])
            required_logs = {"api", "audit", "authenticator"}
            missing_logs = required_logs - set(logs)
            if missing_logs:
                warnings.append(f"[OBSERVABILITY] EKS '{r_name}': missing log types: {missing_logs}")

        # ── Lambda ──
        if r_type == "aws_lambda_function":
            if after.get("tracing_config", {}).get("mode") != "Active":
                warnings.append(f"[OBSERVABILITY] Lambda '{r_name}': X-Ray tracing is not active")

            if not after.get("reserved_concurrent_executions"):
                warnings.append(f"[RELIABILITY] Lambda '{r_name}': no concurrency limit set")

        # ── ElasticSearch / OpenSearch ──
        if r_type in ["aws_elasticsearch_domain", "aws_opensearch_domain"]:
            if not after.get("encrypt_at_rest", {}).get("enabled", False):
                violations.append(f"[ENCRYPTION] OpenSearch '{r_name}': encryption at rest is disabled")

            if not after.get("node_to_node_encryption", {}).get("enabled", False):
                violations.append(f"[ENCRYPTION] OpenSearch '{r_name}': node-to-node encryption is disabled")

    return violations, warnings


def evaluate_terraform_hcl(content: str) -> tuple:
    """Static analysis of raw HCL when terraform plan JSON is unavailable."""
    violations = []
    warnings = []

    if re.search(r'instance_type\s*=\s*"(' + '|'.join(BLOCKED_INSTANCE_TYPES) + ')"', content):
        violations.append("[COST] Blocked instance type detected in HCL")

    if re.search(r'0\.0\.0\.0/0', content):
        warnings.append("[SECURITY] Open CIDR 0.0.0.0/0 detected — review ingress/egress rules")

    if re.search(r'acl\s*=\s*"public', content):
        violations.append("[SECURITY] Public ACL detected on a resource")

    if re.search(r'publicly_accessible\s*=\s*true', content):
        violations.append("[SECURITY] Resource set to publicly_accessible = true")

    if re.search(r'storage_encrypted\s*=\s*false', content):
        violations.append("[ENCRYPTION] storage_encrypted explicitly set to false")

    if re.search(r'deletion_protection\s*=\s*false', content):
        warnings.append("[RELIABILITY] deletion_protection is explicitly disabled")

    if not re.search(r'tags\s*=\s*\{', content):
        warnings.append("[TAGGING] No tags block found in HCL")

    return violations, warnings


# ─────────────────────────────────────────────
# KUBERNETES CHECKS
# ─────────────────────────────────────────────

def evaluate_kubernetes(content: str) -> tuple:
    violations = []
    warnings = []

    # Running as root
    if re.search(r'runAsRoot:\s*true', content) or re.search(r'runAsUser:\s*0\b', content):
        violations.append("[SECURITY] Container configured to run as root user")

    if not re.search(r'runAsNonRoot:\s*true', content):
        warnings.append("[SECURITY] runAsNonRoot is not set to true")

    # Privileged containers
    if re.search(r'privileged:\s*true', content):
        violations.append("[SECURITY] Privileged container detected — grants root-level host access")

    # Allow privilege escalation
    if re.search(r'allowPrivilegeEscalation:\s*true', content):
        violations.append("[SECURITY] allowPrivilegeEscalation is true")

    if not re.search(r'allowPrivilegeEscalation:\s*false', content):
        warnings.append("[SECURITY] allowPrivilegeEscalation not explicitly set to false")

    # Resource limits
    if not re.search(r'resources:', content):
        violations.append("[RELIABILITY] No resource requests/limits defined — risk of resource starvation")
    else:
        if not re.search(r'limits:', content):
            violations.append("[RELIABILITY] Resource limits not set")
        if not re.search(r'requests:', content):
            warnings.append("[RELIABILITY] Resource requests not set")

    # Liveness / readiness probes
    if not re.search(r'livenessProbe:', content):
        warnings.append("[RELIABILITY] livenessProbe not configured")

    if not re.search(r'readinessProbe:', content):
        warnings.append("[RELIABILITY] readinessProbe not configured")

    # Replica count
    replicas = re.search(r'replicas:\s*(\d+)', content)
    if replicas:
        count = int(replicas.group(1))
        if count > MAX_NODE_REPLICAS:
            violations.append(f"[COST] Replica count {count} exceeds org limit of {MAX_NODE_REPLICAS}")
        if count < 2:
            warnings.append(f"[RELIABILITY] Only {count} replica(s) — consider at least 2 for HA")

    # Image tag pinning
    images = re.findall(r'image:\s*([^\s]+)', content)
    for image in images:
        tag = image.split(":")[-1] if ":" in image else "latest"
        if tag in BLOCKED_DOCKER_IMAGES or not re.match(r'.+:.+', image):
            violations.append(f"[RELIABILITY] Image '{image}' uses unpinned or 'latest' tag")

    # Host network / PID
    if re.search(r'hostNetwork:\s*true', content):
        violations.append("[SECURITY] hostNetwork: true shares the host network namespace")

    if re.search(r'hostPID:\s*true', content):
        violations.append("[SECURITY] hostPID: true shares the host PID namespace")

    # Read-only filesystem
    if not re.search(r'readOnlyRootFilesystem:\s*true', content):
        warnings.append("[SECURITY] readOnlyRootFilesystem not set to true")

    # Namespace
    if not re.search(r'namespace:', content):
        warnings.append("[GOVERNANCE] No namespace specified — will deploy to default namespace")

    return violations, warnings


# ─────────────────────────────────────────────
# ANSIBLE CHECKS
# ─────────────────────────────────────────────

def evaluate_ansible(content: str) -> tuple:
    violations = []
    warnings = []

    # Running as root / become root without need
    if re.search(r'become:\s*yes', content) or re.search(r'become:\s*true', content):
        warnings.append("[SECURITY] 'become: yes' used — ensure privilege escalation is necessary")

    if re.search(r'remote_user:\s*root', content):
        violations.append("[SECURITY] remote_user set to root — use a non-root user with sudo")

    # Hardcoded passwords in vars
    if re.search(r'ansible_password:\s*\S+', content):
        violations.append("[SECRETS] ansible_password found in plaintext — use Ansible Vault")

    if re.search(r'ansible_become_password:\s*\S+', content):
        violations.append("[SECRETS] ansible_become_password found in plaintext — use Ansible Vault")

    # Shell/command module (prefer specific modules)
    shell_count = len(re.findall(r'^\s*-?\s*(shell|command):', content, re.MULTILINE))
    if shell_count > 3:
        warnings.append(f"[BEST PRACTICE] {shell_count} shell/command tasks found — prefer idempotent Ansible modules")

    # No_log for sensitive tasks
    if re.search(r'password', content, re.IGNORECASE) and not re.search(r'no_log:\s*true', content):
        warnings.append("[SECRETS] Password-related task found without 'no_log: true'")

    # Ignore errors
    if re.search(r'ignore_errors:\s*(yes|true)', content):
        warnings.append("[RELIABILITY] 'ignore_errors: true' found — errors may go undetected")

    # Tags missing
    if not re.search(r'tags:', content):
        warnings.append("[GOVERNANCE] No tags defined on tasks — tagging aids selective execution")

    # File permissions
    if re.search(r'mode:\s*0?777', content):
        violations.append("[SECURITY] File permission 777 detected — overly permissive")

    if re.search(r'mode:\s*0?666', content):
        warnings.append("[SECURITY] File permission 666 detected — review if write access for all is needed")

    return violations, warnings


# ─────────────────────────────────────────────
# DOCKER COMPOSE CHECKS
# ─────────────────────────────────────────────

def evaluate_docker_compose(content: str) -> tuple:
    violations = []
    warnings = []

    # Privileged mode
    if re.search(r'privileged:\s*true', content):
        violations.append("[SECURITY] Privileged mode enabled — grants full host access")

    # Image pinning
    images = re.findall(r'image:\s*([^\s]+)', content)
    for image in images:
        tag = image.split(":")[-1] if ":" in image else "latest"
        if tag in BLOCKED_DOCKER_IMAGES:
            violations.append(f"[RELIABILITY] Image '{image}' uses 'latest' tag — pin to a specific version")

    # Exposed ports
    if re.search(r'ports:', content):
        exposed = re.findall(r'-\s*["\']?(\d+):(\d+)', content)
        for host_port, container_port in exposed:
            if host_port in ["22", "3306", "5432", "6379", "27017"]:
                violations.append(f"[SECURITY] Sensitive port {host_port} bound to host — avoid exposing DB/SSH ports")

    # Environment variables with secrets
    if re.search(r'environment:', content):
        if re.search(r'(?i)(password|secret|api_key|token):\s*\S+', content):
            violations.append("[SECRETS] Secrets detected in environment variables — use Docker secrets or .env files")

    # Resource limits
    if not re.search(r'mem_limit|memory:', content):
        warnings.append("[RELIABILITY] No memory limits set — containers may consume unbounded memory")

    if not re.search(r'cpus:|cpu_shares:', content):
        warnings.append("[RELIABILITY] No CPU limits set")

    # Restart policy
    if not re.search(r'restart:', content):
        warnings.append("[RELIABILITY] No restart policy defined — consider 'unless-stopped' or 'on-failure'")

    # Volume mounts — host path mounts can be risky
    if re.search(r'volumes:', content):
        host_mounts = re.findall(r'-\s*["\']?(/[^:]+):', content)
        sensitive_paths = ["/etc", "/var/run/docker.sock", "/proc", "/sys", "/root"]
        for mount in host_mounts:
            if any(mount.startswith(p) for p in sensitive_paths):
                violations.append(f"[SECURITY] Sensitive host path '{mount}' mounted into container")

    # Networks — default bridge is less isolated
    if not re.search(r'networks:', content):
        warnings.append("[SECURITY] No custom network defined — services share default bridge network")

    return violations, warnings


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def build_summary(violations: list, warnings: list) -> str:
    if not violations and not warnings:
        return "✅ All policies passed with no issues."

    parts = []
    if violations:
        parts.append(f"{len(violations)} violation(s) found")
    if warnings:
        parts.append(f"{len(warnings)} warning(s) found")

    return " | ".join(parts)