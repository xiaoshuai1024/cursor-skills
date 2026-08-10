# 应用窗口截图（只截应用本身，不截全屏）
# 用法（从 Git Bash / cmd 均可）：
#   powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/screenshot-app.ps1 \
#     -ProcessName "ChatGPT" -WindowTitle "ChatGPT" -Output static/images/<dir>/01.png
#
# 说明：
# - 按进程名 + 窗口标题模糊匹配唯一窗口，先把窗口置前再截 GetWindowRect 区域
# - Windows 上必须用 .ps1 文件跑（-File），内联 -Command 里 $_ 会被 bash 吃掉
# - 中文输出路径：PowerShell 5.1 按 ANSI 读 .ps1，脚本内避免中文硬编码；
#   终端打印中文前确认编码，必要时 -Output 传绝对路径
# - DPI 缩放：SetProcessDPIAware() 后 GetWindowRect 返回物理像素，CopyFromScreen 一致，无需换算
param(
  [Parameter(Mandatory=$true)][string]$ProcessName,
  [string]$WindowTitle = "",
  [Parameter(Mandatory=$true)][string]$Output
)
Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
public struct RECT { public int Left, Top, Right, Bottom; }
public class W32 {
  [DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr hWnd, out RECT rect);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
}
"@
[W32]::SetProcessDPIAware() | Out-Null

$outDir = Split-Path $Output -Parent
if ($outDir -and -not (Test-Path $outDir)) { New-Item -ItemType Directory -Force -Path $outDir | Out-Null }

$win = Get-Process -ErrorAction SilentlyContinue |
  Where-Object { $_.Name -like "*$ProcessName*" -and $_.MainWindowHandle -ne 0 -and $_.MainWindowTitle -like "*$WindowTitle*" } |
  Select-Object -First 1
if (-not $win) { Write-Error "no window for $ProcessName / $WindowTitle"; exit 1 }

$rect = New-Object RECT
[W32]::GetWindowRect($win.MainWindowHandle, [ref]$rect) | Out-Null
[W32]::ShowWindow($win.MainWindowHandle, 9) | Out-Null   # SW_RESTORE: 最小化窗口先还原
[W32]::SetForegroundWindow($win.MainWindowHandle) | Out-Null
Start-Sleep -Milliseconds 800

Add-Type -AssemblyName System.Drawing
$w = $rect.Right - $rect.Left
$h = $rect.Bottom - $rect.Top
if ($w -le 0 -or $h -le 0) { Write-Error "bad rect $w x $h"; exit 1 }

$bmp = New-Object System.Drawing.Bitmap($w, $h)
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.CopyFromScreen($rect.Left, $rect.Top, 0, 0, (New-Object System.Drawing.Size($w, $h)))
$bmp.Save($Output, [System.Drawing.Imaging.ImageFormat]::Png)
Write-Output "saved $Output ${w}x${h}"
