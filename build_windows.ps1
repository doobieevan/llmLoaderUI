$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw 'Python was not found. Install Python 3.10+ and ensure python.exe is on PATH.'
}

$vswhere = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio\Installer\vswhere.exe'
if (Test-Path $vswhere) {
    $vsPath = & $vswhere -latest -products '*' -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
    if ($vsPath) {
        $devShell = Join-Path $vsPath 'Common7\Tools\Launch-VsDevShell.ps1'
        if (Test-Path $devShell) {
            . $devShell -Arch amd64 -HostArch amd64
        }
    }
}
if (-not (Get-Command cl.exe -ErrorAction SilentlyContinue) -or -not (Get-Command nmake.exe -ErrorAction SilentlyContinue)) {
    throw 'MSVC C++ Build Tools (including the x64/x86 C++ workload and NMake) were not found. Modify the Visual Studio installation to add the Desktop development with C++ workload, then open a new terminal.'
}

python -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw 'pip upgrade failed.' }
$env:CMAKE_GENERATOR = 'NMake Makefiles'
python -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Application dependency installation failed.' }
python -m pip install pyinstaller
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller installation failed.' }

python build.py --onefile
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller build failed.' }

Write-Host "Build output created under: $PSScriptRoot\dist"
