!define VER_MAJOR			1
!define VER_MINOR			7
!define VER_PATCH			15
!define VERSION     		"${VER_MAJOR}.${VER_MINOR}.${VER_PATCH}"
!define REGKEY      		"Software\Waf"
!define UNINSTALL_REGKEY	"Software\Microsoft\Windows\CurrentVersion\Uninstall\Waf"

!include "FileFunc.nsh"
!include "MUI2.nsh"
!include "x64.nsh"
!include "plugins\EnvVarUpdate.nsh"

Var /GLOBAL switch_overwrite
!include "plugins\MoveFileFolder.nsh"

Name                    "waf-${VERSION}"

!ifdef RunningX64
OutFile                 "waf-${VERSION}-win64-setup.exe"
!else
OutFile                 "waf-${VERSION}-win32-setup.exe"
!endif

InstallDir              "$PROGRAMFILES\waf"
InstallDirRegKey        HKCU "${REGKEY}" ""
RequestExecutionLevel   admin
AutoCloseWindow         false
ShowInstDetails         show
ShowUnInstDetails       show
CRCCheck                On

!define MUI_ABORTWARNING
!define MUI_STARTMENUPAGE_REGISTRY_ROOT         HKCU
!define MUI_STARTMENUPAGE_REGISTRY_KEY          "${REGKEY}" 
!define MUI_STARTMENUPAGE_REGISTRY_VALUENAME    "Start Menu Folder"  
!define MUI_VERSION                             "${VERSION}"
!define MUI_PRODUCT                             "Waf"
!define MUI_BRANDINGTEXT                        ""
!define MUI_ICON                                "install.ico"
!define MUI_UNICON                              "uninstall.ico"
!define MUI_FINISHPAGE_LINK						"Learn more about waf"
!define MUI_FINISHPAGE_LINK_LOCATION			"https://code.google.com/p/waf/"

Var StartMenuFolder

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_STARTMENU Application $StartMenuFolder
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_WELCOME
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH
!insertmacro MUI_LANGUAGE "English"


Section "-Install" Section0
	SetOutPath "$INSTDIR\_tmp"
	File extract.py

	nsExec::ExecToStack "python --version"
	Pop $0
	Pop $1
	${If} $0 != 0
		MessageBox MB_OK "Failed to find Python interpreter.$\r$\n\
		$\r$\n\
		Please check installation and/or update system environment path."
		Abort
	${EndIf}
	DetailPrint "Detected python interpreter: $1"

	DetailPrint "Downloading waf package..."
	NSISdl::download https://waf.googlecode.com/files/waf-${VERSION}.tar.bz2 "waf-${VERSION}.tar.bz2"	

	DetailPrint "Extracting waf package..."	
	nsExec::ExecToLog "python extract.py --name=waf-${VERSION}.tar.bz2"
	Pop $0
	${If} $0 != 0
		MessageBox MB_OK "Failed to extract compressed archive."
		Abort
	${EndIf}
	
	DetailPrint "Moving waf package to destination..."	
	!insertmacro MoveFolder "$INSTDIR\_tmp\waf-${VERSION}\" "$INSTDIR" "*.*"

	SetOutPath "$INSTDIR"
	nsExec::ExecToLog "python ./waf-light configure"
	Pop $0
	${If} $0 != 0
		MessageBox MB_OK "Failed to configure waf."
		Abort
	${EndIf}
	
	nsExec::ExecToLog "python ./waf-light build"
	Pop $0
	${If} $0 != 0
		MessageBox MB_OK "Failed to build waf."
		Abort
	${EndIf}
	
	RMDir /r "$INSTDIR\_tmp"	
SectionEnd


Section "-Post install" Section1
	${If} ${RunningX64}
		SetRegView 64
	${EndIf}
	GetFullPathName /SHORT $1 $INSTDIR
    ${EnvVarUpdate} $0 "PATH" "R" "HKLM" "$1"
    ${EnvVarUpdate} $0 "PATH" "P" "HKLM" "$1"

    WriteRegStr HKCU "${REGKEY}" 				"" 					$INSTDIR
    WriteRegStr HKCU "${UNINSTALL_REGKEY}" 		"DisplayName"		"Waf"
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


Section Uninstall
	${If} ${RunningX64}
		SetRegView 64
	${EndIf}
	GetFullPathName /SHORT $1 $INSTDIR
    ${un.EnvVarUpdate} $0 "PATH" "R" "HKLM" "$1"

    Delete "$INSTDIR\Uninstall.exe"
    RMDir /r /REBOOTOK "$INSTDIR"
    !insertmacro MUI_STARTMENU_GETFOLDER Application $StartMenuFolder
    Delete "$SMPROGRAMS\$StartMenuFolder\Uninstall.lnk"
    RMDir "$SMPROGRAMS\$StartMenuFolder"
	
    DeleteRegKey /ifempty HKCU "${REGKEY}"
	DeleteRegKey HKCU "${UNINSTALL_REGKEY}"
SectionEnd


Function un.onInit
    MessageBox MB_ICONQUESTION|MB_YESNO|MB_DEFBUTTON2 "Are you sure you want to completely remove $(^Name) and all of its components?" IDYES +2
    Abort
FunctionEnd


Function un.onUninstSuccess
    HideWindow
    MessageBox MB_ICONINFORMATION|MB_OK "$(^Name) was successfully removed from your computer."
FunctionEnd
