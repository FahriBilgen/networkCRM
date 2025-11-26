#requires -Version 5.0
$ErrorActionPreference = "Stop"
$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

& "$ScriptRoot\setup_demo.ps1" @args
