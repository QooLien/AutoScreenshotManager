# 驗證紀錄

日期：2026-11-05。本機 Windows 10 Pro 64-bit，build 19045；Python 3.13.0。
最終依賴：PySide6 Essentials / shiboken6 6.8.3、mss 10.2.0、Pillow 12.3.0、pywin32 312、APScheduler 3.11.3、PyInstaller 6.22.3。完整版本見 requirements-tested.txt。

| 項目 | 結果 | 範圍 |
| --- | --- | --- |
| Python compileall | 通過 | 專案 Python 語法 |
| pip check | 通過 | 無相依衝突 |
| pytest | 10 passed，退出碼 0 | 檔案、防覆寫、失敗清理、JSON、排程觸發與控制、視窗重新辨識、worker 去重、停止狀態、錯誤後復原 |
| GUI smoke | 通過，退出碼 0 | 真正建立主畫面、列舉螢幕／視窗、建立排程服務後關閉 |
| GUI 版面 | 已檢視 | 主畫面 QWidget.grab 預覽；座標欄位及設定無水平裁切 |
| PyInstaller EXE | 通過，退出碼 0 | 固定 6.8.3 後 one-file EXE 建立 GUI 並自動關閉；非乾淨機完整驗收 |
| PrintWindow 合成視窗 | 通過 | 原生 API 於 worker 擷取 516 × 339 圖片並存檔；已目視確認紅／藍色圖塊及測試文字 |
| mss 區域擷取 | **未通過** | 沙箱 BitBlt 回報 access denied；沙箱外重試回傳單色，程式正確回報錯誤，未視為成功 |
| PrintWindow 其他應用程式／背景 GPU | 未驗證 | 合成 Qt 視窗結果不能推廣至 Excel、PowerPoint、瀏覽器或最小化視窗 |
| 第二螢幕／混合 DPI／跨螢幕拖曳 | 未驗證 | 本機只列舉到一個 1920 × 1080 顯示器 |
| 鎖定／UAC／睡眠喚醒／改時鐘 | 未做人工驗收 | 已加入桌面可用性檢查及 misfire 設定，不代表環境驗收通過 |
| Office COM／Playwright | 未實作 | Phase 2 / 3 |
| 乾淨 Windows 10 無 Python 環境 | 未驗證 | 尚需獨立測試機 |

原生整合命令 `python tests/windows_capture_smoke.py` 的整體退出碼目前為 1：PrintWindow 部分成功，Selected Region 部分失敗。這是保留的失敗結果，沒有跳過或改成通過。請在可互動的實際桌面重跑。

曾以未固定的 PySide6 6.12.0 打包，EXE 啟動出現 QtWidgets DLL load failed，故將專案固定為 6.8.3 後重新驗證。測試程式也修正了 QApplication / QWidget 銷毀順序，避免 pytest 顯示測試通過後在程序退出時 abort。

## 重跑

於專案資料夾使用依 README 安裝的虛擬環境：

```powershell
.\.venv\Scripts\python.exe -m compileall -q .
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pytest tests -q
.\.venv\Scripts\python.exe tests/smoke_gui.py
.\.venv\Scripts\python.exe tests/windows_capture_smoke.py
.\dist\AutoScreenshotManager.exe --smoke-test
```

`--smoke-test` 僅建立 GUI 並自動關閉，不會擷取桌面。測試圖片和測試日誌位於 `tests/.runtime/`；正式程式預設為 LOCALAPPDATA。開發機的虛擬環境實際在專案上一層 `.venv`，本次執行使用 `..\.venv\Scripts\python.exe`；以上是依 README 新安裝時的路徑。
