# Local Flowly lifecycle. No queue cleanup, automatic migration, or global kill.
[CmdletBinding()]
param(
  [ValidateSet('start', 'status', 'stop', 'restart')]
  [string]$Action = 'start',
  [ValidateSet('api', 'worker', 'beat')]
  [string[]]$Services = @('api', 'worker', 'beat'),
  [string]$ApiHost,
  [Nullable[int]]$ApiPort,
  [Nullable[int]]$Workers,
  [ValidateRange(1, 600)]
  [int]$StartupTimeout = 30,
  [ValidateRange(1, 600)]
  [int]$StopTimeout = 15,
  [switch]$Json
)

$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path -LiteralPath (Split-Path -Parent $PSScriptRoot)).Path
$VenvPython = Join-Path $Root '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $VenvPython -PathType Leaf)) {
  Write-Error "缺少项目虚拟环境：$VenvPython。请按部署指南安装依赖；未启动或停止任何服务。"
  exit 1
}
$Cli = Join-Path $PSScriptRoot 'local_service_cli.py'
$CliArguments = @($Cli, '--workspace', $Root, '--action', $Action, '--startup-timeout', $StartupTimeout, '--stop-timeout', $StopTimeout)
if ($PSBoundParameters.ContainsKey('ApiHost')) { $CliArguments += @('--api-host', $ApiHost) }
if ($PSBoundParameters.ContainsKey('ApiPort')) { $CliArguments += @('--api-port', $ApiPort) }
if ($PSBoundParameters.ContainsKey('Workers')) { $CliArguments += @('--workers', $Workers) }
if ($Json) { $CliArguments += '--json' }
$CliArguments += '--services'
$CliArguments += $Services
& $VenvPython @CliArguments
exit $LASTEXITCODE
