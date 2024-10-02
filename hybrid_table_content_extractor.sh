#!/bin/bash
printf -v var "%s," "$@"
gradle hybridTableContentExtractor -Ppargs="$var"
