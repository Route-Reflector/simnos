Running SIMNOS in a container enables numerous integrations use cases.

## Running with Docker

Pre-built SIMNOS docker container published to
[DockerHUB repository](https://hub.docker.com/r/fakenos/fakenos)


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
ssh 10.100.0.2 -l user -p 6001                             # (4)
```

1. Clone SIMNOS repository from GitHub
2. Navigate to simnos docker directory
3. Build and start container in detached (`-d`) mode
4. Initiate SSH connection to SIMNOS router

`simnos` container uses  `10.100.0.2` IP address by default as specified in
`docker-compose.yaml` file.

`docker/` folder contains `inventory.yaml` file, with inventory
that is used to start SIMNOS inside a container:

```yaml
default:
  username: "user"
  password: "user"
  port: [10000, 60000]
  server:
    plugin: "ParamikoSshServer"
    configuration:
      address: "0.0.0.0"
      timeout: 1
  shell: {plugin: "CMDShell", configuration: {}}
  nos: {plugin: "cisco_ios", configuration: {}}

hosts:
  router: {count: 10, port: [6001, 7000]}
```

Adjust inventory settings before running the container or update inventory content
and restart `simnos` container to apply changes - `docker restart simnos`

Inventory file bound to the `simnos` container as a `volume` in docker-compose file,
as a result any changes to `inventory.yaml` file visible to `simnos` process
running inside the container.
