@echo off
cd /d C:\Users\SF66405\Code\Python\cDAQ

echo --- Changement de répertoire vers le dépôt Git ---

:: Vérifie que Git est installé
where git >nul 2>&1
if errorlevel 1 (
    echo Git n'est pas installé ou non trouvé dans le PATH.
    pause
    exit /b
)

:: Ajout des fichiers modifiés
git add .

:: Commit avec message automatique (tu peux le personnaliser)
git commit -m "Mise à jour automatique via script .bat"

:: Push vers le dépôt distant
git push origin main

echo --- Dépôt mis à jour avec succès ---
pause
