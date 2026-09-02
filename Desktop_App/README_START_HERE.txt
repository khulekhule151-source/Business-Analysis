BUSINESS ANALYSIS — VERSION 2.0.0
Published by Khùlè Khùlè III

WHAT THIS VERSION FIXES
- Administrator Login is restored and is the first screen after setup.
- Secure first-time administrator creation.
- Password and recovery code are stored as salted PBKDF2 hashes in local SQLite.
- Password recovery is available from the login screen.
- Owner Control Center is available only after administrator login.
- Owner Control Center shows local business metrics and attempts to load remote owner metrics from Render.
- Professional dashboard with revenue/profit charts, filters and business insights.
- Data cleaning / Data Quality Report and duplicate removal.
- Excel, PDF and clean CSV export.
- Live Render API analysis and health status.
- Product names are preserved; valid product values are not replaced with Unknown.
- Privacy-minimal telemetry sends only installation ID, event name, app version, OS and timestamp.
- No customer/transaction/business data is sent as telemetry.

FIRST RUN
1. Run install_requirements.bat once.
2. Run run_business_analysis.bat.
3. Create the administrator username, password and recovery code.
4. Log in.
5. Use Owner Control Center from the left sidebar.

BUILD WINDOWS EXE
1. Run build_exe.bat on Windows.
2. The EXE will be created at dist\\BUSINESS_ANALYSIS.exe.
3. Install Inno Setup on Windows and compile BUSINESS_ANALYSIS.iss to create the installer.

IMPORTANT
- The desktop application works with its local SQLite database.
- The Render API is used for analysis and owner/telemetry services when available.
- Do not put secrets or API passwords inside this desktop package.
- The previous BUSINESS_ANALYSIS_v2_PROFESSIONAL.zip is superseded by this package.
