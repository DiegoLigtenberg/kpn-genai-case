# kpn-genai-case

Case for AI engineer KPN — invoice extraction, deterministic policy (ACCEPT/REJECT), and a small web UI.

## Demo

Normalized invoice preview (left) and extracted fields + policy outcome (right). Per-item amounts are summed and checked against the document total within tolerance.

![Invoice demo: preview and extraction result](image.png)

## Docker

Build from the **repository root**:

```bash
docker build -f docker/backend.Dockerfile -t kpn-genai-backend:latest .
docker build -f docker/frontend.Dockerfile -t kpn-genai-frontend:latest .
# Optional: --build-arg VITE_API_BASE_URL=http://<host>:<port> where the API is reachable from the browser
```

The frontend image serves the built SPA with `serve` and bakes `VITE_API_BASE_URL` (default `http://127.0.0.1:8000` in `docker/frontend.Dockerfile`) so the browser calls the API directly; set `CORS_ORIGINS` on the backend for your UI origin (see `.env.template`). Configure LLM env vars for the backend as needed.

## Helm (Kubernetes)

Minimal chart: **backend** Deployment + Service, **frontend** Deployment + Service. The UI image expects the API at the URL baked at build time (see `docker/frontend.Dockerfile`); use `kubectl port-forward` to the backend (see chart `NOTES.txt`) or rebuild with `VITE_API_BASE_URL` and set `backend.corsOrigins` to your UI URL.

```bash
helm install kpn ./helm/kpn-genai
```

With default `values.yaml`, the UI is exposed as a **NodePort** on **30080**. Open `http://<node-ip>:30080` (or use `kubectl port-forward svc/<release>-kpn-genai-frontend 8080:80` if you switch the service to `ClusterIP` in `values.yaml`).

Images must exist on the cluster nodes (or set `image.*.repository` to a registry path and push the images built above).
