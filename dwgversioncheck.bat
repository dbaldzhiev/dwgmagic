@echo off
:: Create a temporary VBScript file to read DWG version codes
set "VBS=%TEMP%\GetDWGVersion.vbs"
> "%VBS%" echo Set fso = CreateObject("Scripting.FileSystemObject")
>>"%VBS%" echo Set folder = fso.GetFolder(".")
>>"%VBS%" echo Dim versionMap
>>"%VBS%" echo Set versionMap = CreateObject("Scripting.Dictionary")

:: Add version mappings
>>"%VBS%" echo versionMap.Add "AC1012", "AutoCAD R13"
>>"%VBS%" echo versionMap.Add "AC1014", "AutoCAD R14"
>>"%VBS%" echo versionMap.Add "AC1015", "AutoCAD 2000"
>>"%VBS%" echo versionMap.Add "AC1018", "AutoCAD 2004"
>>"%VBS%" echo versionMap.Add "AC1021", "AutoCAD 2007"
>>"%VBS%" echo versionMap.Add "AC1024", "AutoCAD 2010"
>>"%VBS%" echo versionMap.Add "AC1027", "AutoCAD 2013"
>>"%VBS%" echo versionMap.Add "AC1032", "AutoCAD 2018"
>>"%VBS%" echo versionMap.Add "AC1036", "AutoCAD 2024"

>>"%VBS%" echo For Each file In folder.Files
>>"%VBS%" echo^  If LCase(fso.GetExtensionName(file.Name)) = "dwg" Then
>>"%VBS%" echo^    Set stream = CreateObject("ADODB.Stream")
>>"%VBS%" echo^    stream.Type = 1 : stream.Open : stream.LoadFromFile file.Path
>>"%VBS%" echo^    stream.Position = 0 : stream.Type = 2 : stream.Charset = "ASCII"
>>"%VBS%" echo^    code = stream.ReadText(6)
>>"%VBS%" echo^    stream.Close
>>"%VBS%" echo^    If versionMap.Exists(code) Then
>>"%VBS%" echo^       version = versionMap.Item(code)
>>"%VBS%" echo^    Else
>>"%VBS%" echo^       version = "Unknown Version"
>>"%VBS%" echo^    End If
>>"%VBS%" echo^    WScript.Echo file.Name ^& ": " ^& code ^& " - " ^& version
>>"%VBS%" echo^  End If
>>"%VBS%" echo Next

:: Run the VBScript using CScript (Windows Script Host)
cscript //nologo "%VBS%"

:: Cleanup and pause the console
del "%VBS%"
pause
