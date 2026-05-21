#!/usr/bin/env bash
./embedded_remote_control > server.log 2>&1 & echo $! > server.pid