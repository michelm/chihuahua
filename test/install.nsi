
!include "MUI2.nsh"
!include "x64.nsh"

!ifndef VER_MAJOR
!define VER_MAJOR			0
!endif

!ifndef VER_MINOR
!define VER_MINOR			0
!endif

!ifndef VER_PATCH
!define VER_PATCH			0
!endif

!ifndef VERSION
!define VERSION     		"${VER_MAJOR}.${VER_MINOR}.${VER_PATCH}"
!endif

!ifndef APPNAME
!define APPNAME				"ChiHuaHuaTest"
!endif

!ifndef INSTALLER
!ifdef RunningX64
!define INSTALLER			"${APPNAME}-win64-setup.exe"
!else
!define INSTALLER			"${APPNAME}-win32-setup.exe"
!endif
!endif

!define REGKEY      		"Software\${APPNAME}"
!define UNINSTALL_REGKEY	"Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}"

Name                    	"${APPNAME} ${VERSION}"
OutFile                 	"${INSTALLER}"
InstallDir              	"$PROGRAMFILES\${APPNAME}"
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
!define MUI_PRODUCT                             "${APPNAME} ${MUI_VERSION}"
!define MUI_BRANDINGTEXT                        ""

Var StartMenuFolder

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_STARTMENU Application $StartMenuFolder
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
	File /r *.*
SectionEnd


Section "-Post install" Section1
	${If} ${RunningX64}
		SetRegView 64
	${EndIf}
    WriteRegStr HKCU "${REGKEY}" 				"" 					$INSTDIR
    WriteRegStr HKCU "${UNINSTALL_REGKEY}" 		"DisplayName"		"${APPNAME}"
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
    Delete "$INSTDIR\Uninstall.exe"
    RMDir /r /REBOOTOK "$INSTDIR"    
    !insertmacro MUI_STARTMENU_GETFOLDER Application $StartMenuFolder
    Delete "$SMPROGRAMS\$StartMenuFolder\Uninstall.lnk"
    RMDir "$SMPROGRAMS\$StartMenuFolder"    
    DeleteRegKey /ifempty HKCU "${REGKEY}"
	DeleteRegKey HKCU "${UNINSTALL_REGKEY}"
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

