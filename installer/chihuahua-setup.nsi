!addplugindir "plugins"
!include "plugins\EnvVarUpdate.nsh"
!include "plugins\Slice.nsh"
!include "MUI2.nsh"
!include "x64.nsh"


!define VER_MAJOR			0
!define VER_MINOR			1
!define VER_PATCH			2
!define VERSION     		"${VER_MAJOR}.${VER_MINOR}.${VER_PATCH}"
!define REGKEY      		"Software\ChiHuaHua"
!define UNINSTALL_REGKEY	"Software\Microsoft\Windows\CurrentVersion\Uninstall\ChiHuaHua"

!define PYTHON_MAJ			"3.3"
!define PYTHON_VER			"3.3.3"
!define CPPCHECK_VER		"1.64"
!define NSIS_VER			"3.0a2"
!define CODEBLOCKS_VER		"13.12"
!define WAF_VER				"1.7.15"

!define CPPCHECK_PKG		"cppcheck-${CPPCHECK_VER}-x86-Setup.msi"
!define MINGW_PKG			"mingw-get-setup.exe"
!define NSIS_PKG			"nsis-${NSIS_VER}-setup.exe"
!define CODEBLOCKS_PKG		"codeblocks-${CODEBLOCKS_VER}-setup.exe"

!ifdef RunningX64
!define PYTHON_PKG			"python-${PYTHON_VER}.amd64.msi"
!define WAF_PKG				"waf-${WAF_VER}-win64-setup.exe"
!else
!define PYTHON_PKG			"python-${PYTHON_VER}.msi"
!define WAF_PKG				"waf-${WAF_VER}-win32-setup.exe"
!endif


Name                    	"ChiHuaHua ${VERSION}"
!ifdef RunningX64
OutFile                 	"chihuahua-win64-setup.exe"
!else
OutFile                 	"chihuahua-win32-setup.exe"
!endif
InstallDir              	"$PROGRAMFILES\chihuahua"
InstallDirRegKey        	HKCU "${REGKEY}" ""
RequestExecutionLevel   	admin
AutoCloseWindow         	false
ShowInstDetails         	show
ShowUnInstDetails       	show
CRCCheck                	On

!define MUI_ABORTWARNING
!define MUI_STARTMENUPAGE_REGISTRY_ROOT         HKCU
!define MUI_STARTMENUPAGE_REGISTRY_KEY          "${REGKEY}"
!define MUI_STARTMENUPAGE_REGISTRY_VALUENAME    "Start Menu Folder"  
!define MUI_VERSION                             "${VERSION}"
!define MUI_PRODUCT                             "ChiHuaHua ${MUI_VERSION}"
!define MUI_BRANDINGTEXT                        ""
!define MUI_ICON                                "install.ico"
!define MUI_UNICON                              "uninstall.ico"
!define MUI_FINISHPAGE_LINK						"Learn more about ChiHuaHua"
!define MUI_FINISHPAGE_LINK_LOCATION			"https://github.com/michelm/chihuahua"

Var StartMenuFolder
Var InstallPath
Var UninstallString

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_STARTMENU Application $StartMenuFolder
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_WELCOME
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_COMPONENTS
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH
!insertmacro MUI_LANGUAGE "English"

Section "-Install" Section0
	SetOutPath "$INSTDIR"
	File ..\README.md
	File ..\LICENSE
SectionEnd

Section "Python" Section1
	SetOutPath "$INSTDIR\packages"
	NSISdl::download http://www.python.org/ftp/python/${PYTHON_VER}/${PYTHON_PKG} "${PYTHON_PKG}"
	ExecWait '"msiexec" /i "$INSTDIR\packages\${PYTHON_PKG}"'
	
	${If} ${RunningX64}
		SetRegView 64
	${EndIf}
	ReadRegStr $R0 HKLM "SOFTWARE\Python\PythonCore\${PYTHON_MAJ}\InstallPath" ""
	StrCpy $InstallPath $R0
	StrCmp $InstallPath "" 0 +3
	ReadRegStr $R0 HKCU "SOFTWARE\Python\PythonCore\${PYTHON_MAJ}\InstallPath" ""
	StrCpy $InstallPath $R0
	StrCpy $0 $InstallPath "" -1
	StrCmp $0 "\" +2 0
	StrCmp $0 "/" 0 +2
	StrCpy $0 $InstallPath -1
	StrCpy $InstallPath $0
	${EnvVarUpdate} $0 "PATH" "R" "HKLM" "$InstallPath\Scripts"
	${EnvVarUpdate} $0 "PATH" "P" "HKLM" "$InstallPath\Scripts"
	${EnvVarUpdate} $0 "PATH" "R" "HKLM" "$InstallPath"
	${EnvVarUpdate} $0 "PATH" "P" "HKLM" "$InstallPath"

	ReadEnvStr $R0 "PATH"
	StrCpy $R0 "$InstallPath;$InstallPath\Scripts;$R0"
	SetEnv::SetEnvVar "PATH" $R0
SectionEnd
LangString DESC_Section1 ${LANG_ENGLISH} "Installs Python ${PYTHON_VER}."

Section "PyTools" Section2	
	SetOutPath "$INSTDIR\packages"
	File "download-pip.py"
	nsExec::ExecToLog 'python download-pip.py'
	Pop $0
	${If} $0 != 0
		MessageBox MB_OK "Failed to download PIP."
		Abort
	${EndIf}

	nsExec::ExecToLog 'python get-pip.py'
	Pop $0
	${If} $0 != 0
		MessageBox MB_OK "Failed to install PIP."
		Abort
	${EndIf}
	
	SetOutPath "$INSTDIR\packages"	
	nsExec::ExecToLog 'pip install Pygments'
	Pop $0
	${If} $0 != 0
		MessageBox MB_OK "Failed to install Pygments."
		Abort
	${EndIf}

	SetOutPath "$INSTDIR\packages\waftools\waftools"
	File ..\src\waftools\*.py
	SetOutPath "$INSTDIR\packages\waftools"
	File ..\src\setup.py
	nsExec::ExecToLog 'python setup.py install'
	Pop $0
	${If} $0 != 0
		MessageBox MB_OK "Failed to install waftools."
		Abort
	${EndIf}
SectionEnd
LangString DESC_Section2 ${LANG_ENGLISH} "Installs additional python modules and tools (pip, setuptools, pygments, waftools, ...)"

Section "CppCheck" Section3
    SetOutPath "$INSTDIR\packages"
	NSISdl::download http://optimate.dl.sourceforge.net/project/cppcheck/cppcheck/${CPPCHECK_VER}/${CPPCHECK_PKG} "${CPPCHECK_PKG}"
    ExecWait '"msiexec" /i "$INSTDIR\packages\${CPPCHECK_PKG}"'	

	${If} ${RunningX64}
		SetRegView 64
	${EndIf}
	ReadRegStr $R0 HKCU "Software\Cppcheck" "InstallationPath"
	StrCpy $InstallPath $R0
	StrCpy $0 $InstallPath "" -1
	StrCmp $0 "\" +2 0
	StrCmp $0 "/" 0 +2
	StrCpy $0 $InstallPath -1
	StrCpy $InstallPath $0
	${EnvVarUpdate} $0 "PATH" "R" "HKLM" "$InstallPath"
	${EnvVarUpdate} $0 "PATH" "A" "HKLM" "$InstallPath"
SectionEnd
LangString DESC_Section3 ${LANG_ENGLISH} "Installs CppCheck ${CPPCHECK_VER}"

Section "MinGW" Section4
    SetOutPath "$INSTDIR\packages"	
	NSISdl::download http://optimate.dl.sourceforge.net/project/mingw/Installer/mingw-get-setup.exe "${MINGW_PKG}"	
	ExecWait "$INSTDIR\packages\${MINGW_PKG}"

	SetShellVarContext all
	IfFileExists "$DESKTOP\MinGW Installer.lnk" 0 mingw_not_detected
		ShellLink::GetShortCutTarget "$DESKTOP\MinGW Installer.lnk"
		Pop $0
		StrCpy $InstallPath $0
		Push "\libexec\mingw-get\guimain.exe"
		Push $InstallPath
		Call Slice
		Pop $R0
		Pop $R1
		StrCpy $InstallPath $R0
		${EnvVarUpdate} $0 "PATH" "R" "HKLM" "$InstallPath\bin"
		${EnvVarUpdate} $0 "PATH" "R" "HKLM" "$InstallPath\msys\1.0\bin"
		${EnvVarUpdate} $0 "PATH" "A" "HKLM" "$InstallPath\bin"
		${EnvVarUpdate} $0 "PATH" "A" "HKLM" "$InstallPath\msys\1.0\bin"

		${If} ${RunningX64}
			SetRegView 64
		${EndIf}
		WriteRegStr HKCU "${REGKEY}" "InstallPathMinGW" "$InstallPath"
		Goto mingw_end
mingw_not_detected:
		MessageBox MB_OK "Installation path of MinGW could not be detected.$\r$\n\
		Please add the following paths to the PATH system environment variable:$\r$\n\
		<path_to_mingw>/bin$\r$\n\
		<path_to_mingw>/msys/1.0/bin"
mingw_end:
	SetShellVarContext current
SectionEnd
LangString DESC_Section4 ${LANG_ENGLISH} "Installs MinGW compiler suite."

Section "NSIS" Section5
    SetOutPath "$INSTDIR\packages"
	NSISdl::download http://prdownloads.sourceforge.net/nsis/${NSIS_PKG}?download "${NSIS_PKG}"
	ExecWait "$INSTDIR\packages\${NSIS_PKG}"

	${If} ${RunningX64}
		SetRegView 32
	${EndIf}
	ReadRegStr $R0 HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\NSIS" "InstallLocation"
	StrCpy $InstallPath $R0
	${If} ${RunningX64}
		SetRegView 64
	${EndIf}
	${EnvVarUpdate} $0 "PATH" "R" "HKLM" "$InstallPath"
	${EnvVarUpdate} $0 "PATH" "A" "HKLM" "$InstallPath"	
SectionEnd
LangString DESC_Section5 ${LANG_ENGLISH} "Install NSIS ${NSIS_VER}"

Section "CodeBlocks" Section6
    SetOutPath "$INSTDIR\packages"
	NSISdl::download http://skylink.dl.sourceforge.net/project/codeblocks/Binaries/${CODEBLOCKS_VER}/Windows/${CODEBLOCKS_PKG} "${CODEBLOCKS_PKG}"	
    ExecWait "$INSTDIR\packages\${CODEBLOCKS_PKG}"	
SectionEnd
LangString DESC_Section6 ${LANG_ENGLISH} "Installs CodeBlocks ${CODEBLOCKS_VER}"

Section "Waf" Section7
    SetOutPath "$INSTDIR\packages"
	File ${WAF_PKG}
    ExecWait "$INSTDIR\packages\${WAF_PKG}"	
SectionEnd
LangString DESC_Section7 ${LANG_ENGLISH} "Installs Waf ${WAF_VER}"

Section "-Post install" Section8
	${If} ${RunningX64}
		SetRegView 64
	${EndIf}
    WriteRegStr HKCU "${REGKEY}" 				"" 					$INSTDIR
    WriteRegStr HKCU "${UNINSTALL_REGKEY}" 		"DisplayName"		"ChiHuaHua"
    WriteRegStr HKCU "${UNINSTALL_REGKEY}" 		"DisplayVersion"	"${VERSION}"
    WriteRegStr HKCU "${UNINSTALL_REGKEY}" 		"InstallLocation"	"$INSTDIR"
    WriteRegStr HKCU "${UNINSTALL_REGKEY}" 		"Publisher"			""
    WriteRegStr HKCU "${UNINSTALL_REGKEY}" 		"UninstallString"	"$INSTDIR\Uninstall.exe"
	WriteRegDWORD HKCU "${UNINSTALL_REGKEY}"	"VersionMajor"		${VER_MAJOR}
	WriteRegDWORD HKCU "${UNINSTALL_REGKEY}"	"VersionMinor"		${VER_MINOR}
    WriteUninstaller "$INSTDIR\Uninstall.exe"
    
    !insertmacro MUI_STARTMENU_WRITE_BEGIN Application
        CreateDirectory "$SMPROGRAMS\$StartMenuFolder"
        CreateShortCut "$SMPROGRAMS\$StartMenuFolder\Uninstall.lnk" "$INSTDIR\Uninstall.exe"
    !insertmacro MUI_STARTMENU_WRITE_END
SectionEnd

!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
    !insertmacro MUI_DESCRIPTION_TEXT ${Section1} $(DESC_Section1)
    !insertmacro MUI_DESCRIPTION_TEXT ${Section2} $(DESC_Section2)
    !insertmacro MUI_DESCRIPTION_TEXT ${Section3} $(DESC_Section3)
    !insertmacro MUI_DESCRIPTION_TEXT ${Section4} $(DESC_Section4)
    !insertmacro MUI_DESCRIPTION_TEXT ${Section5} $(DESC_Section5)
    !insertmacro MUI_DESCRIPTION_TEXT ${Section6} $(DESC_Section6)
    !insertmacro MUI_DESCRIPTION_TEXT ${Section7} $(DESC_Section7)
!insertmacro MUI_FUNCTION_DESCRIPTION_END

Section Uninstall
    Delete "$INSTDIR\Uninstall.exe"
    RMDir /r /REBOOTOK "$INSTDIR"    
    !insertmacro MUI_STARTMENU_GETFOLDER Application $StartMenuFolder
    Delete "$SMPROGRAMS\$StartMenuFolder\Uninstall.lnk"
    RMDir "$SMPROGRAMS\$StartMenuFolder"    
    DeleteRegKey /ifempty HKCU "${REGKEY}"
	DeleteRegKey HKCU "${UNINSTALL_REGKEY}"
SectionEnd

Section "Un.Python"
	${If} ${RunningX64}
		SetRegView 64
	${EndIf}
	ReadRegStr $R0 HKLM "SOFTWARE\Python\PythonCore\${PYTHON_MAJ}\InstallPath" ""
	StrCpy $InstallPath $R0
	StrCmp $InstallPath "" 0 +3
	ReadRegStr $R0 HKCU "SOFTWARE\Python\PythonCore\${PYTHON_MAJ}\InstallPath" ""
	StrCpy $InstallPath $R0
	StrCpy $0 $InstallPath "" -1
	StrCmp $0 "\" +2 0
	StrCmp $0 "/" 0 +2
	StrCpy $0 $InstallPath -1
	StrCpy $InstallPath $0
    ${un.EnvVarUpdate} $0 "PATH" "R" "HKLM" "$InstallPath\Scripts"

    ExecWait '"msiexec" /uninstall "$INSTDIR\packages\${PYTHON_PKG}"'
	RMDir /r $InstallPath
SectionEnd

Section "Un.CppCheck"
	${If} ${RunningX64}
		SetRegView 64
	${EndIf}	
	ReadRegStr $R0 HKCU "SOFTWARE\CppCheck" "InstallationPath"
	StrCpy $InstallPath $R0
    ${un.EnvVarUpdate} $0 "PATH" "R" "HKLM" "$InstallPath"
    ExecWait '"msiexec" /uninstall "$INSTDIR\packages\${CPPCHECK_PKG}"'	
SectionEnd

Section "Un.MinGW"
	${If} ${RunningX64}
		SetRegView 64
	${EndIf}
	ReadRegStr $R0 HKCU "${REGKEY}" "InstallPathMinGW"
	StrCpy $InstallPath $R0
	StrCmp $InstallPath "" mingw_uninstall 0

	SetShellVarContext all
	IfFileExists "$DESKTOP\MinGW Installer.lnk" 0 mingw_not_detected
		ShellLink::GetShortCutTarget "$DESKTOP\MinGW Installer.lnk"
		Pop $0
		StrCpy $InstallPath $0
		Push "\libexec\mingw-get\guimain.exe"
		Push $InstallPath
		Call un.Slice
		Pop $R0
		Pop $R1
		StrCpy $InstallPath $R0
		
mingw_uninstall:	
	${un.EnvVarUpdate} $0 "PATH" "R" "HKLM" "$InstallPath\bin"
	${un.EnvVarUpdate} $0 "PATH" "R" "HKLM" "$InstallPath\msys\1.0\bin"
	RMDir /r $InstallPath
	Delete "$DESKTOP\MinGW Installer.lnk"		
	Goto mingw_end

mingw_not_detected:
	MessageBox MB_OK "Installation path of MinGW could not be detected.$\r$\n\
	Since the 'MinGW Installer' shortcut could not be found on the desktop.$\r$\n\
	Please remove manually."

mingw_end:

SectionEnd

Section "Un.NSIS"
	${If} ${RunningX64}
		SetRegView 32
	${EndIf}
	ReadRegStr $R0 HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\NSIS" "InstallLocation"
	StrCpy $InstallPath $R0
	ReadRegStr $R0 HKLM "SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\NSIS" "UninstallString"
	StrCpy $UninstallString $R0

	${If} ${RunningX64}
		SetRegView 64
	${EndIf}
	${un.EnvVarUpdate} $0 "PATH" "R" "HKLM" "$InstallPath"	
	ExecWait "$UninstallString"
SectionEnd

Section "Un.CodeBlocks"
	${If} ${RunningX64}
		SetRegView 64
	${EndIf}
	ReadRegStr $R0 HKLM "SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\CodeBlocks" "UninstallString"
	StrCpy $UninstallString $R0
	StrCmp $UninstallString "" 0 +3
	ReadRegStr $R0 HKCU "SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\CodeBlocks" "UninstallString"
	StrCpy $UninstallString $R0
	
	ExecWait "$UninstallString"
SectionEnd

Section "Un.Waf"
	${If} ${RunningX64}
		SetRegView 64
	${EndIf}
	ReadRegStr $R0 HKCU "SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Waf\UninstallString" ""
	StrCpy $UninstallString $R0
	ExecWait "$UninstallString"
SectionEnd

Function .onInit
    ${IfNot} ${RunningX64}
        MessageBox MB_ICONSTOP "This $(^Name) installer is suitable for 64-bit Windows only!"
        Abort
  ${EndIf}
FunctionEnd


Function un.onInit
    MessageBox MB_ICONQUESTION|MB_YESNO|MB_DEFBUTTON2 "Are you sure you want to completely remove $(^Name) and all of its components?" IDYES +2
    Abort
FunctionEnd


Function un.onUninstSuccess
    HideWindow
    MessageBox MB_ICONINFORMATION|MB_OK "$(^Name) was successfully removed from your computer."
FunctionEnd
