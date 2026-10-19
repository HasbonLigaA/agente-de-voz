# Servidor accesible desde el celular (misma red local).
# Uso: powershell -ExecutionPolicy Bypass -File scripts/serve_mobile.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

$Port = if ($env:PORT) { $env:PORT } else { "8767" }
$Python = Join-Path $Root ".venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    Write-Host "No existe .venv. Crea el entorno e instala requirements.txt primero."
    exit 1
}

# Excluir adaptadores virtuales (VirtualBox, etc.) que confunden la IP del celular.
$skipPrefix = @("192.168.56.", "192.168.122.", "172.16.", "172.17.", "172.18.", "172.19.")
$skipAlias = "Loopback|vEthernet|VirtualBox|VMware|Hyper-V|WSL|Tailscale|TAP|TUN|Npcap"

$ips = Get-NetIPAddress -AddressFamily IPv4 |
    Where-Object {
        $_.IPAddress -notlike "127.*" -and
        $_.IPAddress -notlike "169.254.*" -and
        $_.InterfaceAlias -notmatch $skipAlias
    } |
    ForEach-Object {
        $ok = $true
        foreach ($p in $skipPrefix) {
            if ($_.IPAddress.StartsWith($p)) { $ok = $false; break }
        }
        if ($ok) { [PSCustomObject]@{ IP = $_.IPAddress; Iface = $_.InterfaceAlias } }
    } |
    Sort-Object -Property @{ Expression = { if ($_.Iface -match "Wi-Fi|WLAN") { 0 } else { 1 } } }, IP -Unique

Write-Host ""
Write-Host "=== Agente de voz (red local) ==="
Write-Host "En el PC: http://127.0.0.1:$Port"
Write-Host ""
Write-Host "En el CELULAR prueba UNA de estas URLs (misma red que el PC, no datos moviles):"
if ($ips.Count -eq 0) {
    Write-Host "  (no se detecto IP LAN; revisa Wi-Fi o cable al router)"
} else {
    foreach ($row in $ips) {
        Write-Host "  http://$($row.IP):$Port   [$($row.Iface)]"
    }
}
Write-Host ""
Write-Host "PC por cable (LAN) + celular por Wi-Fi del MISMO router = OK (no hace falta cable en el celular)."
Write-Host "Celular con datos 4G/5G = la IP local NO funciona; usa scripts/tunnel_cloudflare.ps1"
Write-Host ""
Write-Host "Si la pagina queda en 'Comprobando servidor', IP equivocada o firewall."
Write-Host "Firewall: scripts/allow_firewall.ps1 (una vez, como administrador)"
Write-Host "Servidor debe usar --host 0.0.0.0 (este script ya lo hace)."
Write-Host "Ctrl+C para detener."
Write-Host ""

& $Python -m uvicorn backend.main:app --host 0.0.0.0 --port $Port
