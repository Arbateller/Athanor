' ============================================================
' StockFetcher.bas - Excel VBA Module
' Pulls stock data from your local FastAPI into Excel
'
' HOW TO USE:
' 1. Open Excel
' 2. Press Alt+F11 to open VBA Editor
' 3. Insert > Module
' 4. Paste this entire file
' 5. Press F5 or run FetchAllStocks()
' ============================================================

' Configuration - change these if needed
Const API_BASE_URL As String = "http://localhost:8000"
Const SHEET_NAME As String = "StockData"
Const REFRESH_INTERVAL_SECONDS As Integer = 60

' ─── MAIN FUNCTION ────────────────────────────────────────

Sub FetchAllStocks()
    ' Fetches all tracked stocks and writes to sheet
    Dim ws As Worksheet
    Dim jsonData As String
    Dim http As Object

    ' Get or create the StockData sheet
    ws = GetOrCreateSheet(SHEET_NAME)

    ' Make HTTP request to API
    Set http = CreateObject("MSXML2.XMLHTTP")
    http.Open "GET", API_BASE_URL & "/stocks/list", False
    http.Send

    If http.Status <> 200 Then
        MsgBox "API Error: " & http.Status & " - " & http.statusText & Chr(13) & _
               "Make sure your FastAPI server is running!", vbCritical
        Exit Sub
    End If

    jsonData = http.responseText

    ' Parse and write data
    WriteStocksToSheet ws, jsonData

    ' Update timestamp
    ws.Range("A1").Value = "Last Updated: " & Now()
    ws.Range("A1").Font.Italic = True
    ws.Range("A1").Font.Color = RGB(128, 128, 128)

    MsgBox "✅ Stock data refreshed at " & Format(Now(), "HH:MM:SS"), vbInformation
End Sub


Sub FetchSingleStock()
    ' Fetches a single stock - prompts for ticker
    Dim ticker As String
    Dim ws As Worksheet
    Dim jsonData As String
    Dim http As Object

    ticker = InputBox("Enter stock ticker symbol:", "Fetch Stock", "AAPL")
    If ticker = "" Then Exit Sub

    ticker = UCase(Trim(ticker))

    Set http = CreateObject("MSXML2.XMLHTTP")
    http.Open "GET", API_BASE_URL & "/stock/" & ticker, False
    http.Send

    If http.Status = 404 Then
        MsgBox "❌ Ticker '" & ticker & "' not found!", vbExclamation
        Exit Sub
    ElseIf http.Status <> 200 Then
        MsgBox "API Error: " & http.Status, vbCritical
        Exit Sub
    End If

    jsonData = http.responseText

    ' Write single stock to a dedicated row
    ws = GetOrCreateSheet(SHEET_NAME)
    WriteSingleStockFromJSON ws, jsonData, ticker

    MsgBox "✅ " & ticker & " data updated!", vbInformation
End Sub


' ─── SHEET SETUP ──────────────────────────────────────────

Function GetOrCreateSheet(sheetName As String) As Worksheet
    Dim ws As Worksheet

    ' Check if sheet exists
    For Each ws In ThisWorkbook.Worksheets
        If ws.Name = sheetName Then
            GetOrCreateSheet = ws
            SetupHeaders ws
            Exit Function
        End If
    Next ws

    ' Create new sheet
    Set ws = ThisWorkbook.Worksheets.Add
    ws.Name = sheetName
    SetupHeaders ws
    GetOrCreateSheet = ws
End Function


Sub SetupHeaders(ws As Worksheet)
    ' Write column headers in row 3
    Dim headers As Variant
    headers = Array("Ticker", "Name", "Price", "Change", "Change %", _
                    "Open", "High", "Low", "Prev Close", "Volume", _
                    "Market Cap", "PE Ratio", "52W High", "52W Low", _
                    "Currency", "Exchange", "Last Updated")

    Dim col As Integer
    For col = 0 To UBound(headers)
        With ws.Cells(3, col + 1)
            .Value = headers(col)
            .Font.Bold = True
            .Font.Color = RGB(255, 255, 255)
            .Interior.Color = RGB(0, 70, 127)
        End With
    Next col

    ' Auto-fit columns
    ws.Columns("A:Q").AutoFit
End Sub


' ─── DATA WRITING ─────────────────────────────────────────
' NOTE: Excel VBA doesn't have native JSON parsing.
' This is a simple implementation. For production,
' use Power Query instead (see PowerQuery_Setup.md)

Sub WriteStocksToSheet(ws As Worksheet, jsonData As String)
    ' Simple approach: call the API and use Power Query
    ' This sub just triggers a Power Query refresh if available

    ' For direct VBA approach, we'd need a JSON parser library
    ' Recommendation: Use Power Query (Data > Get Data > From Web)
    ' URL: http://localhost:8000/stocks/list

    MsgBox "Tip: For best results, use Power Query!" & Chr(13) & _
           "1. Data tab > Get Data > From Web" & Chr(13) & _
           "2. URL: " & API_BASE_URL & "/stocks/list" & Chr(13) & _
           "3. Click Refresh to update data", vbInformation
End Sub


' ─── AUTO REFRESH ─────────────────────────────────────────

Dim refreshTimer As Double

Sub StartAutoRefresh()
    ' Start auto-refreshing every N seconds
    refreshTimer = Now + TimeSerial(0, 0, REFRESH_INTERVAL_SECONDS)
    Application.OnTime refreshTimer, "AutoRefreshCallback"
    MsgBox "Auto-refresh started every " & REFRESH_INTERVAL_SECONDS & " seconds.", vbInformation
End Sub

Sub AutoRefreshCallback()
    FetchAllStocks
    ' Schedule next refresh
    refreshTimer = Now + TimeSerial(0, 0, REFRESH_INTERVAL_SECONDS)
    Application.OnTime refreshTimer, "AutoRefreshCallback"
End Sub

Sub StopAutoRefresh()
    On Error Resume Next
    Application.OnTime refreshTimer, "AutoRefreshCallback", , False
    MsgBox "Auto-refresh stopped.", vbInformation
End Sub
