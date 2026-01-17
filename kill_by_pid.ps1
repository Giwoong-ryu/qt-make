$pids = @(23432, 134556, 136212, 37748, 148692)
foreach ($pid in $pids) {
    try {
        Stop-Process -Id $pid -Force -ErrorAction Stop
        Write-Host "Killed PID: $pid"
    } catch {
        Write-Host "Could not kill PID: $pid"
    }
}
Start-Sleep -Seconds 3
