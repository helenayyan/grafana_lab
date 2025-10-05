# Fast-Food Order Metrics Demo

This workspace simulates a lunch rush at a fast-food restaurant and publishes Prometheus metrics for Grafana dashboards.

## Run the stack

```bash
docker compose up --build
```

Services exposed locally:
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000 (default login `admin` / `admin`)
- Order metrics exporter: http://localhost:9101/metrics

To tweak the simulation, override environment variables when starting the compose stack, e.g.:

```bash
ORDER_FRIES_LUNCH_RATE=90 ORDER_SHAKE_LUNCH_RATE=40 docker compose up --build
```

The exporter is configured to generate orders for the 12:00–14:00 window and keeps serving the resulting metrics for Grafana dashboards.
