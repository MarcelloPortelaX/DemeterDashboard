Set WshShell = CreateObject("WScript.Shell")
Set FileSystem = CreateObject("Scripting.FileSystemObject")

ProjectFolder = FileSystem.GetParentFolderName(WScript.ScriptFullName)
BatFile = ProjectFolder & "\abrir_demeter_pro.bat"

WshShell.Run chr(34) & BatFile & chr(34), 0, False

Set WshShell = Nothing
Set FileSystem = Nothing
