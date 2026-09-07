# Centralized Monitoring & Logging Stack

A production-ready, containerized observability solution built with Prometheus, Grafana, Loki, Alertmanager, Traefik, and Grafana Alloy. This repository provides a dual-component deployment architecture: a centralized **Monitoring Server** that collects, processes, and visualizes metrics and logs, and lightweight **Edge Node Agents** deployed on target servers.

---

## Architecture Overview

```
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

---

## Core Features

- **Centralized Metrics Collection:** Ingestion of OS metrics and container metrics via Prometheus Remote Write receiver.
- **Multi-Tenant Log Aggregation:** Centralized Loki logging engine supporting isolated tenant log streams (e.g., `production`, `staging`).
- **Modern Edge Agent:** Utilization of Grafana Alloy (replacing legacy Promtail and Node Exporter) for lightweight metrics and log forwarding.
- **Automated Reverse Proxy & SSL:** SSL certificate generation (Let's Encrypt) and Basic Authentication enforcement handled by Traefik v3.
- **Pre-configured Provisioning:** Automated Grafana provisioning for datasources and pre-built operational dashboards.
- **Unified Alerting System:** Rule-based alerting via Prometheus and Loki Ruler routed through Alertmanager with localized HTML email notifications.
- **Resource Constrained:** CPU and memory limits applied across all containerized services to ensure system stability.

---

## Project Structure

```
.
├── Monitoring-Server/
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
│   └── docker-compose-prod.yml      # Edge agent deployment stack
└── README.md
```

---

## Deployment Instructions

### Prerequisites

- Docker Engine 20.10+
- Docker Compose v2+
- Domain names configured with DNS A records pointing to your Monitoring Server:
  - `prom.yourdomain.com`
  - `grafana.yourdomain.com`
  - `loki.yourdomain.com`

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
htpasswd -cb "./Monitoring-Server/traefik/htpasswd" alloy-agent "YOUR_SECURE_PASSWORD"
```

#### 3. Environment Variables Setup
Create a `.env` file in `./Monitoring-Server/`:

```env
PROMETHEUS_VERSION=v2.54.1
GRAFANA_VERSION=11.2.0
LOKI_VERSION=3.1.0

GRAFANA_USER=admin
GRAFANA_PASS=YOUR_GRAFANA_PASSWORD

SMTP_FROM=your-email@gmail.com
SMTP_TO=destination-email@gmail.com
SMTP_PASSWORD=your-app-password
```

#### 4. Service Launch
Navigate to the server directory and start the stack:

```bash
cd "Monitoring-Server"
docker compose up -d
```

---

### Phase 2: Deploy Node Agents (Edge Servers)

Deploy Grafana Alloy on every Linux node or application server you wish to monitor.

#### 1. Environment Configuration
Create a `.env` file in the `./Nodes/` directory:

```env
NODE_NAME=node-production-01
ENVIRONMENT_NAME=production
```

#### 2. Agent Configuration Update
Update `./Nodes/config.alloy` with your monitoring server endpoints and basic auth credentials matching those created in Phase 1:

```alloy
prometheus.remote_write "central_monitoring" {
  endpoint {
    url = "https://prom.yourdomain.com/api/v1/write"
    basic_auth {
      username = "alloy-agent"
      password = "YOUR_SECURE_PASSWORD"
    }
  }
}

loki.write "central_loki" {
  endpoint {
    url = "https://loki.yourdomain.com/loki/api/v1/push"
    tenant_id = sys.env("ENVIRONMENT_NAME")
    basic_auth {
      username = "alloy-agent"
      password = "YOUR_SECURE_PASSWORD"
    }
  }
}
```

#### 3. Launch Node Agent
Start the Alloy container on the target node:

```bash
cd Nodes
docker compose -f docker-compose-prod.yml up -d
```

---

## Alerting & Log Rules

### Metrics Alerts
Defined in `./Monitoring-Server/prometheus/alerts/node_rules.yml`:
- **HighCPUUsage:** Triggers when average CPU usage exceeds 85% for 5 minutes.
- **HighMemoryUsage:** Triggers when available memory drops below 10% for 5 minutes.
- **LowDiskSpace:** Triggers when root filesystem free space drops below 10%.
- **NodeDown:** Triggers immediately when target scraping fails for over 3 minutes.

### Log Alerts (Loki Ruler)
Defined under `./Monitoring-Server/loki/rules/`:
- **SSHLoginSuccessful:** Monitors auth logs and fires security alerts on successful SSH logins in production.
- **HighHttp500Errors:** Tracks HTTP 500 error rates from web server container logs with threshold differentiation between staging and production environments.

---

## Security Best Practices

1. **Secrets Isolation:** Never commit secrets, passphrases, or `.env` files to source control.
2. **Reverse Proxy Protection:** Prometheus and Loki endpoints are isolated behind Traefik Basic Auth middleware.
3. **Multi-Tenancy:** Loki operates with `auth_enabled: true` to prevent cross-environment log leakage.
4. **TLS Encryption:** All agent-to-server traffic is encrypted using Let's Encrypt automated TLS certificates.

---

## License

Distributed under the MIT License. See `LICENSE` for details.
