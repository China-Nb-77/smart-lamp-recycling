@echo off
REM Build a single-file exe that bundles the two jars and the launcher using PyInstaller.
REM Run this from repository root (c:\Users\LEGION\Desktop\灯泡) in an activated Python environment.

pip install --upgrade pyinstaller

REM Adjust paths if your jars are in different locations.

REM Paths to jars (adjust if needed)
SET JAR1=wechat_payment_fix\pay-demo\target\pay-demo-patch-0.0.1-SNAPSHOT.jar
SET JAR2=fulfillment - 副本\target\fulfillment-1.0.0.jar

REM Build with PyInstaller. The launcher imports image_quote_system so the package
REM is included automatically. Ensure you run this from repository root.
pyinstaller --noconfirm --onefile --name combined_services ^
  --add-data "%JAR1%;." --add-data "%JAR2%;." ^
  packager\launcher.py

echo Build finished. See the exe in the dist\ folder.
pause
