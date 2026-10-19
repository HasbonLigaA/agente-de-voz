# URL publica HTTPS (Cloudflare Tunnel) para probar desde el celular con microfono.
# Requiere: winget install Cloudflare.cloudflared  (o cloudflared en PATH)
# Uso: abre DOS terminales:
#   1) scripts/serve_mobile.ps1
#   2) scripts/tunnel_cloudflare.ps1

$Port = if ($env:PORT) { $env:PORT } else { "8767" }

if (-not (Get-Command cloudflared -ErrorAction SilentlyContinue)) {
    Write-Host "Instala cloudflared: winget install Cloudflare.cloudflared"
    Write-Host "Luego cierra y abre la terminal."
    exit 1
}

Write-Host "Creando tunel HTTPS hacia http://127.0.0.1:$Port ..."
Write-Host "Copia la URL https://....trycloudflare.com en el navegador del celular."
Write-Host ""

cloudflared tunnel --url "http://127.0.0.1:$Port"
