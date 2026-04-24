"""
彩票学习工具 - 完全确定性版 Web 界面（支持彩票类型）
同一时间 + 同一彩票类型 → 完全相同的结果
声明：仅供编程学习与传统文化研究，严禁用于赌博。
"""

import streamlit as st
import sqlite3
from datetime import datetime, date
import hashlib
from collections import Counter, defaultdict
import os

# 设置页面配置
st.set_page_config(page_title="彩票学习工具", page_icon="🎲", layout="wide")

# ==================== 数据库文件路径 ====================
DB_FILE = "lottery_history.db"

# ==================== 辅助函数：确定性哈希 ====================
def deterministic_index(seed_str, max_val):
    """根据种子字符串返回0到max_val-1之间的确定性整数"""
    hash_val = int(hashlib.md5(seed_str.encode()).hexdigest(), 16)
    return hash_val % max_val

def deterministic_sample(population, k, seed_str):
    """基于种子的确定性抽样（返回排序后的列表）"""
    if k > len(population):
        return sorted(population)
    indexed = [(deterministic_index(seed_str + str(item), len(population)), item) for item in population]
    indexed.sort(key=lambda x: x[0])
    return sorted([item for _, item in indexed[:k]])

# ==================== 时柱干支 ====================
def get_hour_ganzhi(year_gan, month_gan, day_gan, hour):
    dizhi = ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥']
    if hour == 23 or hour == 0:
        dz_index = 0
    elif hour == 1 or hour == 2:
        dz_index = 1
    elif hour == 3 or hour == 4:
        dz_index = 2
    elif hour == 5 or hour == 6:
        dz_index = 3
    elif hour == 7 or hour == 8:
        dz_index = 4
    elif hour == 9 or hour == 10:
        dz_index = 5
    elif hour == 11 or hour == 12:
        dz_index = 6
    elif hour == 13 or hour == 14:
        dz_index = 7
    elif hour == 15 or hour == 16:
        dz_index = 8
    elif hour == 17 or hour == 18:
        dz_index = 9
    elif hour == 19 or hour == 20:
        dz_index = 10
    else:
        dz_index = 11
    
    tiangan = ['甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸']
    start_map = {
        '甲': '甲', '己': '甲',
        '乙': '丙', '庚': '丙',
        '丙': '戊', '辛': '戊',
        '丁': '庚', '壬': '庚',
        '戊': '壬', '癸': '壬'
    }
    start_gan = start_map.get(day_gan, '甲')
    start_index = tiangan.index(start_gan)
    tg_index = (start_index + dz_index) % 10
    tg = tiangan[tg_index]
    return f"{tg}{dizhi[dz_index]}"

# ==================== 模块1：平衡选号（确定性） ====================
class BalanceFilter:
    TOTAL = 49
    PICK = 7
    SMALL_MAX = 24
    LARGE_MIN = 25
    SUM_MIN = 160
    SUM_MAX = 190
    ZONE_SIZE = 7
    MIN_ZONES = 4
    
    @staticmethod
    def is_balanced(numbers):
        if len(numbers) != BalanceFilter.PICK:
            return False
        odd_cnt = sum(1 for n in numbers if n % 2 == 1)
        even_cnt = BalanceFilter.PICK - odd_cnt
        if (odd_cnt, even_cnt) not in [(3,4), (4,3)]:
            return False
        small_cnt = sum(1 for n in numbers if n <= BalanceFilter.SMALL_MAX)
        large_cnt = BalanceFilter.PICK - small_cnt
        if (small_cnt, large_cnt) not in [(3,4), (4,3)]:
            return False
        total = sum(numbers)
        if total < BalanceFilter.SUM_MIN or total > BalanceFilter.SUM_MAX:
            return False
        consecutive_pairs = 0
        for i in range(len(numbers)-1):
            if numbers[i+1] - numbers[i] == 1:
                consecutive_pairs += 1
        if consecutive_pairs > 1:
            return False
        for i in range(len(numbers)-2):
            if numbers[i+2] - numbers[i] == 2:
                return False
        zones = set((n-1)//BalanceFilter.ZONE_SIZE for n in numbers)
        if len(zones) < BalanceFilter.MIN_ZONES:
            return False
        return True
    
    @staticmethod
    def generate_balanced(seed_str):
        """从所有平衡组合中，根据种子字符串选一个固定组合"""
        all_combos = BalanceFilter.get_all_balanced()
        if not all_combos:
            return list(range(1, 8))
        idx = deterministic_index(seed_str, len(all_combos))
        return all_combos[idx]
    
    @staticmethod
    @st.cache_resource
    def get_all_balanced():
        """预计算所有符合平衡条件的组合"""
        from itertools import combinations
        all_nums = range(1, 50)
        cache = []
        for combo in combinations(all_nums, 7):
            if BalanceFilter.is_balanced(list(combo)):
                cache.append(sorted(combo))
        return cache

# ==================== 模块2：聪明组合（确定性） ====================
class WheelGenerator:
    @staticmethod
    def generate(pool, pick=7, guarantee=4, seed_str=""):
        pool = sorted(set(pool))
        if len(pool) < pick:
            return []
        from itertools import combinations
        all_combos = list(combinations(pool, pick))
        if not all_combos:
            return []
        idx = deterministic_index(seed_str + str(pool), len(all_combos))
        return [sorted(all_combos[idx])]

# ==================== 模块3：号码属性（生肖修正版） ====================
class NumberAttributes:
    BASE_YEAR = 2026
    BASE_ZODIAC = ['马', '蛇', '龙', '兔', '虎', '牛', '鼠', '猪', '狗', '鸡', '猴', '羊']
    WUXING = {1:'水',2:'水',3:'木',4:'木',5:'火',6:'火',7:'土',8:'土',9:'金',0:'金'}
    BA_GUA = {1:'乾',2:'兑',3:'离',4:'震',5:'巽',6:'坎',7:'艮',0:'坤'}
    BA_GUA_SYMBOL = {'乾':'☰','兑':'☱','离':'☲','震':'☳','巽':'☴','坎':'☵','艮':'☶','坤':'☷'}
    
    @staticmethod
    def get_zodiac(num, year=None):
        if year is None:
            year = datetime.now().year
        offset = (year - NumberAttributes.BASE_YEAR) % 12
        base_index = (num - 1) % 12
        actual_index = (base_index + offset) % 12
        return NumberAttributes.BASE_ZODIAC[actual_index]
    
    @staticmethod
    def get_wuxing(num):
        return NumberAttributes.WUXING[num % 10]
    
    @staticmethod
    def get_bagua(num):
        return NumberAttributes.BA_GUA[num % 8]
    
    @staticmethod
    def get_full_attrs(num, year=None):
        if year is None:
            year = datetime.now().year
        return {
            'number': num,
            'zodiac': NumberAttributes.get_zodiac(num, year),
            'wuxing': NumberAttributes.get_wuxing(num),
            'bagua': NumberAttributes.get_bagua(num),
            'symbol': NumberAttributes.BA_GUA_SYMBOL.get(NumberAttributes.get_bagua(num), '')
        }
    
    @staticmethod
    def format_attrs(num, year=None):
        attrs = NumberAttributes.get_full_attrs(num, year)
        return f"{num}({attrs['zodiac']},{attrs['wuxing']},{attrs['bagua']}{attrs['symbol']})"
    
    @staticmethod
    def format_number_list(nums, year=None):
        return ' '.join(NumberAttributes.format_attrs(n, year) for n in nums)

# ==================== 模块4：易经起卦 ====================
class YijingDivination:
    BA_GUA = {
        1: {"name": "乾", "symbol": "☰", "meaning": "天", "attr": "健"},
        2: {"name": "兑", "symbol": "☱", "meaning": "泽", "attr": "悦"},
        3: {"name": "离", "symbol": "☲", "meaning": "火", "attr": "丽"},
        4: {"name": "震", "symbol": "☳", "meaning": "雷", "attr": "动"},
        5: {"name": "巽", "symbol": "☴", "meaning": "风", "attr": "入"},
        6: {"name": "坎", "symbol": "☵", "meaning": "水", "attr": "陷"},
        7: {"name": "艮", "symbol": "☶", "meaning": "山", "attr": "止"},
        8: {"name": "坤", "symbol": "☷", "meaning": "地", "attr": "顺"}
    }
    
    HEXAGRAM_NAMES = {
        (1,1):"乾为天",(1,2):"天泽履",(1,3):"天火同人",(1,4):"天雷无妄",(1,5):"天风姤",(1,6):"天水讼",(1,7):"天山遁",(1,8):"天地否",
        (2,1):"泽天夬",(2,2):"兑为泽",(2,3):"泽火革",(2,4):"泽雷随",(2,5):"泽风大过",(2,6):"泽水困",(2,7):"泽山咸",(2,8):"泽地萃",
        (3,1):"火天大有",(3,2):"火泽睽",(3,3):"离为火",(3,4):"火雷噬嗑",(3,5):"火风鼎",(3,6):"火水未济",(3,7):"火山旅",(3,8):"火地晋",
        (4,1):"雷天大壮",(4,2):"雷泽归妹",(4,3):"雷火丰",(4,4):"震为雷",(4,5):"雷风恒",(4,6):"雷水解",(4,7):"雷山小过",(4,8):"雷地豫",
        (5,1):"风天小畜",(5,2):"风泽中孚",(5,3):"风火家人",(5,4):"风雷益",(5,5):"巽为风",(5,6):"风水涣",(5,7):"风山渐",(5,8):"风地观",
        (6,1):"水天需",(6,2):"水泽节",(6,3):"水火既济",(6,4):"水雷屯",(6,5):"水风井",(6,6):"坎为水",(6,7):"水山蹇",(6,8):"水地比",
        (7,1):"山天大畜",(7,2):"山泽损",(7,3):"山火贲",(7,4):"山雷颐",(7,5):"山风蛊",(7,6):"山水蒙",(7,7):"艮为山",(7,8):"山地剥",
        (8,1):"地天泰",(8,2):"地泽临",(8,3):"地火明夷",(8,4):"地雷复",(8,5):"地风升",(8,6):"地水师",(8,7):"地山谦",(8,8):"坤为地"
    }
    
    @staticmethod
    def get_hexagram_name(upper, lower):
        return YijingDivination.HEXAGRAM_NAMES.get((upper, lower), "未知卦")
    
    @staticmethod
    def divination_by_time(dt=None):
        if dt is None:
            dt = datetime.now()
        y, m, d, h, minu = dt.year, dt.month, dt.day, dt.hour, dt.minute
        shang = ((y + m + d + h) % 8) or 8
        xia = ((y + m + d + h + minu) % 8) or 8
        dong = ((y + m + d + h + minu) % 6) or 6
        return {
            "method": "时间起卦",
            "shang_gua": YijingDivination.BA_GUA[shang],
            "xia_gua": YijingDivination.BA_GUA[xia],
            "ben_gua_name": YijingDivination.get_hexagram_name(shang, xia),
            "dong_yao": dong,
            "time": dt.strftime("%Y-%m-%d %H:%M:%S")
        }

# ==================== 模块5：黄历 ====================
class ChineseCalendar:
    @staticmethod
    def get_daily_info(dt=None, hour=12):
        if dt is None:
            dt = date.today()
        if isinstance(dt, datetime):
            hour = dt.hour
            dt = dt.date()
        
        # 硬编码2026-04-19的黄历数据
        if dt == date(2026, 4, 19):
            info = {
                "solar_date": "2026-04-19",
                "weekday": "星期日",
                "lunar_date": "丙午年 三月初三",
                "zodiac": "马",
                "yi": ["房屋清洁", "沐浴", "打鱼", "除事勿取", "结网", "塞穴", "打猎"],
                "ji": ["祈福", "安葬"],
                "chong": "猪日冲蛇 (己亥)",
                "sha": "西",
                "wuxing": "大海水",
                "zhishen": "玉堂",
                "jianchu": "危日",
                "tai_shen": "占房床外东南",
                "pengzu": "癸不词讼理弱故强 亥不嫁娶不利新郎",
                "ji_shen": "母仓 玉堂",
                "xiong_shen": "游祸 天赋 重日",
                "ganzhi": "丙午 壬辰 癸亥",
                "nayin": "大海水"
            }
            hour_ganzhi = get_hour_ganzhi('丙', '壬', '癸', hour)
            info["hour_ganzhi"] = hour_ganzhi
            return info
        else:
            # 其他日期返回基础信息
            weekday_names = ['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日']
            return {
                "solar_date": dt.isoformat(),
                "weekday": weekday_names[dt.weekday()],
                "lunar_date": "需安装 lunar-python 库",
                "zodiac": "马" if (dt.year - 2026) % 12 == 0 else "待计算",
                "yi": ["待查询"],
                "ji": ["待查询"],
                "chong": "待查询",
                "sha": "待查询",
                "wuxing": "待查询",
                "zhishen": "待查询",
                "jianchu": "待查询",
                "tai_shen": "待查询",
                "pengzu": "待查询",
                "ji_shen": "待查询",
                "xiong_shen": "待查询",
                "ganzhi": "待查询",
                "nayin": "待查询",
                "hour_ganzhi": ""
            }
    
    @staticmethod
    def format(info):
        lines = [
            f"📅 {info['solar_date']} {info.get('weekday','')}",
            f"农历：{info['lunar_date']} (属{info.get('zodiac','')})",
            f"干支：{info.get('ganzhi','')} 纳音：{info.get('nayin','')} 时柱：{info.get('hour_ganzhi','')}",
            f"值神：{info.get('zhishen','')} 建除：{info.get('jianchu','')}",
            f"🌟 宜：{', '.join(info.get('yi',[]))}",
            f"🚫 忌：{', '.join(info.get('ji',[]))}",
            f"⚡ 冲煞：{info.get('chong','')} 煞{info.get('sha','')}",
            f"💧 五行：{info.get('wuxing','')}",
            f"👶 胎神：{info.get('tai_shen','')}",
            f"📜 彭祖百忌：{info.get('pengzu','')}",
        ]
        if info.get('ji_shen'):
            lines.append(f"✨ 吉神：{info['ji_shen']}")
        if info.get('xiong_shen'):
            lines.append(f"⚠️ 凶神：{info['xiong_shen']}")
        return "\n".join(lines)

# ==================== 模块6：历史记录管理 ====================
class HistoryManager:
    @staticmethod
    def init_db():
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            draw_time TEXT,
            strategy TEXT,
            user_numbers TEXT,
            draw_numbers TEXT,
            match_count INTEGER,
            prize_level TEXT,
            lottery_type TEXT,
            solar_date TEXT,
            lunar_date TEXT,
            ganzhi TEXT,
            nayin TEXT,
            zhishen TEXT,
            jianchu TEXT,
            main_hexagram TEXT,
            changing_hexagram TEXT,
            hour_ganzhi TEXT
        )''')
        conn.commit()
        conn.close()
    
    @staticmethod
    def get_recent(limit=10):
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute('''SELECT id, draw_time, strategy, user_numbers, draw_numbers, 
                     match_count, prize_level, solar_date, lunar_date, ganzhi, 
                     nayin, zhishen, jianchu, main_hexagram, changing_hexagram, hour_ganzhi, lottery_type 
                     FROM records ORDER BY id DESC LIMIT ?''', (limit,))
        rows = c.fetchall()
        conn.close()
        return rows
    
    @staticmethod
    def get_stats():
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute('SELECT COUNT(*) FROM records')
        total = c.fetchone()[0]
        c.execute('SELECT prize_level, COUNT(*) FROM records GROUP BY prize_level')
        level_counts = dict(c.fetchall())
        conn.close()
        return total, level_counts
    
    @staticmethod
    def add_custom_record(draw_datetime, draw_numbers, strategy="自定义", lottery_type="default"):
        """添加自定义历史记录"""
        if len(set(draw_numbers)) != 7 or any(n<1 or n>49 for n in draw_numbers):
            raise ValueError("开奖号码必须是7个1-49之间不重复的数字")
        
        draw_time_str = draw_datetime.strftime("%Y-%m-%d %H:%M:%S")
        solar_date = draw_datetime.strftime("%Y-%m-%d")
        
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        draw_str = ','.join(map(str, draw_numbers))
        c.execute('''INSERT INTO records (draw_time, strategy, user_numbers, draw_numbers, match_count, prize_level, solar_date, lunar_date, ganzhi, nayin, zhishen, jianchu, main_hexagram, changing_hexagram, hour_ganzhi, lottery_type)
                     VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                  (draw_time_str, strategy, "", draw_str, 0, "无", solar_date, "", "", "", "", "", "", "", "", lottery_type))
        conn.commit()
        conn.close()
    
    @staticmethod
    def batch_import_from_csv(csv_file, lottery_type="default", strategy="批量导入"):
        """
        从CSV文件批量导入历史记录（Streamlit版本）
        CSV格式：第一行为表头，之后每行为日期时间, 号码1, 号码2, ..., 号码7
        返回：(成功数, 失败数, 错误信息列表)
        """
        import csv
        from io import StringIO
        
        success_count = 0
        fail_count = 0
        errors = []
        
        try:
            # 如果是字符串，转为StringIO
            if isinstance(csv_file, str):
                csv_content = StringIO(csv_file)
            else:
                csv_content = StringIO(csv_file.getvalue().decode('utf-8-sig'))
            
            reader = csv.reader(csv_content)
            header = next(reader, None)  # 跳过表头
            
            for line_num, row in enumerate(reader, start=2):
                try:
                    if len(row) < 2:
                        errors.append(f"第{line_num}行：数据列数不足")
                        fail_count += 1
                        continue
                    
                    # 解析日期时间
                    datetime_str = row[0].strip()
                    try:
                        draw_dt = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
                    except:
                        try:
                            draw_dt = datetime.strptime(datetime_str, "%Y/%m/%d %H:%M:%S")
                        except:
                            try:
                                draw_dt = datetime.strptime(datetime_str.split()[0], "%Y-%m-%d")
                            except:
                                errors.append(f"第{line_num}行：日期格式错误 '{datetime_str}'")
                                fail_count += 1
                                continue
                    
                    # 解析号码
                    numbers = []
                    if len(row) >= 8:
                        numbers = []
                        for i in range(1, 8):
                            num_str = row[i].strip()
                            if num_str:
                                try:
                                    num = int(num_str)
                                    if 1 <= num <= 49:
                                        numbers.append(num)
                                except:
                                    pass
                    elif len(row) == 2:
                        num_str = row[1].strip()
                        if num_str.startswith('"') and num_str.endswith('"'):
                            num_str = num_str[1:-1]
                        numbers = [int(n) for n in num_str.replace(',', ' ').split() if n.strip().isdigit()]
                    
                    # 验证号码
                    if len(numbers) != 7:
                        errors.append(f"第{line_num}行：号码数量不正确（需要7个，实际{len(numbers)}个）")
                        fail_count += 1
                        continue
                    
                    if len(set(numbers)) != 7:
                        errors.append(f"第{line_num}行：号码有重复")
                        fail_count += 1
                        continue
                    
                    if any(n < 1 or n > 49 for n in numbers):
                        errors.append(f"第{line_num}行：号码超出范围（1-49）")
                        fail_count += 1
                        continue
                    
                    numbers.sort()
                    
                    # 获取彩票类型和策略（如果CSV中有提供）
                    csv_lottery_type = lottery_type
                    if len(row) > 8 and row[8].strip():
                        csv_lottery_type = row[8].strip()
                    
                    csv_strategy = strategy
                    if len(row) > 9 and row[9].strip():
                        csv_strategy = row[9].strip()
                    
                    # 添加到数据库
                    HistoryManager.add_custom_record(draw_dt, numbers, csv_strategy, csv_lottery_type)
                    success_count += 1
                    
                except Exception as e:
                    errors.append(f"第{line_num}行：处理失败 - {str(e)}")
                    fail_count += 1
            
            return success_count, fail_count, errors
            
        except Exception as e:
            return 0, 0, [f"文件读取失败：{str(e)}"]

# ==================== 模块7：古代术数预测（完全确定性） ====================
class AncientDivination:
    @staticmethod
    def meihua_yishu(dt, seed_str):
        nums = [dt.year, dt.month, dt.day, dt.hour, dt.minute]
        shang = (sum(nums[:3]) % 8) or 8
        xia = (sum(nums[3:]) % 8) or 8
        dong = (sum(nums) % 6) or 6
        
        gua_ranges = {
            1: list(range(1, 7)), 2: list(range(7, 13)), 3: list(range(13, 19)),
            4: list(range(19, 25)), 5: list(range(25, 31)), 6: list(range(31, 37)),
            7: list(range(37, 43)), 8: list(range(43, 50))
        }
        
        pool = list(set(gua_ranges[shang]) | set(gua_ranges[xia]))
        if len(pool) < 7:
            missing = [n for n in range(1, 50) if n not in pool]
            pool.extend(missing[:7-len(pool)])
        
        numbers = deterministic_sample(pool, 7, seed_str + "meihua")
        return numbers, f"梅花易数：以{dt.strftime('%Y-%m-%d %H:%M')}起卦，得上卦{shang}下卦{xia}"
    
    @staticmethod
    def zhouyi(dt, seed_str):
        seed = dt.strftime("%Y%m%d") + "_" + seed_str.split("_")[-1] if "_" in seed_str else dt.strftime("%Y%m%d")
        hash_val = deterministic_index(seed, 64)
        wuxing_list = ['金', '木', '水', '火', '土']
        wuxing = wuxing_list[deterministic_index(seed + "wuxing", 5)]
        
        wuxing_map = {
            '金': [1,2,9,10,17,18,25,26,33,34,41,42,49],
            '木': [3,4,11,12,19,20,27,28,35,36,43,44],
            '水': [5,6,13,14,21,22,29,30,37,38,45,46],
            '火': [7,8,15,16,23,24,31,32,39,40,47,48],
            '土': [49]
        }
        
        pool = wuxing_map[wuxing].copy()
        if len(pool) < 7:
            missing = [n for n in range(1, 50) if n not in pool]
            pool.extend(missing[:7-len(pool)])
        
        numbers = deterministic_sample(pool, 7, seed_str + "zhouyi")
        return numbers, f"周易：基于{dt.strftime('%Y-%m-%d')}得第{hash_val+1}卦，五行属{wuxing}"
    
    @staticmethod
    def qimen_dunjia(dt, seed_str):
        seed = seed_str + "qimen"
        yang_dun = dt.month <= 6
        
        jiuming = {1:'坎',2:'坤',3:'震',4:'巽',5:'中',6:'乾',7:'兑',8:'艮',9:'离'}
        zhi_fu = deterministic_index(seed + "fu", 9) + 1
        zhi_shi = deterministic_index(seed + "shi", 9) + 1
        
        pool = [zhi_fu, zhi_shi]
        candidates = [n for n in range(1, 50) if n not in pool]
        while len(pool) < 7:
            idx = deterministic_index(seed + str(len(pool)), len(candidates))
            pool.append(candidates.pop(idx))
        
        numbers = sorted(pool[:7])
        return numbers, f"奇门遁甲：{'阳遁' if yang_dun else '阴遁'}，值符{jiuming[zhi_fu]}值使{jiuming[zhi_shi]}"
    
    @staticmethod
    def ziwei_doushu(dt, seed_str):
        main_stars = ['紫微', '天机', '太阳', '武曲', '天同', '廉贞', '天府', 
                      '太阴', '贪狼', '巨门', '天相', '天梁', '七杀', '破军']
        
        seed = seed_str + "ziwei"
        indices = [deterministic_index(seed + str(i), len(main_stars)) for i in range(3)]
        selected = [main_stars[i] for i in indices]
        
        star_ranges = {
            '紫微': list(range(1,5)), '天机': list(range(5,9)), '太阳': list(range(9,13)),
            '武曲': list(range(13,17)), '天同': list(range(17,21)), '廉贞': list(range(21,25)),
            '天府': list(range(25,29)), '太阴': list(range(29,33)), '贪狼': list(range(33,37)),
            '巨门': list(range(37,41)), '天相': list(range(41,44)), '天梁': list(range(44,47)),
            '七杀': [47,48], '破军': [49]
        }
        
        pool = set()
        for star in selected:
            pool.update(star_ranges.get(star, []))
        pool = list(pool)
        
        if len(pool) < 7:
            missing = [n for n in range(1, 50) if n not in pool]
            pool.extend(missing[:7-len(pool)])
        
        numbers = deterministic_sample(pool, 7, seed_str + "ziwei_select")
        return numbers, f"紫微斗数：主星{','.join(selected)}"

# ==================== Streamlit 主界面 ====================
def main():
    st.title("🎲 彩票学习工具 - 完全确定性版")
    st.markdown("**声明：仅供编程学习与传统文化研究，严禁用于赌博**")
    st.markdown("---")
    
    # 初始化数据库
    HistoryManager.init_db()
    
    # 侧边栏 - 时间和彩票类型选择
    st.sidebar.header("⏰ 时间设置")
    
    # 日期选择
    selected_date = st.sidebar.date_input("选择日期", date.today())
    
    # 时间选择
    selected_hour = st.sidebar.slider("小时", 0, 23, datetime.now().hour)
    selected_minute = st.sidebar.slider("分钟", 0, 59, datetime.now().minute)
    
    # 构建完整的日期时间对象
    current_dt = datetime.combine(selected_date, datetime.min.time())
    current_dt = current_dt.replace(hour=selected_hour, minute=selected_minute)
    
    # 彩票类型选择
    st.sidebar.header("🎰 彩票类型")
    lottery_type_option = st.sidebar.radio(
        "选择彩票类型",
        ["默认", "自定义1", "自定义2", "自定义3", "自定义标识符"],
        index=0
    )
    
    if lottery_type_option == "默认":
        lottery_type = "default"
    elif lottery_type_option == "自定义标识符":
        lottery_type = st.sidebar.text_input("输入标识符", value="双色球")
    else:
        lottery_type = lottery_type_option.lower().replace("自定义", "custom")
    
    # 生成种子字符串（确定性核心：时间 + 彩票类型）
    seed_str = current_dt.strftime("%Y%m%d%H%M%S") + "_" + lottery_type
    
    st.sidebar.markdown(f"**当前时间：** {current_dt.strftime('%Y-%m-%d %H:%M')}")
    st.sidebar.markdown(f"**彩票类型：** {lottery_type}")
    st.sidebar.markdown(f"**种子：** `{seed_str}`")
    
    # 功能选项卡
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "🔢 平衡选号", "🎯 聪明组合", "📜 黄历查询", 
        "☯️ 易经起卦", "🔮 古代术数", "📊 历史记录", "📥 批量导入"
    ])
    
    # Tab 1: 平衡选号
    with tab1:
        st.header("平衡选号（确定性）")
        st.markdown("基于选定时间和彩票类型生成唯一确定的平衡号码组合")
        
        if st.button("生成平衡号码", key="balance_btn"):
            nums = BalanceFilter.generate_balanced(seed_str)
            year = current_dt.year
            
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("推荐号码")
                st.markdown(f"### {', '.join(map(str, nums))}")
            with col2:
                st.subheader("号码属性")
                st.text(NumberAttributes.format_number_list(nums, year))
            
            # 显示平衡条件
            st.markdown("---")
            st.markdown("**平衡条件验证：**")
            odd_cnt = sum(1 for n in nums if n % 2 == 1)
            small_cnt = sum(1 for n in nums if n <= 24)
            total = sum(nums)
            st.markdown(f"- 奇偶比：{odd_cnt}:{7-odd_cnt}")
            st.markdown(f"- 大小比：{7-small_cnt}:{small_cnt}")
            st.markdown(f"- 和值：{total}")
            st.info(f"💡 相同的时间({current_dt.strftime('%Y-%m-%d %H:%M')}) + 相同的彩票类型({lottery_type}) 将永远得到相同的预测结果")
    
    # Tab 2: 聪明组合
    with tab2:
        st.header("聪明组合（确定性）")
        st.markdown("输入候选号码池，生成确定性组合")
        
        pool_input = st.text_input("输入候选号码（用逗号或空格分隔，至少7个）", 
                                    value="5, 12, 18, 22, 33, 41, 45, 48, 3, 17, 29, 38")
        
        if st.button("生成聪明组合", key="wheel_btn"):
            try:
                pool = [int(x.strip()) for x in pool_input.replace(',', ' ').split() if x.strip()]
                if len(pool) < 7:
                    st.error("候选池不足7个号码！")
                else:
                    combos = WheelGenerator.generate(pool, 7, 4, seed_str)
                    year = current_dt.year
                    
                    for i, combo in enumerate(combos, 1):
                        st.markdown(f"**组合 {i}：** {', '.join(map(str, combo))}")
                        st.text(NumberAttributes.format_number_list(combo, year))
                        st.markdown("---")
            except Exception as e:
                st.error(f"输入错误：{e}")
    
    # Tab 3: 黄历查询
    with tab3:
        st.header("黄历查询")
        
        info = ChineseCalendar.get_daily_info(current_dt)
        st.text(ChineseCalendar.format(info))
    
    # Tab 4: 易经起卦
    with tab4:
        st.header("易经起卦")
        st.markdown("基于选定时间进行起卦")
        
        div_result = YijingDivination.divination_by_time(current_dt)
        
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("上卦")
            st.markdown(f"### {div_result['shang_gua']['name']} {div_result['shang_gua']['symbol']}")
            st.markdown(f"**含义：** {div_result['shang_gua']['meaning']}")
            st.markdown(f"**属性：** {div_result['shang_gua']['attr']}")
        
        with col2:
            st.subheader("下卦")
            st.markdown(f"### {div_result['xia_gua']['name']} {div_result['xia_gua']['symbol']}")
            st.markdown(f"**含义：** {div_result['xia_gua']['meaning']}")
            st.markdown(f"**属性：** {div_result['xia_gua']['attr']}")
        
        st.markdown("---")
        st.subheader(f"本卦：{div_result['ben_gua_name']}")
        st.markdown(f"**动爻：** 第 {div_result['dong_yao']} 爻")
        st.markdown(f"**起卦时间：** {div_result['time']}")
    
    # Tab 5: 古代术数预测
    with tab5:
        st.header("古代术数预测（完全确定性）")
        
        method = st.radio("选择预测方法", 
                          ["梅花易数", "周易", "奇门遁甲", "紫微斗数"],
                          horizontal=True)
        
        if st.button("开始预测", key="ancient_btn"):
            year = current_dt.year
            
            if method == "梅花易数":
                nums, reason = AncientDivination.meihua_yishu(current_dt, seed_str)
            elif method == "周易":
                nums, reason = AncientDivination.zhouyi(current_dt, seed_str)
            elif method == "奇门遁甲":
                nums, reason = AncientDivination.qimen_dunjia(current_dt, seed_str)
            else:  # 紫微斗数
                nums, reason = AncientDivination.ziwei_doushu(current_dt, seed_str)
            
            st.subheader("预测结果")
            st.markdown(f"### {', '.join(map(str, nums))}")
            st.text(NumberAttributes.format_number_list(nums, year))
            st.markdown(f"**推理依据：** {reason}")
            st.info(f"💡 相同的时间({current_dt.strftime('%Y-%m-%d %H:%M')}) + 相同的彩票类型({lottery_type}) 将永远得到相同的预测结果")
    
    # Tab 6: 历史记录
    with tab6:
        st.header("历史记录")
        
        # 统计信息
        total, level_counts = HistoryManager.get_stats()
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("总记录数", total)
        with col2:
            st.metric("中奖次数", sum(level_counts.get(l, 0) for l in ["一等奖","二等奖","三等奖","四等奖","五等奖","六等奖"]))
        with col3:
            st.metric("未中奖次数", level_counts.get("未中奖", 0))
        
        st.markdown("---")
        
        # 最近记录
        st.subheader("最近10期记录")
        rows = HistoryManager.get_recent(10)
        
        if rows:
            for row in rows:
                (rid, draw_time, strategy, user_str, draw_str, 
                 match_cnt, prize, solar, lunar, ganzhi, nayin, 
                 zhishen, jianchu, main_hex, changing_hex, hour_ganzhi, lottery_type_row) = row
                
                with st.expander(f"期号 {rid} - {draw_time} ({lottery_type_row})"):
                    st.markdown(f"**策略：** {strategy}")
                    if user_str:
                        st.markdown(f"**投注号码：** {user_str}")
                    st.markdown(f"**开奖号码：** {draw_str}")
                    if match_cnt is not None:
                        st.markdown(f"**命中：** {match_cnt} 个 → {prize}")
                    if lunar:
                        st.markdown(f"**农历：** {lunar}")
        else:
            st.info("暂无历史记录")
    
    # Tab 7: 批量导入
    with tab7:
        st.header("📥 批量导入历史记录（CSV）")
        st.markdown("""
        **CSV文件格式要求：**
        - 第一行为表头（会被跳过）
        - 每行格式：日期时间, 号码1, 号码2, 号码3, 号码4, 号码5, 号码6, 号码7
        - 日期时间格式：YYYY-MM-DD HH:MM:SS 或 YYYY/MM/DD HH:MM:SS 或 YYYY-MM-DD
        - 可选列：彩票类型, 策略（在第8、9列）
        
        **示例：**
        ```
        日期时间,号码1,号码2,号码3,号码4,号码5,号码6,号码7,彩票类型,策略
        2026-04-20 20:30:00,5,12,18,22,33,41,45,双色球,官方开奖
        2026-04-21 21:00:00,3,8,15,26,37,42,49,default,测试数据
        ```
        """)
        
        # 文件上传
        uploaded_file = st.file_uploader("选择CSV文件", type=['csv'], key="csv_uploader")
        
        # 导入设置
        col1, col2 = st.columns(2)
        with col1:
            import_lottery_type = st.text_input("彩票类型（默认）", value="default", key="import_lottery_type")
        with col2:
            import_strategy = st.text_input("策略名称（默认）", value="批量导入", key="import_strategy")
        
        # 导入按钮
        if st.button("开始导入", key="import_btn"):
            if uploaded_file is not None:
                with st.spinner("正在导入..."):
                    success, fail, errors = HistoryManager.batch_import_from_csv(
                        uploaded_file, 
                        import_lottery_type, 
                        import_strategy
                    )
                
                # 显示结果
                st.success(f"导入完成！成功: {success} 条，失败: {fail} 条")
                
                if errors:
                    with st.expander("查看错误详情", expanded=True):
                        for err in errors[:20]:  # 显示前20条错误
                            st.error(err)
                        if len(errors) > 20:
                            st.warning(f"还有 {len(errors)-20} 条错误未显示")
            else:
                st.warning("请先选择CSV文件")
        
        st.markdown("---")
        st.markdown("💡 **提示：** 导入的记录将用于达尔文预测和智能预测员的学习分析")
    
    # 底部说明
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #888;">
        📌 本工具为完全确定性版本<br>
        同一时间 + 同一彩票类型 → 完全相同的结果<br>
        不同彩票类型 → 结果不同<br>
        声明：仅供编程学习与传统文化研究，严禁用于赌博
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
