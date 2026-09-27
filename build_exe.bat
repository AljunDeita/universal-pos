@echo off
REM build_exe.bat
REM Run this from inside your project's virtual environment (or after
REM activating it) to produce the standalone dist\UniversalPOS folder.
REM Double-click this file, or run it from the PyCharm terminal.

echo ============================================
echo  Building Universal POS standalone EXE...
echo ============================================

pyinstaller UniversalPOS.spec --noconfirm --clean

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo BUILD FAILED. Scroll up to see the error above.
    pause
    exit /b 1
)

echo.
echo ============================================
echo  Build complete! Output is in: dist\UniversalPOS
echo  Test it by double-clicking dist\UniversalPOS\UniversalPOS.exe
echo  Next: open installer.iss in Inno Setup and click Compile.
echo ============================================
pause
