# build.ps1 - بناء حاويات Docker في الخلفية
$projectDir = "D:\الشريعة - ابي\new22 - Copy - Copy"
Set-Location $projectDir

$docker = "C:\Program Files\Docker\Docker\resources\bin\docker.exe"

# بناء Backend
& $docker compose build backend 2>&1 | Tee-Object -FilePath "build-backend.log" -Append

# بناء Frontend
& $docker compose build frontend 2>&1 | Tee-Object -FilePath "build-frontend.log" -Append

# سجل النهاية
"Build completed at $(Get-Date)" | Out-File "build-done.txt"
