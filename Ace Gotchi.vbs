' Ace Gotchi launcher - starts main.py with no console window.
' Finds the real python.exe on PATH, then prefers pythonw.exe beside it.
Set fso = CreateObject("Scripting.FileSystemObject")
Set sh = CreateObject("WScript.Shell")
folder = fso.GetParentFolderName(WScript.ScriptFullName)
sh.CurrentDirectory = folder

pyw = ""
py = ""

On Error Resume Next
Set exec = sh.Exec("cmd /c where python.exe")
If Err.Number = 0 Then
    stream = exec.StdOut.ReadAll()
    lines = Split(Replace(stream, vbCr, ""), vbLf)
    For Each line In lines
        If Len(Trim(line)) > 0 And fso.FileExists(Trim(line)) Then
            py = Trim(line)
            Exit For
        End If
    Next
End If
Err.Clear

If py <> "" Then
    candidate = fso.BuildPath(fso.GetParentFolderName(py), "pythonw.exe")
    If fso.FileExists(candidate) Then pyw = candidate
End If

If pyw = "" Then
    ' last resort: ask Windows where the pythonw shim lives
    Set exec2 = sh.Exec("cmd /c where pythonw.exe")
    If Err.Number = 0 Then
        stream2 = exec2.StdOut.ReadAll()
        lines2 = Split(Replace(stream2, vbCr, ""), vbLf)
        For Each line2 In lines2
            If Len(Trim(line2)) > 0 And fso.FileExists(Trim(line2)) Then
                pyw = Trim(line2)
                Exit For
            End If
        Next
    End If
End If
On Error GoTo 0

If pyw <> "" Then
    sh.Run """" & pyw & """ """ & folder & "\main.py""", 0, False
ElseIf py <> "" Then
    sh.Run """" & py & """ """ & folder & "\main.py""", 1, False
Else
    MsgBox "Could not find Python. Install Python 3.11+ and tick 'Add to PATH'.", 16, "Ace Gotchi"
End If
