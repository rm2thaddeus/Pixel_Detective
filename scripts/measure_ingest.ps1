$start = Get-Date
$body = '{"directory_path":"C:/Users/aitor/OneDrive/Escritorio/dng test"}'
Write-Host "Posting ingestion job for DNG test directory..."
$job = Invoke-RestMethod -Uri 'http://localhost:8002/api/v1/ingest/' -Method POST -Body $body -ContentType 'application/json'
$id = $job.job_id
Write-Host "Job ID: $id"
Write-Host "Polling status..."
while ((Invoke-RestMethod -Uri "http://localhost:8002/api/v1/ingest/status/$id" -Method GET).status -ne 'completed') {
    Start-Sleep -Seconds 1
}
$duration = (Get-Date) - $start
Write-Host "Total Duration: $($duration.TotalSeconds) seconds" 