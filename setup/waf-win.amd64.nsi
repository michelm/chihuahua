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
OutFile                 "waf-${VERSION}-win.amd64-setup.exe"
InstallDir              "$PROGRAMFILES\waf"
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
!define MUI_VERSION                             "${VERSION}"
!define MUI_PRODUCT                             "Waf"
!define MUI_BRANDINGTEXT                        ""
!define MUI_ICON                                "install.ico"
!define MUI_UNICON                              "uninstall.ico"
!define MUI_FINISHPAGE_LINK						"https://code.google.com/p/waf/"
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
	File packages\7zip\7za.exe
	NSISdl::download https://waf.googlecode.com/files/waf-${VERSION}.tar.bz2 "waf-${VERSION}.tar.bz2"	
	nsExec::ExecToLog "7za x -y waf-${VERSION}.tar.bz2"
	nsExec::ExecToLog "7za x -y waf-${VERSION}.tar"
	!insertmacro MoveFolder "$INSTDIR\_tmp\waf-${VERSION}\" "$INSTDIR" "*.*"
	SetOutPath "$INSTDIR"

	nsExec::ExecToStack /TIMEOUT=10000 "python ./waf-light configure"
	Pop $0
	Pop $1
	${If} $0 != 0
		MessageBox MB_OK "Failed to configure waf: $0 $1"
	${EndIf}
	
	nsExec::ExecToStack /TIMEOUT=10000 "python ./waf-light build"
	Pop $0
	Pop $1
	${If} $0 != 0
		MessageBox MB_OK "Failed to build waf: $0 $1"
	${EndIf}
SectionEnd


Section "-Post install" Section1
	SetRegView 64
	GetFullPathName /SHORT $1 $INSTDIR
    ${EnvVarUpdate} $0 "PATH" "R" "HKLM" "$1"
    ${EnvVarUpdate} $0 "PATH" "P" "HKLM" "$1"

    WriteRegStr HKLM "${REGKEY}" 				"" 					$INSTDIR
    WriteRegStr HKLM "${UNINSTALL_REGKEY}" 		"DisplayName"		"Waf"
    WriteRegStr HKLM "${UNINSTALL_REGKEY}" 		"DisplayVersion"	"${VERSION}"
    WriteRegStr HKLM "${UNINSTALL_REGKEY}" 		"InstallLocation"	"$INSTDIR"
    WriteRegStr HKLM "${UNINSTALL_REGKEY}" 		"Publisher"			"https://code.google.com/p/waf/"
    WriteRegStr HKLM "${UNINSTALL_REGKEY}" 		"UninstallString"	"$INSTDIR\Uninstall.exe"
	WriteRegDWORD HKLM "${UNINSTALL_REGKEY}"	"VersionMajor"		${VER_MAJOR}
	WriteRegDWORD HKLM "${UNINSTALL_REGKEY}"	"VersionMinor"		${VER_MINOR}
    WriteUninstaller "$INSTDIR\Uninstall.exe"

    !insertmacro MUI_STARTMENU_WRITE_BEGIN Application
        CreateDirectory "$SMPROGRAMS\$StartMenuFolder"
        CreateShortCut "$SMPROGRAMS\$StartMenuFolder\Uninstall.lnk" "$INSTDIR\Uninstall.exe"
    !insertmacro MUI_STARTMENU_WRITE_END
SectionEnd


Section Uninstall
	SetRegView 64
	GetFullPathName /SHORT $1 $INSTDIR
    ${un.EnvVarUpdate} $0 "PATH" "R" "HKLM" "$1"

    Delete "$INSTDIR\Uninstall.exe"
    RMDir /r /REBOOTOK "$INSTDIR"
    !insertmacro MUI_STARTMENU_GETFOLDER Application $StartMenuFolder
    Delete "$SMPROGRAMS\$StartMenuFolder\Uninstall.lnk"
    RMDir "$SMPROGRAMS\$StartMenuFolder"
	
	SetRegView 64
    DeleteRegKey /ifempty HKLM "${REGKEY}"
    DeleteRegKey /ifempty HKCU "${REGKEY}"
	DeleteRegKey HKLM "${UNINSTALL_REGKEY}"
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
