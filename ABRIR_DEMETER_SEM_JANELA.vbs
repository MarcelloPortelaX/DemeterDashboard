Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
folder = fso.GetParentFolderName(WScript.ScriptFullName)
shell.Run Chr(34) & folder & "\INICIAR_DEMETER.bat" & Chr(34), 0, False
