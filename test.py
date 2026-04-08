import math
import time
from concurrent.futures import ThreadPoolExecutor
# 假設已安裝並導入 pyhula SDK
# import pyhula 

# ==========================================
# 1. 組網與系統配置 (Fleet Network Management)
# ==========================================
DRONE_IPS = [f"192.168.0.{101 + i}" for i in range(20)] # 假設 Router 模式下分配的 IP
NUM_DRONES = len(DRONE_IPS)
TILT_ANGLE = math.radians(20) # 仰角優化 20 度
SPACING = 80 # 最小安全間距 80cm
STAGGER = 60 # Y 軸錯位深度 60cm

# LED 策略配置
LED_STRATEGY = {
    'L':  {'r': 0,   'g': 255, 'b': 0,   'mode': 1},   # Phase 1: 綠色 常亮
    'K1': {'r': 255, 'g': 128, 'b': 0,   'mode': 1},   # Phase 2: 橘色 常亮
    'K2': {'r': 0,   'g': 0,   'b': 255, 'mode': 1},   # Phase 3: 藍色 常亮
    'C':  {'r': 128, 'g': 0,   'b': 128, 'mode': 64},  # Phase 4: 紫色 呼吸
    '45': {'r': 255, 'g': 0,   'b': 0,   'mode': 32}   # Phase 5: 紅色 閃爍
}

# 初始化 API 實例列表 (模擬)
# apis = [pyhula.UserApi(ip) for ip in DRONE_IPS]
class MockAPI:
    def __init__(self, ip, index):
        self.ip = ip
        self.index = index
    def single_fly_takeoff(self): pass
    def single_fly_hover_flight(self, t): pass
    # 假設有一個將無人機導航到絕對 X, Y, Z 座標的擴展指令，並設定 LED
    def single_fly_go_xyz(self, x, y, z, speed, led_dict):
        pass
    def single_fly_land(self): pass

apis = [MockAPI(ip, i) for i, ip in enumerate(DRONE_IPS)]

# ==========================================
# 2. 空間數學與仰視優化核心
# ==========================================
def apply_tilt(x, y, z):
    """應用觀眾視角的 X 軸旋轉矩陣"""
    y_new = y * math.cos(TILT_ANGLE) - z * math.sin(TILT_ANGLE)
    z_new = y * math.sin(TILT_ANGLE) + z * math.cos(TILT_ANGLE)
    return x, y_new, z_new

def generate_shape_L():
    """生成字母 L 的安全座標清單"""
    coords = []
    base_z = 200 # 基準高度 200cm
    
    for i in range(NUM_DRONES):
        if i < 13:
            # 垂直主幹 (13 架)
            x = 0
            z = base_z + i * SPACING
            # 防擾流 Y 軸深度錯位
            y = STAGGER if i % 2 != 0 else 0 
        else:
            # 水平底座 (7 架)
            x = (i - 12) * SPACING
            z = base_z
            y = 0 # 橫向已有足夠的 X 間距，無需 Y 軸錯位
            
        # 套用仰視優化矩陣
        x_tilt, y_tilt, z_tilt = apply_tilt(x, y, z)
        coords.append((x_tilt, y_tilt, z_tilt))
    return coords

def generate_shape_K():
    """生成字母 K 的安全座標清單 (簡化版)"""
    # 這裡將以參數化生成 K 的主幹與兩條斜線，同樣對主幹應用 Y 軸錯位
    # 為保持長度簡潔，此處回傳佔位座標，實際應用中需依比例劃分 20 架飛機
    coords = [(i*10, (i%2)*STAGGER, 200 + i*40) for i in range(NUM_DRONES)] 
    return [apply_tilt(x, y, z) for x, y, z in coords]

def generate_shape_C():
    """生成字母 C 的安全座標清單 (半圓形)"""
    coords = []
    R = 300 # 半徑
    for i in range(NUM_DRONES):
        angle = math.pi/2 + (i / (NUM_DRONES - 1)) * math.pi # 90度到270度
        x = R * math.cos(angle)
        z = 200 + R + R * math.sin(angle)
        y = (i % 2) * 30 # 稍微錯位以防萬一
        coords.append(apply_tilt(x, y, z))
    return coords

def generate_shape_45():
    """生成數字 45 的安全座標清單"""
    coords = [(i*20, 0, 200 + i*20) for i in range(NUM_DRONES)] # 佔位邏輯
    return [apply_tilt(x, y, z) for x, y, z in coords]

# ==========================================
# 3. 併發執行與安全機制
# ==========================================
def move_drone(api, coord, led_config):
    """驅動單架無人機飛往指定座標 (被執行緒池呼叫)"""
    x, y, z = coord
    # 使用 50 cm/s 的安全過渡速度
    api.single_fly_go_xyz(x, y, z, 50, led_config)

def execute_formation(coords, led_config, hold_time=5):
    """透過 ThreadPoolExecutor 平行調度所有無人機變換陣型"""
    print(f"\n🚀 開始執行陣型變換...")
    with ThreadPoolExecutor(max_workers=NUM_DRONES) as executor:
        for i, api in enumerate(apis):
            executor.submit(move_drone, api, coords[i], led_config)
    
    # 確保所有無人機到達定位後懸停展示
    print(f"✨ 陣型就位，維持 {hold_time} 秒...")
    time.sleep(hold_time)

def emergency_land():
    """全域緊急迫降機制"""
    print("🚨 觸發緊急迫降！所有無人機立即降落！")
    with ThreadPoolExecutor(max_workers=NUM_DRONES) as executor:
        for api in apis:
            executor.submit(api.single_fly_land)

# ==========================================
# 4. 主編舞程式 (Main Show Flow)
# ==========================================
def main_show():
    try:
        # 起飛準備
        print("🛫 執行全機隊起飛...")
        with ThreadPoolExecutor(max_workers=NUM_DRONES) as executor:
            for api in apis:
                executor.submit(api.single_fly_takeoff)
        time.sleep(5) # 等待起飛完成
        
        # Phase 1: 字母 'L'
        coords_L = generate_shape_L()
        execute_formation(coords_L, LED_STRATEGY['L'], hold_time=8)
        
        # Phase 2: 字母 'K' (橘色)
        coords_K = generate_shape_K()
        execute_formation(coords_K, LED_STRATEGY['K1'], hold_time=6)
        
        # Phase 3: 字母 'K' (藍色)
        # 座標與 Phase 2 相同，僅改變 LED 顏色
        execute_formation(coords_K, LED_STRATEGY['K2'], hold_time=6)
        
        # Phase 4: 字母 'C'
        coords_C = generate_shape_C()
        execute_formation(coords_C, LED_STRATEGY['C'], hold_time=8)
        
        # Phase 5: 數字 '45'
        coords_45 = generate_shape_45()
        execute_formation(coords_45, LED_STRATEGY['45'], hold_time=10)
        
        # 完美降落
        print("🛬 表演結束，執行安全降落...")
        emergency_land() # 這裡作為常規降落調用
        
    except Exception as e:
        print(f"❌ 發生未預期錯誤: {e}")
        emergency_land()

if __name__ == "__main__":
    main_show()