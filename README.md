# Auto Screenshot Manager

Windows 桌面定時截圖工具，Python 3.11+、PySide6（固定官方 Essentials 6.8.3，包含所需 Widgets / Gui / Core）。此交付實作 **Phase 1**，另包含多個獨立任務、設定檔匯出與 JSONL 歷史紀錄；Phase 2–5 的完整驗收尚未完成。

## 安裝與執行

在另一台 Windows 電腦執行原始碼時，先解壓縮整個專案並安裝 Python 3.13（64-bit，使用 Windows Python Launcher 或將 python 加入 PATH），再雙擊 `Start.bat`。首次啟動需連線安裝依賴，完成後會開啟主畫面並關閉命令提示字元。若啟動失敗，視窗會保留錯誤訊息。直接雙擊 `main.py` 時，Python 啟動例外會顯示錯誤對話框，詳細資料寫入 `%TEMP%\AutoScreenshotManager-startup.log`。

Windows 10 64-bit，以下使用已在本機驗證的 Python 3.13（64-bit）。於本資料夾開啟 PowerShell：

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe main.py
```

不需啟用 PowerShell activation script。若使用其他 Python 版本，調整 `py -3.13`。一般使用只需 requirements.txt；開發測試和封裝需 requirements-dev.txt。需互動式 Windows 桌面，不是 Windows Service。`requirements-tested.txt` 保存本機 Python 3.13 的完整測試依賴版本；可用 `python -m pip install -r requirements-tested.txt` 重建相同版本環境。

## 操作

1. 左側選全螢幕擷取、指定區域、指定視窗或指定應用程式。
2. 全螢幕擷取預設輸出 1920 × 1080，可從下拉選單改用常見解析度或原始尺寸。縮放保留比例，必要時補黑邊。顯示器 0 代表所有螢幕，其餘依 mss 列舉順序；從尺寸及座標確認第二個顯示器。螢幕重接後請重新啟動並確認編號。
3. 選擇指定區域後，按「拖曳選取區域」。主視窗會暫時隱藏，游標旁會顯示 5 倍放大鏡與十字準星。放開滑鼠套用範圍，按 Esc 取消，主視窗會在兩種情況下恢復。放大鏡取樣自開始選取時的桌面畫面。座標和尺寸以實體像素顯示，左側螢幕可為負座標，也可以手動修改欄位。
4. 指定視窗／指定應用程式。重新整理並選取清單中的目標，清單依執行檔名稱分組，同組視窗依標題排序，並顯示 PID、尺寸和狀態。指定應用程式模式使用同一視窗清單，以執行檔名稱識別應用程式。可輸入標題關鍵字供視窗重啟後重新尋找；原 HWND / PID / process 仍有效時沿用，否則以 process + 標題匹配。匹配不到或有多個結果就回報錯誤，不任選目標。
   按「在視窗預覽上拖曳選區」可框選目標視窗內的範圍。後續可立即截圖或啟動排程。選區以目標視窗左上角為原點，移動視窗後仍使用同一組相對像素座標。若縮小視窗後選區超出邊界，請重新選取。選區可儲存到設定檔。這個模式需要目標視窗支援 PrintWindow 背景擷取，視窗最小化時請先還原。
5. 設定檔名、儲存資料夾、PNG / JPG、品質及日期子資料夾。立即截圖 立即排入一次工作。
6. 選固定間隔（至少 1 秒）或單次排程（系統本地時間的未來日期），按 啟動排程 新增獨立任務。修改表單只影響之後新增的任務。
7. 從下方任務清單選取任務再 暫停／繼續／停止。正在執行或已排入的截圖仍會完成；停止會移除之後的排程。一次性排程觸發後無後續 job，無法再暫停或恢復。
8. 右側預覽會依可用空間等比例縮放最新截圖，可按「開啟原始圖片」查看原尺寸。儲存設定檔／載入設定檔 儲存或載入目前表單；載入不會自動啟動排程。

每個任務都有獨立設定快照、輸出路徑、狀態、上次時間、下次時間、成功張數及錯誤訊息。立即截圖 也會建立任務列。

## 架構與執行緒

- `gui/`：僅 GUI 主執行緒操作 Qt widgets。區域遮罩為非阻塞 Qt 視窗。
- `capture/`：mss 螢幕及區域擷取、PrintWindow 視窗擷取、服務分派。
- `scheduler/`：APScheduler 3 背景排程，透過 Qt queued signal 將請求送到 GUI。
- `utils/`：DPI awareness、Windows 視窗列舉與重新辨識、互動桌面檢查、唯一檔名、JSON 設定及輪替日誌。
- 截圖與存檔使用單一 ThreadPoolExecutor worker；每次在 worker 內建立並關閉 mss，避免跨執行緒重用其 handle。busy 集合僅由 GUI 執行緒變更，避免同一任務排入多次。
- 不同任務序列執行，因此多個排程可同時啟用，但圖片不保證在同一時刻擷取。執行時間超過間隔時略過該任務的新要求，不堆積同任務工作。
- 關閉時停止排程，等已排入的工作完成才退出。PrintWindow 屬同步 Windows API，若目標掛住，worker 可能長時間等待；GUI 仍可回應，但關閉需等待。尚未實作可終止的獨立擷取子程序。
- 單次工作使用帶 offset 的 ISO 時間。APScheduler 使用啟動時取得的本地時區；系統變更時區後應重新建立排程。睡眠期間不能截圖；喚醒後 coalesce 合併錯過的觸發，超過 30 秒的 misfire 略過。不補拍歷史畫面，也不會喚醒電腦。

## 儲存、紀錄

檔名：`TaskName_YYYYMMDD_HHMMSS_mmm_<12位UUID>.png`，使用 exclusive-create 防止覆寫；同毫秒多圖不互相覆蓋。寫入失敗會清除本次的部分檔案，檔名碰撞不刪除既有檔案。非法 Windows 檔名字元會替換。

`%LOCALAPPDATA%\AutoScreenshotManager\application.log`：2 MB 輪替、3 份備份。
`%LOCALAPPDATA%\AutoScreenshotManager\history.jsonl`：每行記錄時間、任務、模式、圖片路徑、結果及錯誤。歷史及截圖可能包含敏感資訊，請自行管理存取權。

Phase 1 保留所有圖片及歷史；尚未實作保留天數、容量清理與歷史 GUI。磁碟滿或無權限會記錄錯誤並保留主程式運作。

## 背景擷取與 Windows 限制

PrintWindow 優先使用 PW_RENDERFULLCONTENT，擷取完整視窗。它不保證能取得 GPU / DirectComposition、DRM 影片、瀏覽器或其他硬體加速內容。所有擷取模式偵測單色圖片時回報可能失敗；有效純色畫面也可能被拒絕，部分黑畫面則不一定能檢出。成功回傳也不保證內容完整。

最小化視窗會回報錯誤。手動還原或調整大小後，原任務下次擷取會重新讀取視窗的實際長寬。勾選螢幕備援後，PrintWindow 失敗會擷取其桌面矩形，**可能包含遮擋物、其他程式或視窗外內容**；不代表背景內容成功擷取。需使用者自行確保視窗可見。

鎖定畫面、UAC 安全桌面、遠端桌面斷線、不同登入工作階段不可保證擷取；執行前檢查互動桌面可用性，失敗即報錯。睡眠時不執行。較高權限程序可能拒絕一般權限的 PrintWindow，不要求管理員權限且不自動提權。

啟動前設定 per-monitor-v2 DPI awareness。混合縮放螢幕、負座標、跨螢幕遮罩仍需多螢幕實機驗收，特別是 Qt 邏輯桌面與原生實體桌面配置有差異的組合。執行中顯示器位置或縮放改變後請重啟並重選範圍。不要把螢幕擷取當作鎖定狀態的自動化服務。

## 測試

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q
.\.venv\Scripts\python.exe tests/smoke_gui.py
.\.venv\Scripts\python.exe tests/windows_capture_smoke.py
```

單元／基本整合測試也檢查 worker 重入去重、停止期間完成工作的狀態一致性、擷取失敗紀錄與 worker 復原，並涵蓋唯一檔名、JPG、碰撞不覆寫、存檔失敗清理、JSON、無效模式、真正的排程觸發、暫停／恢復／停止、視窗重辨識與歧義處理。GUI smoke test 建立實際 GUI 後退出，不拍攝桌面。測試目前不驗證 Office / Playwright（尚未實作）。實際結果請見 `TEST_RESULTS.md`。

人工 Phase 1 驗收：

- 第二螢幕 interval=10 秒，檢查解析度與時間、負座標。
- 拖曳跨螢幕範圍、不同 DPI、手動輸入及 profile 往返。
- 一般視窗前景、背景、最小化、關閉後重新開啟、多個同名視窗。
- 瀏覽器 GPU 視窗，確認 PrintWindow 錯誤與勾選備援的差別。
- 多任務同時啟用、暫停／繼續／停止、執行期間關閉主程式。
- 鎖定／解鎖、睡眠／喚醒、儲存位置拒絕權限及磁碟滿。

## EXE 打包

在 Windows 64-bit 的專案虛擬環境內：

```powershell
.\.venv\Scripts\python.exe -m PyInstaller --clean --noconfirm build/AutoScreenshotManager.spec --workpath build/work --distpath dist
.\dist\AutoScreenshotManager.exe
```

spec 產生 windowed one-file EXE。首次解壓縮啟動會較慢，日誌放 LOCALAPPDATA，無須寫入 EXE 所在資料夾。發布前需在乾淨 Windows 10 64-bit（無 Python）測試上述人工清單；本機 build 成功不代表 Windows 10 全面相容。不要把開發機的 `.venv` 一起交付。

## 後續階段／未完成

- Phase 2：Excel Workbook / Worksheet / Range / Chart、PowerPoint Presentation / Slide COM 匯出，尚未實作或驗證；需 STA COM worker、序列化剪貼簿、Excel Busy 重試，且不可修改原始資料。視窗截圖可用現有 Window 模式，但不等於內容匯出。
- Phase 3：Playwright URL、CSS、整頁、登入 profile 及刷新尚未實作。瀏覽器視窗可用 Window 模式擷取。未存取或繞過網站登入。
- Phase 4：每日多時間、開始結束區間、排程重啟恢復、tray、開機啟動、歷史瀏覽及保留政策尚未實作。現有 profile 只存表單，關閉程式後不會執行或恢復排程。
- Phase 5：PyInstaller one-file EXE 已產生並通過本機 GUI 啟動／關閉測試；乾淨 Windows 10 實機驗收與安裝程式尚未完成。

本版本未達成原完整規格中 Office、完整網頁及乾淨 Win10 環境的驗收條件；請依 Phase 1 範圍評估。
