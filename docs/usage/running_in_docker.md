# Running in Docker

Running SIMNOS in a container enables numerous integration use cases.

## Running with Docker

Pre-built SIMNOS docker container published to
[GitHub Container Registry](https://github.com/Route-Reflector/simnos/pkgs/container/simnos).

```{ .bash .annotate }
docker pull ghcr.io/route-reflector/simnos:latest   # (1)
docker run -d -p 12723:6001 -p 12724:6002 \
  --name simnos ghcr.io/route-reflector/simnos       # (2)
ssh localhost -l user -p 12723                        # (3)
```

1. Pull the latest SIMNOS image from GHCR
2. Run the container in detached mode with port mappings
3. Initiate SSH connection to SIMNOS router via mapped port

To use a custom inventory, mount it as a volume:

```bash
docker run -d -p 12723:6001 -p 12724:6002 \
  -v /path/to/inventory.yaml:/app/docker/inventory.yaml \
  --name simnos ghcr.io/route-reflector/simnos
```

!!! warning
    The default inventory binds to `0.0.0.0` with credentials `user:user`.
    This is intended for local testing only. For shared or production
    environments, use a custom inventory with appropriate credentials.

## Build and Run with Docker-Compose

SIMNOS GitHub repository contains `docker-compose` and `Docker` files to build
and start SIMNOS in a container. To use it, providing that you already installed
[Docker](https://docs.docker.com/engine/install/),
[Docker-Compose](https://docs.docker.com/compose/install/) and
[GIT](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git) on the system:

```{ .bash .annotate }
git clone https://github.com/Route-Reflector/simnos.git   # (1)
cd simnos/docker/                                          # (2)
docker-compose up -d                                       # (3)
ssh localhost -l user -p 12723                              # (4)
```

1. Clone SIMNOS repository from GitHub
2. Navigate to simnos docker directory
3. Build and start container in detached (`-d`) mode
4. Initiate SSH connection to SIMNOS router via mapped port

The `docker-compose.yaml` maps container ports to host ports
(e.g. `12723:6001`, `12724:6002`), so connect to the mapped ports on `localhost`.

`docker/` folder contains `inventory.yaml` file, with inventory
that is used to start SIMNOS inside a container:

```yaml
default:
  server:
    plugin: "ParamikoSshServer"
    configuration:
      address: "0.0.0.0"
      timeout: 1

hosts:
  router:
    username: user
    password: user
    port: [6001, 6002]
    replicas: 2
    platform: cisco_ios
```

Adjust inventory settings before running the container or update inventory content
and restart `simnos` container to apply changes - `docker restart simnos`
