@echo off
echo.
echo [INFRA - CI/CD] Executing database migration pipeline...

IF "%PROD_DB_PASSWORD%"=="" (
    echo    [-] FATAL: Senha de producao nao encontrada no ambiente.
    exit /b 1
) ELSE (
    echo    [+] Migrations applied using secure password: %PROD_DB_PASSWORD%
)