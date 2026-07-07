# build-docker.ps1
$env:PATH = $env:PATH + ";C:\Program Files\Docker\Docker\resources\bin"
Set-Location "D:\الشريعة - ابي\new22 - Copy - Copy"

# بناء Backend
& "C:\Program Files\Docker\Docker\resources\bin\docker.exe" compose build backend 2>&1 | Out-File "build-backend-ps.log" -Append
"BACKEND_BUILD_DONE" | Out-File "build-status.txt" -Append

# بناء Frontend
& "C:\Program Files\Docker\Docker\resources\bin\docker.exe" compose build frontend 2>&1 | Out-File "build-frontend-ps.log" -Append
"FRONTEND_BUILD_DONE" | Out-File "build-status.txt" -Append
