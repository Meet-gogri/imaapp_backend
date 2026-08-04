@echo off
echo ==========================================
echo Syncing Backend with GitHub...
echo ==========================================
git add .
git commit -m "Auto-update backend: %date% %time%"
git push origin main
echo Done!
pause