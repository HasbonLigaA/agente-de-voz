# Permite entrar al puerto del agente desde otros equipos en la red (ej. celular).
# Ejecutar PowerShell COMO ADMINISTRADOR:
#   powershell -ExecutionPolicy Bypass -File scripts/allow_firewall.ps1

$Port = if ($env:PORT) { [int]$env:PORT } else { 8767 }

$ruleName = "Agente de voz (puerto $Port)"

$existing = Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "La regla '$ruleName' ya existe."
    exit 0
}

New-NetFirewallRule -DisplayName $ruleName `
    -Direction Inbound `
    -Action Allow `
    -Protocol TCP `
    -LocalPort $Port `
    -Profile Private `
    -Description "FastAPI uvicorn para probar agente desde el celular en LAN"

Write-Host "Regla creada para red Privada, puerto TCP $Port."
