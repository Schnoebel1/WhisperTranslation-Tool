$desktopPath = [Environment]::GetFolderPath('Desktop')
$files = Get-ChildItem -Path $desktopPath -Filter "*Whisper*.lnk"
if ($files.Count -gt 0) {
    $shortcutPath = $files[0].FullName
} else {
    $shortcutPath = Join-Path $desktopPath "Whisper Translation Tool.lnk"
}
$WshShell = New-Object -comObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut($shortcutPath)
$scriptDir = $PSScriptRoot
if ([string]::IsNullOrEmpty($scriptDir)) {
    $scriptDir = (Get-Location).Path
}

$Shortcut.TargetPath = Join-Path $scriptDir "venv\Scripts\pythonw.exe"
$appPath = Join-Path $scriptDir "app.py"
$Shortcut.Arguments = "`"$appPath`""
$iconPath = Join-Path $scriptDir "icon.ico"
$Shortcut.IconLocation = "$iconPath, 0"
$Shortcut.WorkingDirectory = $scriptDir
$Shortcut.Save()
Write-Host "Shortcut created/updated at $shortcutPath"
