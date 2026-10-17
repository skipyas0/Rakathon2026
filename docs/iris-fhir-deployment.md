# IRIS FHIR server: operation and web-app deployment

This guide covers the InterSystems IRIS for Health server used by MDT Copilot.
The commands assume Docker Desktop (or Docker Engine with Compose), `curl`, and
`uv`. Run them from the repository root unless indicated otherwise.

## How it works

IRIS stores FHIR R4 resources and exposes a REST API. The application backend
reads patients and their related resources over HTTP; it does not connect to the
IRIS database directly. Authentication uses HTTP Basic auth.

```text
Browser -> web app :8000 -> IRIS :52773/fhir/r4 -> durable database volume
           React + FastAPI
```

The [application Dockerfile](../Dockerfile) builds React and packages it with
FastAPI. FastAPI serves both the built frontend and `/api` on port 8000.
The browser calls the backend, so IRIS credentials stay on the server side.

| URL on the Docker host | Purpose |
|---|---|
| `http://localhost:52773/fhir/r4` | FHIR API base URL |
| `http://localhost:52773/fhir/r4/metadata` | FHIR CapabilityStatement |
| `http://localhost:52773/csp/sys/UtilHome.csp` | IRIS Management Portal |
| `http://localhost:8000` | Containerized MDT Copilot |

**A 404 at `http://localhost:52773/` does not mean IRIS is down.** Use
`/fhir/r4/metadata` to test the FHIR service. Metadata can be available without
authentication even though patient reads require it. Development credentials are
`SuperUser` / `SYS`; an unauthenticated patient request returns 401.

The organisers' dataset is loaded by
[load_fhir.py](../backend/src/mdt_backend/load_fhir.py). It converts collection
bundles into transaction bundles of PUT requests, preserves resource IDs where
valid, and normalizes the dataset's known FHIR R4 incompatibilities. Reloading
updates resources with the same IDs; it is not a backup or a reset.

## Existing Docker configuration

The root [docker-compose.yml](../docker-compose.yml) defines **HAPI**, not IRIS,
as service `fhir` on port 8080. Its `app` service points at that HAPI service.
Starting the root stack unchanged does not make the app use IRIS.

The IRIS configuration lives in
[the kit's docker-compose.yml](../FHIR-AI-Kit/docker-iris-fhir/docker-compose.yml):

| Setting | Effect |
|---|---|
| Service `iris`, container `iris-fhir` | Fixed container name; only one such container can exist on a Docker engine |
| Build context `.` | Builds from the kit's Dockerfile, relative to its Compose directory |
| `1972:1972` | Native IRIS protocol, used by host-side initialization |
| `52773:52773` | HTTP FHIR API and Management Portal |
| `ISC_DATA_DIRECTORY=/durable` | IRIS durable database/configuration location |
| `iris-data:/durable` | Named volume retains data across container replacement |
| `./:/home/irisowner/dev` | Development bind mount of the kit directory |

The [IRIS Dockerfile](../FHIR-AI-Kit/docker-iris-fhir/Dockerfile):

- Uses `intersystems/irishealth-community:latest-cd` (a moving Community image).
- Sets the IRIS executable/Python paths and development credentials.
- Prepares directories owned by `irisowner` and copies Swagger UI files.
- Starts IRIS during the build to merge [merge.cpf](../FHIR-AI-Kit/docker-iris-fhir/merge.cpf)
  and remove password expiration, then stops it. The inherited image entrypoint
  runs IRIS when the container starts.

Building the image does **not** create the `/fhir/r4` service. The separate
[native setup script](../FHIR-AI-Kit/docker-iris-fhir/fhir_server_setup_native.py)
creates namespace `FHIRSERVER`, installs the JSON/SQL storage strategy, and
installs the FHIR R4 `4.0.1` endpoint.

**Do not use the kit's `start.sh` for routine restarts or this dataset's initial
load.** It invokes the setup script's full `install()`, which also imports the
kit's sample patients. MDT Copilot uses the organisers' six patients instead.

At verification on 2026-10-17, the existing container used:

- Compose project: `docker-iris-fhir`.
- Durable volume: `docker-iris-fhir_iris-data`.
- Runtime restart policy: `unless-stopped`, applied using `docker update`.

The kit's Compose file does not declare that restart policy, so container
recreation from that file alone need not preserve it.

## Restart the existing server

Start Docker Desktop and wait for the engine. On macOS, if `docker` is not on
your shell's PATH:

```bash
export PATH="/Applications/Docker.app/Contents/Resources/bin:$PATH"
```

Then:

```bash
docker start iris-fhir
docker update --restart unless-stopped iris-fhir
docker ps --filter name=iris-fhir

curl --fail --show-error --retry 30 --retry-delay 2 --retry-all-errors \
  --connect-timeout 5 --max-time 15 \
  -u 'SuperUser:SYS' \
  'http://localhost:52773/fhir/r4/Patient?_summary=count'
```

For the currently loaded dataset, the response is a FHIR Bundle with `total: 6`.
For a container not yet created, use the kit's Compose file:

```bash
docker compose -f FHIR-AI-Kit/docker-iris-fhir/docker-compose.yml up -d iris
```

A fresh database then needs initialization as described below. Do not initialize
or reload an already healthy installation merely to restart it.

## Deploy IRIS alongside the web app

The following is a **local/demo deployment**, not an internet-facing production
configuration. It combines the existing app image with IRIS on one Compose
network, without starting HAPI.

### 1. Select the durable volume

For the existing installation, verify the project and volume before proceeding:

```bash
docker inspect iris-fhir --format \
  '{{index .Config.Labels "com.docker.compose.project"}}'
docker inspect iris-fhir --format \
  '{{range .Mounts}}{{if eq .Destination "/durable"}}{{.Name}}{{end}}{{end}}'

export IRIS_PROJECT=docker-iris-fhir
export IRIS_DATA_VOLUME=docker-iris-fhir_iris-data
```

Use the actual inspected values if different. Reusing the same project and
service allows Compose to manage the existing container; do not run a second
project competing for the `iris-fhir` name or port 52773.

For a **fresh installation only**, instead use:

```bash
export IRIS_PROJECT=mdt
export IRIS_DATA_VOLUME=mdt-iris-data
docker volume create "$IRIS_DATA_VOLUME"
```

The example below makes the volume external so its identity is explicit and
Compose does not own its deletion.

### 2. Create a combined Compose file

Save this example as `compose.iris-app.yml` in the repository root. This is a
standalone configuration: do not merge it with the root HAPI Compose file.

```yaml
services:
  iris:
    container_name: iris-fhir
    build:
      context: ./FHIR-AI-Kit/docker-iris-fhir
    restart: unless-stopped
    ports:
      - "127.0.0.1:1972:1972"
      - "127.0.0.1:52773:52773"
    environment:
      ISC_DATA_DIRECTORY: /durable
    volumes:
      - iris-data:/durable

  app:
    build:
      context: .
    restart: unless-stopped
    ports:
      - "127.0.0.1:8000:8000"
    environment:
      FHIR_BASE_URL: http://iris:52773/fhir/r4
      FHIR_USER: SuperUser
      FHIR_PASSWORD: SYS
      APP_PASSWORD: ${APP_PASSWORD:?Set APP_PASSWORD before starting the app}
    volumes:
      - records:/app/data/records

volumes:
  iris-data:
    external: true
    name: ${IRIS_DATA_VOLUME:?Set IRIS_DATA_VOLUME}
  records:
```

Compose gives both services a shared network and DNS. Inside `app`,
`localhost` means the app container, **not IRIS**; use `http://iris:52773/fhir/r4`.
On the host, continue using `http://localhost:52773/fhir/r4`.

This example omits the kit's development bind mount: its files are already copied
into the IRIS image. Host ports are bound to loopback rather than every network
interface. Starting `iris` may recreate the existing container to apply these
settings, causing a brief interruption; the selected durable volume is retained.

### 3. Build and start IRIS

Ensure `FHIR-AI-Kit/` and the organisers' `Dataset/` are present locally. The app
image copies `Dataset/` during its build; it cannot build without it.

```bash
export APP_PASSWORD='replace-with-a-local-demo-password'

docker compose -p "$IRIS_PROJECT" -f compose.iris-app.yml config --quiet
docker compose -p "$IRIS_PROJECT" -f compose.iris-app.yml up -d --build iris

docker exec iris-fhir iris session IRIS -U %SYS 'write "ready",!'
```

If the last command fails while IRIS is still starting, inspect
`docker logs --tail 100 iris-fhir`, wait, and retry. Do not continue with
initialization until the native session succeeds.

### 4. Initialize only a fresh database

**Skip this step when reusing the initialized volume.** From the repository
root, create only the FHIR endpoint, without the kit's sample-data importer:

```bash
(
  cd FHIR-AI-Kit/docker-iris-fhir
  uv run --with intersystems-irispython python -c \
    'from fhir_server_setup_native import FHIRServerSetup; FHIRServerSetup("FHIRSERVER", "/fhir/r4").create_fhir_server()'
)
```

The setup helper uses host ports 1972 and 52773 and its built-in development
credentials. `create_fhir_server()` skips an existing endpoint by default;
do not enable its destructive `overwrite` option.

Verify the endpoint, then load the organisers' dataset only if needed:

```bash
curl --fail --show-error --retry 30 --retry-delay 2 --retry-all-errors \
  --connect-timeout 5 --max-time 15 \
  -u 'SuperUser:SYS' \
  http://localhost:52773/fhir/r4/metadata

(
  cd backend
  FHIR_BASE_URL=http://localhost:52773/fhir/r4 \
    FHIR_USER=SuperUser FHIR_PASSWORD=SYS \
    uv run mdt-load-fhir
)
```

### 5. Start and verify the web app

Start the app only after the authenticated FHIR checks succeed. Container start
order alone does not establish FHIR readiness.

```bash
docker compose -p "$IRIS_PROJECT" -f compose.iris-app.yml up -d --build app
docker compose -p "$IRIS_PROJECT" -f compose.iris-app.yml ps

curl --fail --show-error \
  -u 'SuperUser:SYS' \
  'http://localhost:52773/fhir/r4/Patient?_summary=count'

curl --fail --show-error http://localhost:8000/api/health

curl --fail --show-error \
  -u "demo:$APP_PASSWORD" http://localhost:8000/api/patients
```

Expected results:

- IRIS patient count: `total: 6` for the organisers' unmodified dataset.
- App health: `{"status":"ok"}`. This checks FastAPI only, **not IRIS**.
- App patients: a FHIR patient Bundle returned through the backend, confirming
  app-to-IRIS networking and credentials.

Open `http://localhost:8000` and sign in with any username and `APP_PASSWORD`.
The app uses separate FHIR credentials internally.

The `records` volume persists saved MDT records. This minimal deployment does not
mount generated AI briefings from the host's `data/ai_cases/`, nor configure LLM
credentials. Those are separate from serving the FHIR dataset; see
[architecture.md](architecture.md) for the agent workflow.

## Troubleshooting and lifecycle

```bash
docker logs --tail 100 iris-fhir
docker compose -p "$IRIS_PROJECT" -f compose.iris-app.yml logs --tail 100 app
docker inspect iris-fhir --format '{{json .State}}'
```

- **Connection refused:** check Docker Engine, container state, published ports,
  and whether IRIS has finished starting.
- **404 at `/`:** use the Portal or FHIR paths listed above.
- **404 at `/fhir/r4/metadata`:** check endpoint initialization and selected volume.
- **401 on patients:** check FHIR credentials; metadata alone is not sufficient.
- **App works but shows no live patients:** verify `/api/patients`, the app's
  `FHIR_BASE_URL`, and the selected database volume. Some case views can fall back
  to dataset files when FHIR is unreachable, so a working UI is not proof.
- **Container-name/port conflict:** use the existing Compose project; do not
  launch an unrelated IRIS stack alongside it on the same ports.

For a planned stop/start, retain the same Compose project and exported variables:

```bash
docker compose -p "$IRIS_PROJECT" -f compose.iris-app.yml stop
docker compose -p "$IRIS_PROJECT" -f compose.iris-app.yml start
```

`unless-stopped` requires the Docker engine to be running and does not undo an
explicit stop. Restarting containers retains volumes. Do not delete
`IRIS_DATA_VOLUME` or use volume-removal commands as a troubleshooting shortcut.
Back up IRIS using its supported database backup procedures before upgrades;
the source dataset does not preserve all subsequent server changes.

## Before deploying beyond localhost

- Replace the moving `latest-cd` base image with a tested version/digest and
  confirm the IRIS edition's license, capacity limits, and supported deployment.
- Replace the demo superuser/password with dedicated least-privilege accounts.
  The current Dockerfile and setup helper contain development defaults; changing
  only the app's environment does **not** change the IRIS account password.
- Manage credentials outside version control; update the provisioning process
  rather than exposing its default credentials publicly.
- Terminate HTTPS at a reverse proxy, expose only the web app, and keep native
  port 1972, the Portal, and the FHIR service private. HTTP Basic auth alone
  provides no transport encryption.
- Add authenticated readiness monitoring, tested database backups/restores,
  access auditing, and appropriate application authentication/authorization.
  The demo's single shared app password is not clinical-user identity.
- Keep application images private: they include the local dataset. Keep real
  patient data out of this demo deployment.
