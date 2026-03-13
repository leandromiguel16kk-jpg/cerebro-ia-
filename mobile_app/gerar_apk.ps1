# Automação de Build do APK - Algo-Risonho AI

# 1. Instalar dependências
Write-Host "Instalando dependências..." -ForegroundColor Cyan
npm install @capacitor/core @capacitor/cli @capacitor/android

# 2. Inicializar Capacitor se necessário
if (!(Test-Path "capacitor.config.ts")) {
    npx cap init AlgoRisonho com.algorisonho.ai --web-dir www
}

# 3. Sincronizar arquivos
Write-Host "Sincronizando arquivos..." -ForegroundColor Cyan
npx cap add android
npx cap sync android

# 4. Abrir no Android Studio
Write-Host "Abrindo Android Studio... Gere o APK em Build > Build APK(s)" -ForegroundColor Green
npx cap open android
