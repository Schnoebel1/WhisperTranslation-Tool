$desktopPath = [Environment]::GetFolderPath('Desktop')
$files = Get-ChildItem -Path $desktopPath -Filter "*Whisper*.lnk"
if ($files.Count -gt 0) {
    $shortcutPath = $files[0].FullName
} else {
    $shortcutPath = Join-Path $desktopPath "Whisper Translation Tool.lnk"
}
$WshShell = New-Object -comObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut($shortcutPath)
$pythonCmd = Get-Command pythonw.exe -ErrorAction SilentlyContinue
if ($pythonCmd) {
    $Shortcut.TargetPath = $pythonCmd.Source
} else {
    $Shortcut.TargetPath = "pythonw.exe"
}
$Shortcut.Arguments = '""C:\Users\Nicolas Aldebert\Desktop\SoftwareEntwicklungen\WhisperTranslation Tool\app.py""'
$Shortcut.IconLocation = "C:\Users\Nicolas Aldebert\Desktop\SoftwareEntwicklungen\WhisperTranslation Tool\icon.ico, 0"
$Shortcut.WorkingDirectory = "C:\Users\Nicolas Aldebert\Desktop\SoftwareEntwicklungen\WhisperTranslation Tool"
$Shortcut.Save()
Write-Host "Shortcut created/updated at $shortcutPath"
