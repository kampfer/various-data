#!/usr/bin/env pwsh
<#
.SYNOPSIS
    本地打包并部署调度器到远程 Linux 服务器。

.DESCRIPTION
    依次执行：构建前端并打 zip -> 上传 -> 远程解压 -> 执行 install.sh install -> 健康检查。
    只要修改下方 $Config 中的地址、用户、密码/密钥，然后在 Windows 上运行本脚本即可。

    认证方式二选一：
    1. SSH 密钥（推荐）：KeyPath 填密钥路径，Password 留空。
    2. 密码：填写 Password，脚本改用 PuTTY 的 plink/pscp，并自动接受首次主机指纹。
       密码会出现在本机命令行与进程列表中，不要提交填写后的脚本。

.EXAMPLE
    powershell -NoProfile -ExecutionPolicy Bypass -File .\deploy\deploy_remote.ps1
#>
[CmdletBinding()]
param(
    [string]$HostName = "",
    [string]$User = "",
    [int]$Port = 0,
    [string]$Password  = "",
    [string]$KeyPath = "",
    [string]$RemoteDir = "",

    # 前端没有改动时跳过 npm build
    [switch]$SkipFrontend,

    # 复用本地已有 zip，不重新打包
    [switch]$SkipBuild
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot

# ==================== 配置区：只改这里 ====================
$Config = @{
    HostName  = "192.168.1.10"     # 服务器地址
    User      = "android"          # SSH 用户
    Port      = 2222               # SSH 端口
    Password  = ""                 # 留空则运行时提示输入密码；或改用 KeyPath
    KeyPath   = ""                 # 例如 "$HOME\.ssh\id_ed25519"
    RemoteDir = "/srv"             # 远程安装目录，最终项目在 <RemoteDir>/various-data-scheduler
}
# ========================================================

if (-not $HostName) { $HostName = $Config.HostName }
if (-not $User) { $User = $Config.User }
if ($Port -le 0) { $Port = [int]$Config.Port }
if (-not $Password) { $Password = $Config.Password }
if (-not $KeyPath) { $KeyPath = $Config.KeyPath }
if (-not $RemoteDir) { $RemoteDir = $Config.RemoteDir }

if (-not $HostName) {
    throw "请先填写脚本顶部 `$Config.HostName"
}

$Target = "$User@$HostName"

# 没有预填密码、也没有密钥时，运行时提示输入
if (-not $Password -and -not $KeyPath) {
    $secure = Read-Host "请输入 $Target 的 SSH 密码" -AsSecureString
    $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
    try {
        $Password = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
    }
    finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
    }
    if (-not $Password) {
        throw "密码为空，且未配置 KeyPath"
    }
}

$UsePassword = [bool]$Password

$SshBase = @("-p", "$Port", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=accept-new")
if ($KeyPath) {
    $SshBase += @("-i", $KeyPath)
}

$Plink = $null
$Pscp = $null
if ($UsePassword) {
    $Plink = Get-Command plink -ErrorAction SilentlyContinue
    $Pscp = Get-Command pscp -ErrorAction SilentlyContinue
    if (-not $Plink -or -not $Pscp) {
        throw "密码模式需要 PuTTY 的 plink 和 pscp。请安装 PuTTY 并加入 PATH，或改用 SSH 密钥（Password 留空）。"
    }
    Write-Warning "已启用密码认证：密码会出现在本机命令行与进程列表中。部署完成后建议清空 Password，并避免提交填写后的脚本。"
}

function Invoke-RemoteCapture {
    param([Parameter(Mandatory = $true)][string]$Command)

    if ($UsePassword) {
        & $Plink.Source -ssh -P $Port -pw $Password -batch $Target $Command
    }
    else {
        & ssh @SshBase $Target $Command
    }
}

function Invoke-Remote {
    param(
        [Parameter(Mandatory = $true)][string]$Command,
        [switch]$Interactive
    )

    Write-Host "==> 远程: $Command"
    if ($Interactive) {
        if ($UsePassword) {
            & $Plink.Source -ssh -t -P $Port -pw $Password -batch $Target $Command
        }
        else {
            & ssh -t @SshBase $Target $Command
        }
    }
    else {
        Invoke-RemoteCapture $Command
    }
    if ($LASTEXITCODE -ne 0) {
        throw "远程命令失败（退出码 $LASTEXITCODE）：$Command"
    }
}

function Get-LatestZip {
    $zip = Get-ChildItem (Join-Path $Root "dist/various-data-scheduler-*.zip") -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
    if (-not $zip) {
        throw "dist 下没有部署包，请先执行 python deploy/build_zip.py"
    }
    return $zip
}

Write-Host "==> 检查 SSH 连接: $Target (端口 $Port)"
Invoke-RemoteCapture "echo ok" | Out-Null
if ($LASTEXITCODE -ne 0 -and $UsePassword) {
    Write-Host "==> 首次连接，自动接受主机指纹"
    "y" | & $Plink.Source -ssh -P $Port -pw $Password $Target "echo ok" | Out-Null
}
if ($LASTEXITCODE -ne 0) {
    if ($UsePassword) {
        throw "无法通过密码登录 $Target，请检查地址、端口、用户名与密码"
    }
    throw @"
无法免密登录 $Target。请先配置 SSH 密钥：
  ssh-keygen -t ed25519
  type $HOME\.ssh\id_ed25519.pub | ssh -p $Port $Target "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys"
"@
}

$SudoMode = "none"
if ($User -ne "root") {
    Invoke-RemoteCapture "sudo -n true" | Out-Null
    if ($LASTEXITCODE -eq 0) {
        $SudoMode = "nopasswd"
    }
    else {
        $SudoMode = "interactive"
        Write-Host "==> 该用户没有免密 sudo，安装阶段会提示输入 sudo 密码"
    }
}

if ($SkipBuild) {
    $Zip = Get-LatestZip
    Write-Host "==> 复用已有部署包: $($Zip.Name)"
}
else {
    $Python = Join-Path $Root "src/backend/.venv/Scripts/python.exe"
    if (-not (Test-Path $Python)) {
        $Python = "python"
    }
    $BuildArgs = @((Join-Path $Root "deploy/build_zip.py"))
    if ($SkipFrontend) {
        $BuildArgs += "--skip-frontend"
    }
    Write-Host "==> 本地打包"
    & $Python @BuildArgs
    if ($LASTEXITCODE -ne 0) {
        throw "本地打包失败"
    }
    $Zip = Get-LatestZip
}

$RemoteZip = "/tmp/$($Zip.Name)"
Write-Host "==> 上传 $($Zip.Name) 到 $RemoteZip"
if ($UsePassword) {
    & $Pscp.Source -P $Port -pw $Password $Zip.FullName "${Target}:$RemoteZip"
}
else {
    $ScpArgs = @("-P", "$Port", "-o", "StrictHostKeyChecking=accept-new")
    if ($KeyPath) {
        $ScpArgs += @("-i", $KeyPath)
    }
    & scp @ScpArgs $Zip.FullName "${Target}:$RemoteZip"
}
if ($LASTEXITCODE -ne 0) {
    throw "上传失败"
}

$Setup = "mkdir -p $RemoteDir && unzip -o $RemoteZip -d $RemoteDir && cd $RemoteDir/various-data-scheduler && bash deploy/install.sh install"
switch ($SudoMode) {
    "none" { Invoke-Remote $Setup }
    "nopasswd" { Invoke-Remote "sudo -n bash -c '$Setup'" }
    "interactive" { Invoke-Remote "sudo bash -c '$Setup'" -Interactive }
}
Invoke-Remote "cd '$RemoteDir/various-data-scheduler' && bash deploy/install.sh status"

Write-Host "==> 健康检查"
Invoke-RemoteCapture "curl -fsS --max-time 5 http://127.0.0.1:8787/api/health || echo '健康检查未通过：可能已关闭管理服务或改过端口'"

$RemoteIp = (Invoke-RemoteCapture "hostname -I") -split "\s+" | Where-Object { $_ } | Select-Object -First 1
Write-Host ""
Write-Host "部署完成。管理页面: http://${RemoteIp}:8787"
Write-Host "远程操作: ssh -p $Port $Target"
Write-Host "  cd $RemoteDir/various-data-scheduler && bash deploy/install.sh start|stop|restart|status|logs"
