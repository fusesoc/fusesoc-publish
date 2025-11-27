# fusesoc-publish

## Overview

fusesoc-publish is a tool for publishing [FuseSoC](https://github.com/olofk/fusesoc) core description files to a [FuseSoC Package Database](https://github.com/fusesoc/fusesoc-webserver).

## Getting Started

### Installation

```bash
git clone https://github.com/fusesoc/fusesoc-publish
pip install -e fusesoc-publish
```

### Quickstart guide

#### Create a test server

fusesoc-publish contains some example cores that can be used to test the publishing feature. In order to do so, we also need a server where they can be published. For testing purposes, the simplest way is to set up a private server. The process is described in further detail in the [FuseSoC Package Database](https://github.com/fusesoc/fusesoc-webserver) documentation but the commands below should be sufficient to get started.

```bash
# Clone FuseSoC Package Database repo
git clone https://github.com/fusesoc/fusesoc-webserver
cd fusesoc-webserver

# Copy and extend example environment file
cp .env.example .env
echo DJANGO_DEBUG=True >> .env
echo DJANGO_SECRET_KEY=ignoreme >> .env

# Build webserver container
docker compose up --build
```

The server should now be running at http://localhost:8000

#### Set up FuseSoC

fusesoc-publish uses the same library parsing and configuration file as fusesoc, so we begin by registering the directory containing the example cores as a FuseSoC library.

```bash
# Create an empty workspace directory anywhere in your filesystem
mkdir workspace && cd workspace

# Register the directory of the fusesoc-publish example cores as a library
fusesoc library add <path to>/fusesoc-publish/examples

# Make sure that the example cores can be found
fusesoc core list
```

#### Publish a core

From the workspace directory it should now be possible to publish any of the cores in the local library. Try publishing the first example core with

```bash
fusesoc-publish basic http://localhost:8000
```

The published core should now be available to look at in the local server. Try also to add the other example cores to see more features like signing and automatic provider guessing.

Have fun!

![NLNet logo](https://nlnet.nl/logo/banner.svg)
[This project](https://nlnet.nl/project/FuseSoC-catalog/) was sponsored by [NLNet Foundation](https://nlnet.nl) through the [NGI0 Commons Fund](https://nlnet.nl/commonsfund/)
