Dim objExcel, objWorkbook, objNewWorkbook, objNewSheet
Dim objFSO, strSourceFile, strDestFile
Dim rowCount, colCount, lastRow, i, j, sheetIndex, targetRow

' Set file paths (Use double backslashes for Windows paths)
strSourceFile = "[Source]\Foods_Separated.xlsx" ' Change to your source file path
strDestFile = "[Destination]\Merged.xlsx"       ' Output file path

' Create Excel application object
Set objExcel = CreateObject("Excel.Application")
objExcel.Visible = False
objExcel.DisplayAlerts = False

' Open source workbook
Set objWorkbook = objExcel.Workbooks.Open(strSourceFile)

' Create new workbook for merged data
Set objNewWorkbook = objExcel.Workbooks.Add
Set objNewSheet = objNewWorkbook.Sheets(1)

' Initialize target row index
targetRow = 1

' Loop through all sheets in the source workbook
For sheetIndex = 1 To objWorkbook.Sheets.Count
    Dim objSheet
    Set objSheet = objWorkbook.Sheets(sheetIndex)

    ' Find the last row with data
    lastRow = objSheet.Cells(objSheet.Rows.Count, 1).End(-4162).Row ' -4162 is xlUp

    ' Find the number of columns
    colCount = objSheet.UsedRange.Columns.Count

    ' Copy header only once (from first sheet)
    If sheetIndex = 1 Then
        For j = 1 To colCount
            objNewSheet.Cells(1, j).Value = objSheet.Cells(1, j).Value
        Next
        targetRow = 2 ' Move to next row after header
    End If

    ' Copy data (excluding header row)
    For i = 2 To lastRow
        For j = 1 To colCount
            objNewSheet.Cells(targetRow, j).Value = objSheet.Cells(i, j).Value
        Next
        targetRow = targetRow + 1
    Next

    Set objSheet = Nothing
Next

' Auto-fit columns
objNewSheet.Columns.AutoFit

' Save the new workbook
objNewWorkbook.SaveAs strDestFile, 51 ' 51 = xlOpenXMLWorkbook (.xlsx)

' Clean up
objWorkbook.Close False
objNewWorkbook.Close True
objExcel.Quit

Set objWorkbook = Nothing
Set objNewWorkbook = Nothing
Set objExcel = Nothing

MsgBox "Merging completed! File saved as: " & strDestFile, vbInformation, "Done"
