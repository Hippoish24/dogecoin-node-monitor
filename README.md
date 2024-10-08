# Node Monitor

Node monitor for one or many nodes.  Includes the client script, Prometheus server, Grafana, and frontend webpage.

## Prometheus Client

On port 8334.  Starts a web server with metrics that can be scraped by the Prometheus server.
Metrics are gathered by running `dogecoin-cli` commands every 30 seconds.  Both the port and
interval are configurable.

Installation:
```sh
apt install -y python3-pip
pip3 install -r requirements.txt
```

Running as a background task:
```sh
nohup python3 monitor.py &
```

To kill the task later:
```sh
ps ax | grep monitor.py
kill PID
```

## Prometheus Server

On port 9090.  Use [prometheus.yml](prometheus-server/prometheus.yml) to configure client
connections (update the `static_configs` section with the addresses of your nodes).  Can
also configure the scrape interval (currently 15 seconds).

## Grafana

On port 3030.  Configuration is stored in [grafana.ini](grafana/grafana.ini). Automatically adds
`http://prometheus:9090` as a data source - if deploying using Docker (see below), this will work
without any additional configuration.  Also automatically adds `dogecoin.json` as the home
dashboard, which will connect to the Prometheus data source.

This configuration allows anonymous viewing access and admin authentication.  The admin password
is stored in [grafana.ini](grafana/grafana.ini) - change it before deploying your server!

There is also commented-out configuration in the `[server]` block if you're serving Grafana as a
subpage (will require additional reverse proxy configuration that is beyond the scope of this
project).

Dogecoin dashboard is inspired by this [Bitcoin Node dashboard](https://grafana.com/grafana/dashboards/11274).


# Deploying

Deploys using Docker Compose or Swarm.  The volumes in the [docker-compose.yml](docker-compose.yml)
file are relative to the current directory.

Run using:
* (Docker Compose) `docker compose up -d`
* (Docker Swarm) `docker stack deploy -c docker-compose.yml node_monitor`
  * You may need to first init the server as a Docker Swarm manager with `docker swarm init --advertise-addr <IP address>`.
