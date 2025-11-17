@echo off
set BROKER=localhost
set PORT=1883
set TOPIC=improve/measure
set TAG=main-bus
py -m ingestor_mqtt --broker %BROKER% --port %PORT% --topic %TOPIC% --tag %TAG%
