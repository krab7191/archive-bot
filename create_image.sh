#!/bin/bash

docker buildx build . --progress=plain --platform=linux/amd64 --no-cache -t archive-bot:latest