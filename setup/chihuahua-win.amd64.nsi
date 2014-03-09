!define VER_MAJOR			0
!define VER_MINOR			1
!define VER_PATCH			1
!define VERSION     		"${VER_MAJOR}.${VER_MINOR}.${VER_PATCH}"
!define REGKEY      		"Software\ChiHuaHua"
!define UNINSTALL_REGKEY	"Software\Microsoft\Windows\CurrentVersion\Uninstall\ChiHuaHua"

!define PYTHON_MAJ			"3.3"
!define PYTHON_VER			"3.3.3"
!define CPPCHECK_VER		"1.64"
!define NSIS_VER			"3.0a2"
!define CODEBLOCKS_VER		"13.12"
!define WAF_VER				"1.7.15"

!define PYTHON_PKG			"python-${PYTHON_VER}.amd64.msi"
!define CPPCHECK_PKG		"cppcheck-${CPPCHECK_VER}-x86-Setup.msi"
!define MINGW_PKG			"mingw-get-setup.exe"
!define NSIS_PKG			"nsis-${NSIS_VER}-setup.exe"
!define CODEBLOCKS_PKG		"codeblocks-${CODEBLOCKS_VER}-setup.exe"
!define WAF_PKG				"waf-${WAF_VER}-win.amd64-setup.exe"

!addplugindir "plugins"
!include "plugins\EnvVarUpdate.nsh"
!include "plugins\Slice.nsh"
!include "MUI2.nsh"
!include "x64.nsh"

Name                    "ChiHuaHua"
OutFile                 "chihuahua-v${VERSION}-win.amd64-setup.exe"
InstallDir              "$PROGRAMFILES\chihuahua"
InstallDirRegKey        HKLM "${REGKEY}" ""
RequestExecutionLevel   admin
AutoCloseWindow         false
ShowInstDetails         show
ShowUnInstDetails       show
CRCCheck                On

!define MUI_ABORTWARNING
!define MUI_STARTMENUPAGE_REGISTRY_ROOT         HKLM
!define MUI_STARTMENUPAGE_REGISTRY_KEY          "${REGKEY}"
!define MUI_STARTMENUPAGE_REGISTRY_VALUENAME    "Start Menu Folder"  
!define MUI_VERSION                             "v${VERSION}"
!define MUI_PRODUCT                             "ChiHuaHua ${MUI_VERSION}"
!define MUI_BRANDINGTEXT                        ""
!define MUI_ICON                                "install.ico"
!define MUI_UNICON                              "uninstall.ico"
!define MUI_FINISHPAGE_LINK						"https://github.com/michelm/chihuahua"
!define MUI_FINISHPAGE_LINK_LOCATION			"https://github.com/michelm/chihuahua"

Var StartMenuFolder
Var PythonPath
Var MinGWPath
Var UninstallString
Var InstallPath

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
    SetOutPath "$INSTDIR\packages"
	File packages\python\ez_setup.py

	StrCpy $PythonPath ""
    SetOutPath "$INSTDIR"
	File ..\LICENSE
SectionEnd

Section "Python" Section1
    SetOutPath "$INSTDIR\packages"
	NSISdl::download http://www.python.org/ftp/python/${PYTHON_VER}/${PYTHON_PKG} "${PYTHON_PKG}"
	ExecWait '"msiexec" /i "$INSTDIR\packages\${PYTHON_PKG}"'
	
	SetRegView 64
	ReadRegStr $R0 HKLM "SOFTWARE\Python\PythonCore\${PYTHON_MAJ}\InstallPath" ""
	StrCpy $PythonPath $R0
	StrCmp $PythonPath "" 0 +3
	ReadRegStr $R0 HKCU "SOFTWARE\Python\PythonCore\${PYTHON_MAJ}\InstallPath" ""
	StrCpy $PythonPath $R0
	StrCpy $0 $PythonPath "" -1
	StrCmp $0 "\" +2 0
	StrCmp $0 "/" 0 +2
	StrCpy $0 $PythonPath -1
	StrCpy $PythonPath $0
    ${EnvVarUpdate} $0 "PATH" "R" "HKLM" "$PythonPath\Scripts"
    ${EnvVarUpdate} $0 "PATH" "P" "HKLM" "$PythonPath\Scripts"
    ${EnvVarUpdate} $0 "PATH" "R" "HKLM" "$PythonPath"
    ${EnvVarUpdate} $0 "PATH" "P" "HKLM" "$PythonPath"
	
	ReadEnvStr $R0 "PATH"
	StrCpy $R0 "$PythonPath;$PythonPath\Scripts;$R0"
	SetEnv::SetEnvVar "PATH" $R0
SectionEnd
LangString DESC_Section1 ${LANG_ENGLISH} "Installs Python version ${PYTHON_VER}."

Section "PyTools" Section2
    SetOutPath "$INSTDIR\packages"
	File packages\python\ez_setup.py
	nsExec::ExecToLog 'python ez_setup.py'
	Pop $0
	Pop $1
	${If} $0 != 0
		MessageBox MB_OK "Failed to install Setuptools: $0 $1"
	${EndIf}

    SetOutPath "$INSTDIR\packages"
	File packages\python\get-pip.py	
	nsExec::ExecToLog 'python get-pip.py'
	Pop $0
	Pop $1
	${If} $0 != 0
		MessageBox MB_OK "Failed to install Setuptools: $0 $1"
	${EndIf}
	
    SetOutPath "$INSTDIR\packages"	
	nsExec::ExecToLog 'pip install Pygments'
	Pop $0
	Pop $1
	${If} $0 != 0
		MessageBox MB_OK "Failed to install Pygments: $0 $1"
	${EndIf}

    SetOutPath "$INSTDIR\packages\waftools\waftools"
	File ..\waftools\*.py
    SetOutPath "$INSTDIR\packages\waftools"
	File ..\setup.py
	nsExec::ExecToLog 'python setup.py install'
	Pop $0
	Pop $1
	${If} $0 != 0
		MessageBox MB_OK "Failed to install waftools: $0 $1"
	${EndIf}
SectionEnd
LangString DESC_Section2 ${LANG_ENGLISH} "Installs additional python modules and tools (pip, setuptools, pygments, waftools, ...)"

Section "CppCheck" Section3
    SetOutPath "$INSTDIR\packages"
	NSISdl::download http://optimate.dl.sourceforge.net/project/cppcheck/cppcheck/${CPPCHECK_VER}/${CPPCHECK_PKG} "${CPPCHECK_PKG}"
    ExecWait '"msiexec" /i "$INSTDIR\packages\${CPPCHECK_PKG}"'	
	
	SetRegView 64
	ReadRegStr $R0 HKCU "SOFTWARE\CppCheck\InstallationPath" ""
	StrCpy $InstallPath $R0
    ${EnvVarUpdate} $0 "PATH" "R" "HKLM" "$InstallPath"
    ${EnvVarUpdate} $0 "PATH" "A" "HKLM" "$InstallPath"	
SectionEnd
LangString DESC_Section3 ${LANG_ENGLISH} "Installs cppcheck, a C/C++ source code analyzer."

Section "MinGW" Section4
    SetOutPath "$INSTDIR\packages"	
	NSISdl::download http://optimate.dl.sourceforge.net/project/mingw/Installer/mingw-get-setup.exe "${MINGW_PKG}"	
	ExecWait "$INSTDIR\packages\${MINGW_PKG}"

	SetShellVarContext all
	IfFileExists "$DESKTOP\MinGW Installer.lnk" 0 mingw_not_detected
		ShellLink::GetShortCutTarget "$DESKTOP\MinGW Installer.lnk"
		Pop $0
		StrCpy $MinGWPath $0
		Push "\libexec\mingw-get\guimain.exe"
		Push $MinGWPath
		Call Slice
		Pop $R0
		Pop $R1
		StrCpy $MinGWPath $R0
		${EnvVarUpdate} $0 "PATH" "R" "HKLM" "$MinGWPath\bin"
		${EnvVarUpdate} $0 "PATH" "R" "HKLM" "$MinGWPath\msys\1.0\bin"
		${EnvVarUpdate} $0 "PATH" "A" "HKLM" "$MinGWPath\bin"
		${EnvVarUpdate} $0 "PATH" "A" "HKLM" "$MinGWPath\msys\1.0\bin"
		SetRegView 64
		WriteRegStr HKLM "${REGKEY}" "InstallPathMinGW" "$MinGWPath"
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
SectionEnd
LangString DESC_Section5 ${LANG_ENGLISH} "Nullsoft Scriptable Install System"

Section "CodeBlocks" Section6
    SetOutPath "$INSTDIR\packages"
	NSISdl::download http://skylink.dl.sourceforge.net/project/codeblocks/Binaries/${CODEBLOCKS_VER}/Windows/${CODEBLOCKS_PKG} "${CODEBLOCKS_PKG}"	
    ExecWait "$INSTDIR\packages\${CODEBLOCKS_PKG}"	
SectionEnd
LangString DESC_Section6 ${LANG_ENGLISH} "Installs Code::Block (C/C++ IDE well suited for cross platform development)."

Section "Waf" Section7
    SetOutPath "$INSTDIR\packages"
	File ${WAF_PKG}
    ExecWait "$INSTDIR\packages\${WAF_PKG}"	
SectionEnd
LangString DESC_Section7 ${LANG_ENGLISH} "Installs Waf - The Meta Build System."

Section "-Post install" Section8
	SetRegView 64
    WriteRegStr HKLM "${REGKEY}" 				"" 					$INSTDIR
    WriteRegStr HKLM "${UNINSTALL_REGKEY}" 		"DisplayName"		"ChiHuaHua"
    WriteRegStr HKLM "${UNINSTALL_REGKEY}" 		"DisplayVersion"	"${VERSION}"
    WriteRegStr HKLM "${UNINSTALL_REGKEY}" 		"InstallLocation"	"$INSTDIR"
    WriteRegStr HKLM "${UNINSTALL_REGKEY}" 		"Publisher"			"https://github.com/michelm/chihuahua"
    WriteRegStr HKLM "${UNINSTALL_REGKEY}" 		"UninstallString"	"$INSTDIR\Uninstall.exe"
	WriteRegDWORD HKLM "${UNINSTALL_REGKEY}"	"VersionMajor"		${VER_MAJOR}
	WriteRegDWORD HKLM "${UNINSTALL_REGKEY}"	"VersionMinor"		${VER_MINOR}
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
    DeleteRegKey /ifempty HKLM "${REGKEY}"
	DeleteRegKey HKLM "${UNINSTALL_REGKEY}"
SectionEnd

Section "Un.Python"	
    ExecWait '"msiexec" /uninstall "$INSTDIR\packages\${PYTHON_PKG}"'
	SetRegView 64
	ReadRegStr $R0 HKLM "SOFTWARE\Python\PythonCore\${PYTHON_MAJ}\InstallPath" ""
	StrCpy $PythonPath $R0
	StrCpy $0 $PythonPath "" -1
	StrCmp $0 "\" +2 0
	StrCmp $0 "/" 0 +2
	StrCpy $0 $PythonPath -1
	StrCpy $PythonPath $0
    ${un.EnvVarUpdate} $0 "PATH" "R" "HKLM" "$PythonPath\Scripts"
	RMDir /r $PythonPath
SectionEnd

Section "Un.CppCheck"
	SetRegView 64
	ReadRegStr $R0 HKCU "SOFTWARE\CppCheck\InstallationPath" ""
	StrCpy $InstallPath $R0
    ${un.EnvVarUpdate} $0 "PATH" "R" "HKLM" "$InstallPath"

    ExecWait '"msiexec" /uninstall "$INSTDIR\packages\${CPPCHECK_PKG}"'	
SectionEnd

Section "Un.MinGW"
	SetRegView 64
	ReadRegStr $R0 HKLM "${REGKEY}\InstallPathMinGW" ""
	; TODO

	SetShellVarContext all
	IfFileExists "$DESKTOP\MinGW Installer.lnk" 0 mingw_not_detected
		ShellLink::GetShortCutTarget "$DESKTOP\MinGW Installer.lnk"
		Pop $0
		StrCpy $MinGWPath $0
		Push "\libexec\mingw-get\guimain.exe"
		Push $MinGWPath
		Call un.Slice
		Pop $R0
		Pop $R1
		StrCpy $MinGWPath $R0
		${un.EnvVarUpdate} $0 "PATH" "R" "HKLM" "$MinGWPath\bin"
		${un.EnvVarUpdate} $0 "PATH" "R" "HKLM" "$MinGWPath\msys\1.0\bin"
		RMDir /r $MinGWPath
		Delete "$DESKTOP\MinGW Installer.lnk"		
		Goto mingw_end
mingw_not_detected:
		MessageBox MB_OK "Installation path of MinGW could not be detected.$\r$\n\
		Since the 'MinGW Installer' shortcut could not be found on the desktop.$\r$\n\
		Please remove manually."
mingw_end:

SectionEnd

Section "Un.NSIS"
	SetRegView 64
	ReadRegStr $R0 HKLM "SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\NSIS\UninstallString" ""
	StrCpy $UninstallString $R0
	ExecWait "$UninstallString"
SectionEnd

Section "Un.CodeBlocks"
	SetRegView 64
	ReadRegStr $R0 HKLM "SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\CodeBlocks\UninstallString" ""
	StrCpy $UninstallString $R0
	ExecWait "$UninstallString"
SectionEnd

Section "Un.Waf"
	SetRegView 64
	ReadRegStr $R0 HKLM "SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Waf\UninstallString" ""
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
