
Function Slice
 Exch $R0 ; input string
 Exch
 Exch $R1 ; to cut
 Push $R2
 Push $R3
 Push $R4
 Push $R5
 
 StrLen $R3 $R1
 StrCpy $R4 -1
 StrCpy $R5 0
 
 Loop:
 
  IntOp $R4 $R4 + 1
  StrCpy $R2 $R0 $R3 $R4
  StrCmp $R2 "" Done
  StrCmp $R2 $R1 0 Loop
 
   StrCpy $R5 1
 
   StrCmp $R4 0 0 +3
    StrCpy $R1 ""
    Goto +2
   StrCpy $R1 $R0 $R4
   StrLen $R2 $R0
   IntOp $R4 $R2 - $R4
   IntOp $R4 $R4 - $R3
   IntCmp $R4 0 0 0 +3
    StrCpy $R2 ""
    Goto +2
   StrCpy $R2 $R0 "" -$R4
   StrCpy $R0 $R1$R2
 
 Done:
 StrCpy $R1 $R5
 
 Pop $R5
 Pop $R4
 Pop $R3
 Pop $R2
 Exch $R1 ; slice? 0/1
 Exch
 Exch $R0 ; output string
FunctionEnd


Function un.Slice
 Exch $R0 ; input string
 Exch
 Exch $R1 ; to cut
 Push $R2
 Push $R3
 Push $R4
 Push $R5
 
 StrLen $R3 $R1
 StrCpy $R4 -1
 StrCpy $R5 0
 
 Loop:
 
  IntOp $R4 $R4 + 1
  StrCpy $R2 $R0 $R3 $R4
  StrCmp $R2 "" Done
  StrCmp $R2 $R1 0 Loop
 
   StrCpy $R5 1
 
   StrCmp $R4 0 0 +3
    StrCpy $R1 ""
    Goto +2
   StrCpy $R1 $R0 $R4
   StrLen $R2 $R0
   IntOp $R4 $R2 - $R4
   IntOp $R4 $R4 - $R3
   IntCmp $R4 0 0 0 +3
    StrCpy $R2 ""
    Goto +2
   StrCpy $R2 $R0 "" -$R4
   StrCpy $R0 $R1$R2
 
 Done:
 StrCpy $R1 $R5
 
 Pop $R5
 Pop $R4
 Pop $R3
 Pop $R2
 Exch $R1 ; slice? 0/1
 Exch
 Exch $R0 ; output string
FunctionEnd





