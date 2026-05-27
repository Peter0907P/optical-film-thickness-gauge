from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import numpy as np
from scipy.optimize import minimize
import os
import uvicorn

app = FastAPI()

# 1. 託管靜態檔案資料夾（網頁介面）
app.mount("/static", StaticFiles(directory="static"), name="static")

# 2. 首頁直接導向 index.html
@app.get("/")
def read_index():
    return FileResponse("static/index.html")

# 3. 定義前端傳來的資料格式 (初始猜測膜厚)
class MeasureRequest(BaseModel):
    initial_guess: float

# 4. 膜厚量測與擬合演算法 API
@app.post("/api/measure")
def measure_thickness(req: MeasureRequest):
    # 模擬光譜儀抓到的實測波長 (400nm ~ 800nm)
    wavelengths = np.linspace(400, 800, 100)
    
    # 模擬一組真實厚度為 350 nm 的實測反射率數據（加上一點雜訊）
    true_d = 350.0
    n_air = 1.0
    n_film = 1.45  # 假設是二氧化矽 SiO2 的折射率
    n_sub = 1.5    # 假設是玻璃基板的折射率
    
    def calc_theoretical_R(d_val):
        # 簡易薄膜干涉公式（相位差）
        delta = (4 * np.pi * n_film * d_val) / wavelengths
        # 簡化反射率模型
        return 0.5 + 0.3 * np.cos(delta)
    
    # 產生模擬的實測數據
    noise = np.random.normal(0, 0.02, len(wavelengths))
    measured_R = calc_theoretical_R(true_d) + noise
    
    # 定義擬合最佳化的目標函數（RMSE 均方根誤差）
    def objective_function(d):
        theoretical_R = calc_theoretical_R(d[0])
        return np.sqrt(np.mean((measured_R - theoretical_R) ** 2))
    
    # 執行 Scipy 最佳化尋優
    res = minimize(objective_function, x0=[req.initial_guess], bounds=[(10, 2000)])
    fitted_d = float(res.x[0])
    
    # 計算擬合後的理論曲線，用來畫在網頁圖表上
    fitted_R = calc_theoretical_R(fitted_d)
    
    # 將數據包裝成 JSON 回傳給前端
    return {
        "status": "success",
        "thickness_nm": round(fitted_d, 2),
        "wavelengths": wavelengths.tolist(),
        "measured_R": measured_R.tolist(),
        "fitted_R": fitted_R.tolist()
    }

if __name__ == "__main__":
    # Render 自動分配連接埠，本機預設 8000
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=False)