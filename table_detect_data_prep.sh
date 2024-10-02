#!/bin/bash
printf -v var "%s," "$@"
gradle tableDetectDataPrep -Ppargs="$var"
