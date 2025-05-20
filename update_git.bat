@echo off
:: Script de mise a jour automatique du depot GitHub

echo ----------------------------------------
echo [1/5] Changement de repertoire vers le depot Git...
cd c:\user\SF66405\Code\Python\cDAQ
if errorlevel 1 (
    echo [ERREUR] Le chemin d'acces specifie est introuvable.
    timeout /t 5
    exit /b 1
)

:: Verifie que Git est disponible
where git >nul 2>&1
if errorlevel 1 (
    echo [ERREUR] Git n'est pas installe ou non detecte dans le PATH.
    timeout /t 5
    exit /b 1
)

:: Vérifie si Thermocouple_Data est un sous-module
git submodule status Thermocouple_Data >nul 2>&1
if not errorlevel 1 (
    echo [INFO] 'Thermocouple_Data' est detecte comme un sous-module Git.
    echo [ATTENTION] Les modifications dans les sous-modules doivent etre committees et poussees separement.
)

echo [2/5] Ajout des fichiers modifies (y compris les fichiers non suivis)...
git add --all
if errorlevel 1 (
    echo [ERREUR] Probleme lors de l'ajout des fichiers.
    timeout /t 5
    exit /b 1
)

echo [3/5] Pull des dernieres modifications...
git pull origin main
if errorlevel 1 (
    echo [ERREUR] echec du pull depuis GitHub.
    timeout /t 5
    exit /b 1
)

echo [4/5] Commit des modifications...
git commit -m "Mise a jour automatique via script .bat"
:: Pas d'erreur si aucun changement a committer

echo [5/5] Push vers le depot distant...
git push origin main
if errorlevel 1 (
    echo [ERREUR] echec de l'envoi vers GitHub.
    timeout /t 5
    exit /b 1
)

echo ----------------------------------------
echo [SUCCeS] Depot mis a jour avec succes !
timeout /t 3
exit /b 0
