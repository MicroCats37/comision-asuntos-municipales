# ── Seed All ──────────────────────────────────────────────────────────────────
# Orden correcto de comandos de seed para CAM liquidaciones.
# Ejecutar desde la raiz del proyecto con el venv activado.
#
# Uso:
#   .\scripts\seed.ps1                    # seed completo (admin + tarifas)
#   .\scripts\seed.ps1 -OnlyAdmin         # solo seed_real_all
#   .\scripts\seed.ps1 -OnlyTarifas       # solo seed_tarifas_all
#   .\scripts\seed.ps1 -SkipEdificacion   # sin tarifas de edificacion
# ────────────────────────────────────────────────────────────────────────────────

param(
    [switch]$OnlyAdmin,
    [switch]$OnlyTarifas,
    [switch]$SkipEdificacion,
    [switch]$SkipM2,
    [switch]$SkipInspeccion
)

$ErrorActionPreference = "Stop"
$backendDir = Join-Path $PSScriptRoot "..\backend"

Push-Location $backendDir

try {
    if (-not $OnlyTarifas) {
        Write-Host "`n[1/3] Limpiando duplicados de especialidades..." -ForegroundColor Cyan
        python manage.py cleanup_especialidad_duplicates
        if ($LASTEXITCODE -ne 0) { throw "cleanup_especialidad_duplicates fallo" }

        Write-Host "`n[2/3] Cargando datos reales (admin)... " -ForegroundColor Cyan
        python manage.py seed_real_all
        if ($LASTEXITCODE -ne 0) { throw "seed_real_all fallo" }
    }

    if (-not $OnlyAdmin) {
        Write-Host "`n[3/3] Sembrando tarifas de liquidacion..." -ForegroundColor Cyan
        $tarifasArgs = @()
        if ($SkipEdificacion) { $tarifasArgs += "--skip-edificacion" }
        if ($SkipM2) { $tarifasArgs += "--skip-m2" }
        if ($SkipInspeccion) { $tarifasArgs += "--skip-inspeccion" }

        python manage.py seed_tarifas_all @tarifasArgs
        if ($LASTEXITCODE -ne 0) { throw "seed_tarifas_all fallo" }
    }

    Write-Host "`nSeed completado." -ForegroundColor Green
} finally {
    Pop-Location
}
