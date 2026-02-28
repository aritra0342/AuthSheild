@echo off
echo.
echo ================================================================
echo    AuthShield AI - Full Demo Simulation
echo ================================================================
echo.
echo [1/5] Simulating Normal Users...
python test_botnet.py --quick --phase 1
echo.
echo [2/5] Simulating Botnet Attack...
python test_botnet.py --quick --phase 2
echo.
echo [3/5] Detecting Clusters...
python test_botnet.py --quick --phase 3
echo.
echo [4/5] Auto-Freezing Suspicious Accounts...
python test_botnet.py --quick --phase 4
echo.
echo [5/5] Checking Freeze Log...
python test_botnet.py --quick --phase 5
echo.
echo ================================================================
echo    Demo Complete! Open http://localhost:8000
echo ================================================================
pause
