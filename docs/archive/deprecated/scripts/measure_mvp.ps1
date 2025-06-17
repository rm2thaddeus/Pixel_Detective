$start = Get-Date
$folder = 'C:/Users/aitor/OneDrive/Escritorio/dng test'
Write-Host "Running MVP CLI for test folder: $folder"
# Run MVP CLI and capture output
python scripts/mvp_app.py --folder $folder --batch-size 16 --max-workers 4 --save-summary
$duration = (Get-Date) - $start
Write-Host "Total Duration: $($duration.TotalSeconds) seconds" 