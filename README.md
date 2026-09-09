```markdown
# Centralized Monitoring & Logging Stack

A production-ready, containerized observability solution built with Prometheus, Grafana, Loki, Alertmanager, Traefik, and Grafana Alloy. This repository provides a dual-component deployment architecture: a centralized **Monitoring Server** that collects, processes, and visualizes metrics and logs, and lightweight **Edge Node Agents** deployed on target servers.

---

## Architecture Overview

```text
                          +-----------------------------------+
                          |            Edge Nodes             |
                          | (Linux Servers / Docker Host)     |
                          |                                   |
                          |    +-------------------------+    |
                          |    |      Grafana Alloy      |    |
                          |    | (Node / cAdvisor / Logs)|    |
                          |    +------------+------------+    |
                          +-----------------|-----------------+
                                            |
                         HTTPS Remote Write | HTTPS Log Push
                         (Basic Auth)       | (Tenant Header)
                                            v
+-----------------------------------------------------------------------------------+
|                                 Monitoring Server                                 |
|                                                                                   |
|  +-----------------------------------------------------------------------------+  |
|  |                            Traefik Reverse Proxy                            |  |
|  |                   (TLS Termination, ACME, Basic Auth)                       |  |
|  +---------+------------------------------+--------------------------+---------+  |
|            |                              |                          |            |
|            v                              v                          v            |
|    +---------------+              +---------------+          +---------------+    |
|    |  Prometheus   |<-------------|    Grafana    |--------->|     Loki      |    |
|    | (Remote Write)|              | (Dashboards & |          | (Multi-tenant |    |
|    +-------+-------+              | Datasources)  |          | Log Storage)  |    |
|            |                      +---------------+          +-------+-------+    |
|            v                                                         |            |
|    +---------------+                                                 |            |
|    | Alertmanager  |<------------------------------------------------+            |
|    | (SMTP Email)  |               Loki Alerting Rules                            |
|    +---------------+                                                              |
+-----------------------------------------------------------------------------------+

```

### Architectural Note: Environments vs. Servers

Environments represent logical separations (e.g., `production`, `staging`), not physical servers. Multiple servers can be members of a single environment. To add new environments, both the Prometheus and Loki configuration files must be updated accordingly.

---

## Core Features

* **Centralized Metrics Collection:** Ingestion of OS metrics and container metrics via Prometheus Remote Write receiver.
* **Multi-Tenant Log Aggregation:** Centralized Loki logging engine supporting isolated tenant log streams (e.g., `production`, `staging`).
* **Modern Edge Agent:** Utilization of Grafana Alloy (replacing legacy Promtail and Node Exporter) for lightweight metrics and log forwarding.
* **Automated Reverse Proxy & SSL:** SSL certificate generation utilizing the Let's Encrypt DNS Challenge via Cloudflare, and Basic Authentication enforcement handled by Traefik v3.
* **Pre-configured Provisioning:** Automated Grafana provisioning for datasources and pre-built operational dashboards.
* **Unified Alerting System:** Rule-based alerting via Prometheus and Loki Ruler routed through Alertmanager with localized HTML email notifications. An SMTP server must be actively set up with its password defined in the configuration for alerts to be delivered.
* **Resource Constrained:** CPU and memory limits applied across all containerized services to ensure system stability.

---

## Project Structure

```text
.
├── Monitoring_Server/
│   ├── alertmanager/
│   │   └── alertmanager.yml         # Email alert routing configuration
│   ├── docker-compose.yml           # Core services deployment stack
│   ├── grafana/
│   │   └── provisioning/            # Pre-configured datasources and dashboards
│   ├── loki/
│   │   ├── loki-config.yml          # Loki engine and ruler configuration
│   │   └── rules/                   # Log alert rules (production & staging)
│   ├── prometheus/
│   │   ├── alerts/                  # Node and hardware alert rules
│   │   └── prometheus.yml           # Prometheus scrape and remote write settings
│   └── traefik/
│       └── htpasswd                 # Basic Auth user credentials
├── Nodes/
│   ├── config.alloy                 # Grafana Alloy collection pipelines
│   └── docker-compose.yml           # Edge agent deployment stack
└── README.md

```

---

## Environment Management (Multi-Tenancy)

This architecture utilizes Loki's multi-tenancy feature. It is crucial to understand that the environment definition separates environments, not individual servers. Multiple servers can belong to a single environment (e.g., multiple nodes can be part of the `production` environment).

To add a new environment (e.g., `development`):

1. Create a new folder matching the exact environment name under `./Monitoring_Server/loki/rules/development/`.
2. Add a new datasource entry for the new environment in `./Monitoring_Server/grafana/provisioning/datasources/datasources.yml`, ensuring the `X-Scope-OrgID` matches the environment name.
3. On the target Node, set `ENVIRONMENT_NAME=development` in the `.env` file so Alloy passes the correct tenant header.

---

## Deployment Instructions

### Prerequisites

* Docker Engine 20.10+
* Docker Compose v2+
* Domain names configured with DNS A records pointing to your Monitoring Server:
* `prom.yourdomain.com`
* `grafana.yourdomain.com`
* `loki.yourdomain.com`


* A configured SMTP server for Alertmanager to send notifications.
* Cloudflare API Token for Let's Encrypt DNS Challenge.

---

### Phase 1: Deploy Monitoring Server

#### 1. Volume Initialization

Create the required external Docker volumes for persistent storage:

```bash
docker volume create prometheus_data
docker volume create grafana_data
docker volume create loki_data

```

#### 2. Authentication Configuration

Generate basic authentication credentials for secured endpoints (Prometheus, Loki):

```bash
sudo apt-get install apache2-utils -y
htpasswd -cb "./Monitoring_Server/traefik/htpasswd" alloy-agent "YOUR_SECURE_PASSWORD"

```

#### Deep-Dive: How Alertmanager Dynamic Configuration Works

If you are wondering how `alertmanager.yml` receives its credentials from the `.env` file without hardcoding secrets into git, here is the architectural mechanism used in this project:

1. **The Template File:** Inside the `./Monitoring_Server/alertmanager/` directory, instead of a static configuration, there is a template file (often named `alertmanager.yml.template` or handled directly via entrypoint scripts) containing placeholder variables like `__SMTP_FROM__`, `__SMTP_TO__`, and `__SMTP_PASSWORD__`.
2. **Runtime Substitution via `sed`:** When the Alertmanager container starts up, the entrypoint script executes a series of `sed` (Stream Editor) commands. It reads the environment variables defined in your `./Monitoring_Server/.env` file (`SMTP_FROM`, `SMTP_TO`, `SMTP_PASSWORD`) and dynamically replaces the placeholders in the template.
3. **Generated Config:** The final, populated `alertmanager.yml` is generated dynamically inside the container at runtime before the Alertmanager daemon process actually boots up.
   - *Why this matters:* This ensures your sensitive SMTP credentials never leak into your version control system while keeping Alertmanager fully configured automatically upon every `docker compose up -d`.

#### 3. Environment Variables Setup

Create a `.env` file in `./Monitoring_Server/`:

```env
PROMETHEUS_VERSION=v2.54.1
GRAFANA_VERSION=11.2.0
LOKI_VERSION=3.1.0

GRAFANA_USER=admin
GRAFANA_PASS=YOUR_GRAFANA_PASSWORD

# SMTP Configuration is strictly required for alerting
SMTP_FROM=your-email@gmail.com
SMTP_TO=destination-email@gmail.com
# Use an App Password if using Gmail or similar services
SMTP_PASSWORD=your-app-password

# Cloudflare DNS Challenge Token
CF_DNS_API_TOKEN=your-cloudflare-token

```

*Note on Alertmanager: The `alertmanager.yml` file acts as a template. The actual values are populated dynamically at runtime using the `sed` command passed through the container's entrypoint.*

#### 4. Service Launch

Navigate to the server directory and start the stack:

```bash
cd "Monitoring_Server"
docker compose up -d

```

#### 5. Accessing Grafana & Verification
Once the monitoring server stack is fully up and running, you can access the provisioned web interfaces through your configured reverse proxy domains:

- **Grafana Dashboard:** `https://grafana.yourdomain.com`
  - **Username:** The value defined in `GRAFANA_USER` (e.g., `admin`).
  - **Password:** The value defined in `GRAFANA_PASS` in your `./Monitoring_Server/.env` file.
- **Prometheus UI:** `https://prom.yourdomain.com` (Protected by Traefik Basic Auth)[cite: 5].
- **Loki Endpoint:** `https://loki.yourdomain.com` (Protected by Traefik Basic Auth)[cite: 5].

---

### Phase 2: Deploy Node Agents (Edge Servers)

Deploy Grafana Alloy on every Linux node or application server you wish to monitor.

#### 1. Environment Configuration

Create a `.env` file in the `./Nodes/` directory. **Ensure that `NODE_NAME` is strictly unique for every deployment to prevent metric collision:**

```env
NODE_NAME=node-production-01
ENVIRONMENT_NAME=production
ALLOY_BASIC_AUTH_USER=alloy-agent
ALLOY_BASIC_AUTH_PASS=YOUR_SECURE_PASSWORD

```

#### 2. Agent Configuration Update

Update `./Nodes/config.alloy` with your monitoring server endpoints and basic auth credentials matching those created in Phase 1:

```alloy
prometheus.remote_write "central_monitoring" {
  endpoint {
    url = "https://prom.krnl.ir/api/v1/write"
    basic_auth {
      username = sys.env("ALLOY_BASIC_AUTH_USER")
      password = sys.env("ALLOY_BASIC_AUTH_PASS")
    }
  }
}

loki.write "central_loki" {
  endpoint {
    url = "https://prom.krnl.ir/api/v1/write"
    tenant_id = sys.env("ENVIRONMENT_NAME")
    basic_auth {
      username = sys.env("ALLOY_BASIC_AUTH_USER")
      password = sys.env("ALLOY_BASIC_AUTH_PASS")
    }
  }
}

```

#### 3. Launch Node Agent

Start the Alloy container on the target node:

```bash
cd Nodes
docker compose up -d

```

---

## Alerting & Log Rules

**Alertmanager Configuration:** The `alertmanager.yml` file is dynamically populated using the `sed` command, substituting necessary environment variables directly via the entrypoint.

### Metrics Alerts

Defined in `./Monitoring_Server/prometheus/alerts/node_rules.yml`:

* **HighCPUUsage:** Triggers when average CPU usage exceeds 85% for 5 minutes.
* **HighMemoryUsage:** Triggers when available memory drops below 10% for 5 minutes.
* **LowDiskSpace:** Triggers when root filesystem free space drops below 10%.
* **NodeDown:** Triggers immediately when target scraping fails for over 3 minutes. To ensure accurate detection of downed nodes specific to this architecture, the following custom expression is utilized:

```yaml
- alert: NodeDown
  expr: (time() - max(timestamp(node_boot_time_seconds)) by (instance, environment)) > 120
  for: 1m
  labels:
    severity: critical
  annotations:
    summary: "Node {{ $labels.instance }} appears to be down ({{$labels.environment }})"
    description: "No metrics received from {{ $labels.instance }} for over 2 minutes in {{$labels.environment }}."

```

### Log Alerts (Loki Ruler)

Defined under `./Monitoring_Server/loki/rules/`:

* **SSHLoginSuccessful:** Monitors auth logs and fires security alerts on successful SSH logins in production.
* **HighHttp500Errors:** Tracks HTTP 500 error rates from web server container logs with threshold differentiation between staging and production environments.

---

## Operational Guides

### Adding a New Dashboard

When adding a new dashboard to the `dashboard` directory, you must substitute the datasource placeholder to ensure Grafana recognizes it and prevents legacy errors. Follow this procedure:

**Step 1 — Identify the exact placeholder name:**

```bash
grep -o '${DS_[A-Za-z0-9_]*}' grafana/provisioning/dashboards/your-dashboard.json | sort -u

```

*(The expected output is usually `${DS_PROMETHEUS}`)*

**Step 2 — Verify your datasource name:**

```bash
cat grafana/provisioning/datasources/datasources.yml

```

*(Search for the `name:` line; it is likely `Prometheus`)*

**Step 3 — Replace the placeholder:**

```bash
sed -i 's/${DS_PROMETHEUS}/Prometheus/g' grafana/provisioning/dashboards/your-dashboard.json

```

*(If your datasource has a different name, substitute `Prometheus` with that exact name)*

**Step 4 — Verify the placeholder has been removed:**

```bash
grep -c '${DS_' grafana/provisioning/dashboards/your-dashboard.json

```

*(This command must return `0`)*

**Step 5 — Apply changes:**

```bash
docker compose restart grafana

```

*(Open the newly added dashboard to confirm the legacy error no longer appears)*

---

## Security Best Practices

1. **Secrets Isolation:** Never commit secrets, passphrases, or `.env` files to source control.
2. **Reverse Proxy Protection:** Prometheus and Loki endpoints are isolated behind Traefik Basic Auth middleware.
3. **Multi-Tenancy:** Loki operates with `auth_enabled: true` to prevent cross-environment log leakage.
4. **TLS Encryption:** All agent-to-server traffic is encrypted using Let's Encrypt automated TLS certificates.

---


