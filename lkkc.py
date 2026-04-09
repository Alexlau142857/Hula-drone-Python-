# -*- coding: utf-8 -*-
import time
import math
import threading
import pyhula
import pyhula.userapi as api

# ---------------- 全域數位孿生開關 ---------------- #
DRY_RUN = True  # True: 終端機模擬印出路徑 | False: 實機發送指令

# ---------------- 物理限制與環境參數 ---------------- #
MAX_SPEED = 80       # 最高速度 (cm/s)
SAFE_X = 80          # 水平最小間距 (cm)
SAFE_Y = 60          # 深度交錯最小間距 (cm)
SAFE_Z = 150         # 垂直最小間距 (cm)
MAX_BOUND = 500      # 空間邊界 (cm)

# 全域無人機狀態
TOTAL_DRONES = 20
active_drones = list(range(TOTAL_DRONES))
formation_lock = threading.Lock()

# ---------------- 拓撲座標解算引擎 ---------------- #
def generate_L(drone_count):
    # L字型：垂直與水平線段
    coords = []
    vert_count = int(drone_count * 0.6)
    horiz_count = drone_count - vert_count
    for i in range(vert_count):
        # Y軸交錯以滿足 3D 距離限制
        coords.append((0, (i%2)*SAFE_Y, i*SAFE_Z * (MAX_BOUND/SAFE_Z/vert_count)))
    for i in range(1, horiz_count + 1):
        coords.append((i*SAFE_X, (i%2)*SAFE_Y, 0))
    return coords

def generate_K(drone_count):
    # K字型：左側垂直，右上斜線，右下斜線
    coords = []
    vert = drone_count // 2
    upper = (drone_count - vert) // 2
    lower = drone_count - vert - upper
    for i in range(vert):
        coords.append((0, (i%2)*SAFE_Y, i*SAFE_Z * 0.6))
    mid_z = (vert // 2) * SAFE_Z * 0.6
    for i in range(1, upper + 1):
        coords.append((i*SAFE_X, (i%2)*SAFE_Y, mid_z + i*SAFE_Z*0.5))
    for i in range(1, lower + 1):
        coords.append((i*SAFE_X, (i%2)*SAFE_Y, mid_z - i*SAFE_Z*0.5))
    return coords

def generate_C(drone_count):
    # C字型：半圓形弧線
    coords = []
    radius = 200
    for i in range(drone_count):
        angle = math.pi * 0.2 + (math.pi * 1.6 * (i / max(1, drone_count - 1)))
        x = radius * math.cos(angle)
        z = radius * math.sin(angle) + 250
        coords.append((x, (i%2)*SAFE_Y, z))
    return coords

def generate_45(drone_count):
    # 45字型：左邊 4，右邊 5
    coords = []
    half = drone_count // 2
    # 生成 4 (左側)
    for i in range(half):
        if i < 4: coords.append((-150 - i*30, (i%2)*SAFE_Y, 150 + i*40)) # 斜線
        elif i < 7: coords.append((-150 + (i-4)*40, (i%2)*SAFE_Y, 150)) # 水平
        else: coords.append((-100, (i%2)*SAFE_Y, 100 + (i-7)*50)) # 垂直
    # 生成 5 (右側)
    for i in range(half):
        if i < 3: coords.append((100 + i*40, (i%2)*SAFE_Y, 300)) # 頂部水平
        elif i < 5: coords.append((100, (i%2)*SAFE_Y, 300 - (i-2)*50)) # 左上垂直
        elif i < 8: coords.append((100 + (i-5)*40, (i%2)*SAFE_Y, 200 - (i-5)*20)) # 圓弧上半
        else: coords.append((100 + (i-8)*40, (i%2)*SAFE_Y, 100)) # 底部
    return coords

# ---------------- 動態重構與飛行控制 ---------------- #
def execute_formation(shape_name, color_rgb):
    with formation_lock:
        current_count = len(active_drones)
        if current_count == 0:
            return

        # 動態幾何解算
        if shape_name == "L": targets = generate_L(current_count)
        elif shape_name == "K": targets = generate_K(current_count)
        elif shape_name == "C": targets = generate_C(current_count)
        elif shape_name == "45": targets = generate_45(current_count)
        else: targets = [(0,0,0)] * current_count

        print(f"\n[矩陣躍遷] 啟動圖形: {shape_name} | 參演機數: {current_count}")
        
        for idx, drone_id in enumerate(active_drones):
            tx, ty, tz = targets[idx]
            r, g, b = color_rgb
            
            if DRY_RUN:
                print(f"  [DRY_RUN] Drone {drone_id:02d} -> 航點 (X:{tx:5.1f}, Y:{ty:5.1f}, Z:{tz:5.1f}) | 燈光: RGB({r},{g},{b})")
            else:
                try:
                    # 發送實際飛行與燈光指令 (依照 Pyhula API 邏輯)
                    api.fly_to(drone_id, tx, ty, tz, MAX_SPEED)
                    api.set_led(drone_id, r, g, b)
                    if shape_name == "45" and idx % 2 == 0:
                        api.Plane_cmd_electromagnet(drone_id, 2) # 雷射或特效模擬
                except Exception as e:
                    print(f"  [錯誤] Drone {drone_id} 傳輸失敗: {e}")
        
        # 轉場時間
        time.sleep(5 if DRY_RUN else 10)

# ---------------- 容錯與環境監控執行緒 ---------------- #
def telemetry_monitor():
    while True:
        if DRY_RUN:
            time.sleep(2)
            continue
            
        with formation_lock:
            for drone_id in list(active_drones):
                try:
                    bat = api.get_battery(drone_id)
                    acc = api.get_accelerated_speed(drone_id) # [X, Y, Z]
                    
                    # 電量低下或姿態嚴重異常防護
                    if bat < 10 or abs(acc[0]) > 200 or abs(acc[1]) > 200:
                        print(f"[終極防護] 偵測到 Drone {drone_id} 異常 (電量: {bat}%, 姿態: {acc})。啟動緊急隔離降落！")
                        api.land(drone_id)
                        active_drones.remove(drone_id)
                        print(f"[動態重構] 剩餘機數 {len(active_drones)}，下一圖形將自動啟動 N-1 拓撲運算。")
                except:
                    pass
        time.sleep(1)

# ---------------- 主劇本執行緒 ---------------- #
def main():
    print("=== Pyhula_AI 數位孿生編舞系統啟動 ===")
    if DRY_RUN:
        print(">>> 目前為 DRY_RUN 模式，無實機聯線，僅作空間拓撲運算與終端機模擬 <<<")
    else:
        print(">>> 實機模式已啟動，請確保周遭淨空 <<<")
        # 啟動全機群起飛
        for d in active_drones:
            api.takeoff(d, 100) # 預設升空至 100cm
        time.sleep(5)

    # 啟動監控執行緒
    monitor_thread = threading.Thread(target=telemetry_monitor, daemon=True)
    monitor_thread.start()

    # 執行序列：L ➔ K ➔ K ➔ C ➔ 45
    sequence = [
        ("L", (0, 100, 255)),    # 啟航藍
        ("K", (150, 0, 255)),    # 躍動紫
        ("K", (255, 0, 150)),    # 迴響粉
        ("C", (0, 255, 200)),    # 聚合青
        ("45", (255, 200, 0))    # 榮耀金
    ]

    for shape, color in sequence:
        execute_formation(shape, color)

    print("\n[演出結束] 啟動全機群歸航程序...")
    if not DRY_RUN:
        for d in active_drones:
            api.land(d)

if __name__ == "__main__":
    # 若需實飛，請將全局變數 DRY_RUN 改為 False
    main()
