@echo off
set IP=192.168.1.50
set PORT=502
set UNIT=1
set REGV=0
set REGI=1
set REGPF=2
set REGTHD=3
set SCALEV=0.1
set SCALEI=0.1
set SCALEPF=0.001
set SCALETHD=0.1
set TAG=main-bus
set PERIOD=1.0
py -m ingestor_modbus --ip %IP% --port %PORT% --unit %UNIT% --regV %REGV% --regI %REGI% --regPF %REGPF% --regTHD %REGTHD% --scaleV %SCALEV% --scaleI %SCALEI% --scalePF %SCALEPF% --scaleTHD %SCALETHD% --tag %TAG% --period %PERIOD%
