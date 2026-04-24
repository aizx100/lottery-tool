"""
彩票学习工具 - 完全确定性版（支持彩票类型）
特点：同一时间 + 同一彩票类型 → 完全相同的结果；不同彩票类型 → 结果不同。
声明：仅供编程学习与传统文化研究，严禁用于赌博。
"""

import sqlite3
from datetime import datetime, date
import itertools
import hashlib
import re
from collections import Counter, defaultdict

DB_FILE = "lottery_history.db"

# ==================== 辅助函数 ====================
def deterministic_index(seed_str, max_val):
    """根据种子字符串返回0到max_val-1之间的确定性整数"""
    hash_val = int(hashlib.md5(seed_str.encode()).hexdigest(), 16)
    return hash_val % max_val

def get_all_balanced_combinations():
    """预计算所有符合平衡条件的组合（缓存）"""
    if not hasattr(get_all_balanced_combinations, 'cache'):
        from itertools import combinations
        all_nums = range(1, 50)
        cache = []
        for combo in combinations(all_nums, 7):
            if BalanceFilter.is_balanced(list(combo)):
                cache.append(sorted(combo))
        get_all_balanced_combinations.cache = cache
    return get_all_balanced_combinations.cache

def get_lottery_type():
    """交互式获取彩票类型，返回字符串标识"""
    print("\n请选择彩票类型：")
    print("1. 默认")
    print("2. 自定义1")
    print("3. 自定义2")
    print("4. 自定义3")
    print("5. 手动输入标识符")
    opt = input("请选择(1-5): ")
    if opt == '1':
        return "default"
    elif opt == '2':
        return "custom1"
    elif opt == '3':
        return "custom2"
    elif opt == '4':
        return "custom3"
    elif opt == '5':
        return input("请输入标识符（如：双色球、大乐透等）: ").strip() or "manual"
    else:
        return "default"

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
    dz = dizhi[dz_index]
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
    return f"{tg}{dz}"

# ==================== 模块1：平衡选号 ====================
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
        all_combos = get_all_balanced_combinations()
        if not all_combos:
            return list(range(1, 8))
        idx = deterministic_index(seed_str, len(all_combos))
        return all_combos[idx]

# ==================== 模块2：聪明组合 ====================
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
    def _get_hexagram_name(upper, lower):
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
            "ben_gua_name": YijingDivination._get_hexagram_name(shang, xia),
            "dong_yao": dong,
            "bian_gua_name": "需根据动爻计算",
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
            return {
                "solar_date": dt.isoformat(),
                "lunar_date": "需安装 lunar-python",
                "ganzhi": "",
                "nayin": "",
                "zhishen": "",
                "jianchu": "",
                "wuxing": "",
                "hour_ganzhi": ""
            }
    
    @staticmethod
    def format(info):
        lines = [
            f"\n📅 {info['solar_date']} {info.get('weekday','')}",
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
        lines.append("="*40)
        return "\n".join(lines)

# ==================== 模块6：历史记录管理（增加彩票类型字段） ====================
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
            lottery_type TEXT
        )''')
        conn.commit()
        
        new_columns = [
            'solar_date TEXT', 'lunar_date TEXT', 'ganzhi TEXT', 'nayin TEXT',
            'zhishen TEXT', 'jianchu TEXT', 'main_hexagram TEXT',
            'changing_hexagram TEXT', 'hour_ganzhi TEXT'
        ]
        for col_def in new_columns:
            col_name = col_def.split()[0]
            try:
                c.execute(f"ALTER TABLE records ADD COLUMN {col_def}")
            except sqlite3.OperationalError:
                pass
        
        try:
            c.execute("ALTER TABLE records ADD COLUMN lottery_type TEXT")
        except sqlite3.OperationalError:
            pass
        conn.commit()
        conn.close()
    
    @staticmethod
    def save_record(strategy, user_nums, draw_nums, match_count, prize_level, draw_datetime=None, lottery_type="default"):
        if draw_datetime is None:
            draw_datetime = datetime.now()
        draw_time_str = draw_datetime.strftime("%Y-%m-%d %H:%M:%S")
        solar_date = draw_datetime.strftime("%Y-%m-%d")
        cal_info = ChineseCalendar.get_daily_info(draw_datetime)
        lunar_date = cal_info.get('lunar_date', '')
        ganzhi = cal_info.get('ganzhi', '')
        nayin = cal_info.get('nayin', '')
        zhishen = cal_info.get('zhishen', '')
        jianchu = cal_info.get('jianchu', '')
        hour_ganzhi = cal_info.get('hour_ganzhi', '')
        div = YijingDivination.divination_by_time(draw_datetime)
        main_hexagram = div['ben_gua_name']
        changing_hexagram = div['bian_gua_name']
        
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        user_str = ','.join(map(str, user_nums))
        draw_str = ','.join(map(str, draw_nums))
        c.execute('''INSERT INTO records (draw_time, strategy, user_numbers, draw_numbers, match_count, prize_level, solar_date, lunar_date, ganzhi, nayin, zhishen, jianchu, main_hexagram, changing_hexagram, hour_ganzhi, lottery_type)
                     VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                  (draw_time_str, strategy, user_str, draw_str, match_count, prize_level, solar_date, lunar_date, ganzhi, nayin, zhishen, jianchu, main_hexagram, changing_hexagram, hour_ganzhi, lottery_type))
        conn.commit()
        conn.close()
    
    @staticmethod
    def add_custom_record(draw_datetime, draw_numbers, strategy="自定义", lottery_type="default"):
        if len(set(draw_numbers)) != 7 or any(n<1 or n>49 for n in draw_numbers):
            raise ValueError("开奖号码必须是7个1-49之间不重复的数字")
        user_nums = []
        match_count = 0
        prize_level = "无"
        draw_time_str = draw_datetime.strftime("%Y-%m-%d %H:%M:%S")
        solar_date = draw_datetime.strftime("%Y-%m-%d")
        cal_info = ChineseCalendar.get_daily_info(draw_datetime)
        lunar_date = cal_info.get('lunar_date', '')
        ganzhi = cal_info.get('ganzhi', '')
        nayin = cal_info.get('nayin', '')
        zhishen = cal_info.get('zhishen', '')
        jianchu = cal_info.get('jianchu', '')
        hour_ganzhi = cal_info.get('hour_ganzhi', '')
        div = YijingDivination.divination_by_time(draw_datetime)
        main_hexagram = div['ben_gua_name']
        changing_hexagram = div['bian_gua_name']
        
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        user_str = ','.join(map(str, user_nums)) if user_nums else ""
        draw_str = ','.join(map(str, draw_numbers))
        c.execute('''INSERT INTO records (draw_time, strategy, user_numbers, draw_numbers, match_count, prize_level, solar_date, lunar_date, ganzhi, nayin, zhishen, jianchu, main_hexagram, changing_hexagram, hour_ganzhi, lottery_type)
                     VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                  (draw_time_str, strategy, user_str, draw_str, match_count, prize_level, solar_date, lunar_date, ganzhi, nayin, zhishen, jianchu, main_hexagram, changing_hexagram, hour_ganzhi, lottery_type))
        conn.commit()
        conn.close()
    
    @staticmethod
    def get_recent(limit=10):
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute('''SELECT id, draw_time, strategy, user_numbers, draw_numbers, match_count, prize_level, solar_date, lunar_date, ganzhi, nayin, zhishen, jianchu, main_hexagram, changing_hexagram, hour_ganzhi, lottery_type FROM records ORDER BY id DESC LIMIT ?''', (limit,))
        rows = c.fetchall()
        conn.close()
        return rows
    
    @staticmethod
    def get_all_records():
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT strategy, user_numbers, draw_numbers, lottery_type FROM records WHERE user_numbers != ''")
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
    def format_record(row):
        (rid, draw_time, strategy, user_str, draw_str, match_cnt, prize, solar, lunar, ganzhi, nayin, zhishen, jianchu, main_hex, changing_hex, hour_ganzhi, lottery_type) = row
        user_nums = list(map(int, user_str.split(','))) if user_str else []
        draw_nums = list(map(int, draw_str.split(',')))
        try:
            draw_year = int(draw_time.split('-')[0]) if draw_time else datetime.now().year
        except:
            draw_year = datetime.now().year
        lines = [
            f"\n【期号 {rid}】开奖时间：{draw_time}",
            f"阳历：{solar} 农历：{lunar}",
            f"四柱八字：{ganzhi} {hour_ganzhi}",
            f"纳音：{nayin} 值神：{zhishen} 建除：{jianchu}",
            f"主卦：{main_hex} 变卦：{changing_hex}",
            f"策略：{strategy} 彩票类型：{lottery_type}",
        ]
        if user_nums:
            lines.append(f"投注号码：{NumberAttributes.format_number_list(user_nums, draw_year)}")
        lines.append(f"开奖号码：{NumberAttributes.format_number_list(draw_nums, draw_year)}")
        if user_nums:
            lines.append(f"命中个数：{match_cnt} 奖级：{prize}")
        else:
            lines.append("（自定义记录，无投注信息）")
        lines.append("-"*40)
        return "\n".join(lines)


    @staticmethod
    def batch_import_from_csv(csv_file_path, lottery_type="default", strategy="批量导入"):
        """
        从CSV文件批量导入历史记录
        CSV格式要求：
        - 第一行为表头（会被跳过）
        - 列顺序：日期时间(YYYY-MM-DD HH:MM:SS), 号码1, 号码2, 号码3, 号码4, 号码5, 号码6, 号码7
        - 或者：日期时间, "号码1 号码2 号码3 号码4 号码5 号码6 号码7"（空格分隔）
        - 可选列：彩票类型, 策略（如有则使用，否则使用默认值）
        返回：(成功数, 失败数, 错误信息列表)
        """
        import csv
        success_count = 0
        fail_count = 0
        errors = []
        
        try:
            with open(csv_file_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.reader(f)
                header = next(reader, None)  # 跳过表头
                
                for line_num, row in enumerate(reader, start=2):  # 从第2行开始（第1行是表头）
                    try:
                        if len(row) < 2:  # 至少需要日期时间和号码
                            errors.append(f"第{line_num}行：数据列数不足")
                            fail_count += 1
                            continue
                        
                        # 解析日期时间
                        datetime_str = row[0].strip()
                        try:
                            draw_dt = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
                        except:
                            # 尝试其他格式
                            try:
                                draw_dt = datetime.strptime(datetime_str, "%Y/%m/%d %H:%M:%S")
                            except:
                                try:
                                    draw_dt = datetime.strptime(datetime_str.split()[0], "%Y-%m-%d")
                                except:
                                    errors.append(f"第{line_num}行：日期格式错误 '{datetime_str}'")
                                    fail_count += 1
                                    continue
                        
                        # 解析号码（支持多种格式）
                        numbers = []
                        if len(row) >= 8:
                            # 格式1：日期时间, 号码1, 号码2, ... 号码7
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
                            # 格式2：日期时间, "号码1 号码2 ... 号码7"
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
                        
                        # 获取彩票类型（如果CSV中有提供）
                        csv_lottery_type = lottery_type
                        if len(row) > 8 and row[8].strip():
                            csv_lottery_type = row[8].strip()
                        
                        # 获取策略名称（如果CSV中有提供）
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
            
        except FileNotFoundError:
            return 0, 0, [f"文件不存在：{csv_file_path}"]
        except Exception as e:
            return 0, 0, [f"文件读取失败：{str(e)}"]
# ==================== 模块7：达尔文预测 ====================
class DarwinPrediction:
    @staticmethod
    def get_number_attrs(num):
        attrs = NumberAttributes.get_full_attrs(num)
        return {
            'zodiac': attrs['zodiac'],
            'wuxing': attrs['wuxing'],
            'bagua': attrs['bagua'],
            'size': '大' if num >= 25 else '小',
            'parity': '奇' if num % 2 else '偶',
            'head': num // 10,
            'tail': num % 10
        }
    
    @staticmethod
    def get_group_attrs(numbers):
        attrs_list = [DarwinPrediction.get_number_attrs(n) for n in numbers]
        odd_cnt = sum(1 for a in attrs_list if a['parity'] == '奇')
        even_cnt = 7 - odd_cnt
        small_cnt = sum(1 for a in attrs_list if a['size'] == '小')
        large_cnt = 7 - small_cnt
        zodiac_cnt = Counter(a['zodiac'] for a in attrs_list)
        wuxing_cnt = Counter(a['wuxing'] for a in attrs_list)
        bagua_cnt = Counter(a['bagua'] for a in attrs_list)
        head_cnt = Counter(a['head'] for a in attrs_list)
        tail_cnt = Counter(a['tail'] for a in attrs_list)
        total_sum = sum(numbers)
        return {
            'odd_even': (odd_cnt, even_cnt),
            'size': (small_cnt, large_cnt),
            'zodiac': zodiac_cnt,
            'wuxing': wuxing_cnt,
            'bagua': bagua_cnt,
            'head': head_cnt,
            'tail': tail_cnt,
            'sum': total_sum
        }
    
    @staticmethod
    def similarity(attrs1, attrs2):
        score = 0
        if attrs1['odd_even'] == attrs2['odd_even']:
            score += 10
        if attrs1['size'] == attrs2['size']:
            score += 10
        sum_diff = abs(attrs1['sum'] - attrs2['sum'])
        score += max(0, 30 - sum_diff)
        zodiac_overlap = sum((attrs1['zodiac'] & attrs2['zodiac']).values())
        score += zodiac_overlap * 2
        wuxing_overlap = sum((attrs1['wuxing'] & attrs2['wuxing']).values())
        score += wuxing_overlap * 2
        bagua_overlap = sum((attrs1['bagua'] & attrs2['bagua']).values())
        score += bagua_overlap * 2
        head_overlap = sum((attrs1['head'] & attrs2['head']).values())
        tail_overlap = sum((attrs1['tail'] & attrs2['tail']).values())
        score += head_overlap + tail_overlap
        return score
    
    @staticmethod
    def get_history_records(limit=50, lottery_type="default"):
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT user_numbers, draw_numbers FROM records WHERE user_numbers != '' AND lottery_type=? ORDER BY id DESC LIMIT ?", (lottery_type, limit))
        rows = c.fetchall()
        conn.close()
        history = []
        for user_str, draw_str in rows:
            if not user_str:
                continue
            user_nums = list(map(int, user_str.split(',')))
            draw_nums = list(map(int, draw_str.split(',')))
            history.append({
                'user': user_nums,
                'draw': draw_nums,
                'user_attrs': DarwinPrediction.get_group_attrs(user_nums),
                'draw_attrs': DarwinPrediction.get_group_attrs(draw_nums)
            })
        return history
    
    @staticmethod
    def predict(current_numbers, seed_str=""):
        lottery_type = seed_str.split("_")[-1] if "_" in seed_str else "default"
        current_attrs = DarwinPrediction.get_group_attrs(current_numbers)
        history = DarwinPrediction.get_history_records(100, lottery_type)
        if len(history) < 3:
            return BalanceFilter.generate_balanced(seed_str), ["历史记录不足，使用平衡选号"]
        
        sim_list = [(DarwinPrediction.similarity(current_attrs, rec['user_attrs']), rec) for rec in history]
        sim_list.sort(key=lambda x: x[0], reverse=True)
        most_similar = sim_list[:3]
        least_similar = sim_list[-3:]
        
        next_attrs_counter = defaultdict(Counter)
        for _, rec in most_similar:
            for num in rec['draw']:
                attrs = DarwinPrediction.get_number_attrs(num)
                for key, val in attrs.items():
                    next_attrs_counter[key][val] += 1
        
        diff_next_attrs_counter = defaultdict(Counter)
        for _, rec in least_similar:
            for num in rec['draw']:
                attrs = DarwinPrediction.get_number_attrs(num)
                for key, val in attrs.items():
                    diff_next_attrs_counter[key][val] += 1
        
        combined = defaultdict(Counter)
        for key in next_attrs_counter:
            for val, cnt in next_attrs_counter[key].items():
                combined[key][val] = cnt * 0.6
        for key in diff_next_attrs_counter:
            for val, cnt in diff_next_attrs_counter[key].items():
                combined[key][val] = combined[key].get(val, 0) + cnt * 0.4
        
        scores = {}
        for num in range(1, 50):
            attrs = DarwinPrediction.get_number_attrs(num)
            score = 0
            for key, val in attrs.items():
                score += combined[key].get(val, 0)
            scores[num] = score
        
        top_numbers = sorted(scores, key=scores.get, reverse=True)[:7]
        return top_numbers, ["基于同中求异/异中求同分析", f"参考了{len(history)}期历史记录"]
    
    @staticmethod
    def query_prediction(current_numbers=None, seed_str=""):
        if current_numbers is None:
            print("\n--- 达尔文预测查询 ---")
            print("1. 使用最近一期开奖号码")
            print("2. 手动输入7个号码")
            choice = input("选择(1/2): ")
            if choice == '1':
                lottery_type = seed_str.split("_")[-1] if "_" in seed_str else "default"
                conn = sqlite3.connect(DB_FILE)
                c = conn.cursor()
                c.execute("SELECT draw_numbers FROM records WHERE draw_numbers != '' AND lottery_type=? ORDER BY id DESC LIMIT 1", (lottery_type,))
                row = c.fetchone()
                conn.close()
                if row:
                    current = list(map(int, row[0].split(',')))
                else:
                    print("无历史记录")
                    return
            else:
                try:
                    nums = list(map(int, input("输入7个数字: ").split()))
                    if len(set(nums)) != 7 or any(n<1 or n>49 for n in nums):
                        print("无效")
                        return
                    current = sorted(nums)
                except:
                    print("错误")
                    return
        else:
            current = current_numbers
        recommended, reasons = DarwinPrediction.predict(current, seed_str)
        print("\n【预测结果】下一期推荐号码：")
        print(NumberAttributes.format_number_list(recommended, datetime.now().year))
        print("推理依据：")
        for r in reasons:
            print(f" - {r}")

# ==================== 模块8：古代术数预测（支持彩票类型） ====================
class AncientDivination:
    @staticmethod
    def _get_datetime_from_user():
        print("\n请选择时间来源：")
        print("1. 使用当前电脑时间")
        print("2. 手动输入时间（年-月-日 时:分）")
        opt = input("请选择(1/2): ")
        if opt == '2':
            try:
                date_str = input("请输入日期（格式 YYYY-MM-DD）：")
                time_str = input("请输入时间（格式 HH:MM，24小时制）：")
                dt = datetime.strptime(f"{date_str} {time_str}:00", "%Y-%m-%d %H:%M:%S")
                return dt
            except Exception as e:
                print(f"输入无效，将使用当前时间。错误：{e}")
                return datetime.now()
        else:
            return datetime.now()
    
    @staticmethod
    def meihua_yishu(dt, seed_str):
        nums = [dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second]
        shang = (sum(nums[:3]) % 8) or 8
        xia = (sum(nums[3:6]) % 8) or 8
        dong = (sum(nums) % 6) or 6
        gua_ranges = {
            1: list(range(1, 7)),
            2: list(range(7, 13)),
            3: list(range(13, 19)),
            4: list(range(19, 25)),
            5: list(range(25, 31)),
            6: list(range(31, 37)),
            7: list(range(37, 43)),
            8: list(range(43, 50))
        }
        pool = set(gua_ranges[shang]) | set(gua_ranges[xia])
        if len(pool) < 7:
            missing = [n for n in range(1,50) if n not in pool]
            needed = 7 - len(pool)
            missing_sorted = sorted(missing, key=lambda x: deterministic_index(seed_str + str(x), len(missing)))
            pool.update(missing_sorted[:needed])
        
        pool_list = sorted(pool)
        if len(pool_list) > 7:
            idx = deterministic_index(seed_str + "select", len(pool_list))
            if idx + 7 <= len(pool_list):
                numbers = pool_list[idx:idx+7]
            else:
                numbers = pool_list[idx:] + pool_list[:7 - (len(pool_list)-idx)]
        else:
            numbers = pool_list
        numbers.sort()
        return numbers, f"梅花易数：以指定时间{dt.strftime('%Y-%m-%d %H:%M:%S')}起卦，得本卦{shang}{xia}，动爻{dong}，取卦象数字范围生成。"
    
    @staticmethod
    def zhouyi(dt, seed_str):
        seed = dt.strftime("%Y%m%d") + "_" + seed_str.split("_")[-1] if "_" in seed_str else dt.strftime("%Y%m%d")
        hash_val = deterministic_index(seed, 64)
        gua_index = hash_val + 1
        wuxing_list = ['金','木','水','火','土']
        wuxing = wuxing_list[deterministic_index(seed + "wuxing", 5)]
        wuxing_map = {
            '金': [1,2,9,10,17,18,25,26,33,34,41,42,49],
            '木': [3,4,11,12,19,20,27,28,35,36,43,44],
            '水': [5,6,13,14,21,22,29,30,37,38,45,46],
            '火': [7,8,15,16,23,24,31,32,39,40,47,48],
            '土': [49]
        }
        pool = wuxing_map[wuxing]
        if len(pool) < 7:
            missing = [n for n in range(1,50) if n not in pool]
            needed = 7 - len(pool)
            missing_sorted = sorted(missing, key=lambda x: deterministic_index(seed_str + "zhouyi" + str(x), len(missing)))
            pool.extend(missing_sorted[:needed])
        pool = sorted(set(pool))
        if len(pool) > 7:
            idx = deterministic_index(seed_str + "select_zhouyi", len(pool))
            if idx + 7 <= len(pool):
                numbers = pool[idx:idx+7]
            else:
                numbers = pool[idx:] + pool[:7 - (len(pool)-idx)]
        else:
            numbers = pool
        numbers.sort()
        return numbers, f"周易预测：基于时间{dt.strftime('%Y-%m-%d')}（哈希{hash_val}）得第{gua_index}卦，卦属{wuxing}行，取相应数字池生成。"
    
    @staticmethod
    def qimen_dunjia(dt, seed_str):
        hour = dt.hour
        shichen = (hour + 1) // 2 if hour % 2 == 1 else hour // 2
        shichen = shichen % 12 if shichen % 12 != 0 else 12
        yang_dun = dt.month <= 6
        jiuming = {1:'坎',2:'坤',3:'震',4:'巽',5:'中',6:'乾',7:'兑',8:'艮',9:'离'}
        seed = seed_str + "qimen"
        zhi_fu = deterministic_index(seed + "fu", 9) + 1
        zhi_shi = deterministic_index(seed + "shi", 9) + 1
        base_nums = [zhi_fu, zhi_shi]
        pool = set(base_nums)
        candidates = [n for n in range(1,50) if n not in pool]
        needed = 20 - len(pool)
        for i in range(needed):
            idx = deterministic_index(seed + str(i), len(candidates))
            pool.add(candidates[idx])
            candidates.pop(idx)
        pool_list = sorted(pool)
        if len(pool_list) > 7:
            idx = deterministic_index(seed + "select", len(pool_list))
            if idx + 7 <= len(pool_list):
                numbers = pool_list[idx:idx+7]
            else:
                numbers = pool_list[idx:] + pool_list[:7 - (len(pool_list)-idx)]
        else:
            numbers = pool_list
        numbers.sort()
        return numbers, f"奇门遁甲：基于时间{dt.strftime('%Y-%m-%d %H:%M:%S')}，时辰{shichen}时，{'阳遁' if yang_dun else '阴遁'}，值符星{jiuming[zhi_fu]}，值使门{jiuming[zhi_shi]}，取星门数字生成。"
    
    @staticmethod
    def ziwei_doushu(dt, seed_str):
        main_stars = ['紫微', '天机', '太阳', '武曲', '天同', '廉贞', '天府', '太阴', '贪狼', '巨门', '天相', '天梁', '七杀', '破军']
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
        if len(pool) < 7:
            missing = [n for n in range(1,50) if n not in pool]
            needed = 7 - len(pool)
            missing_sorted = sorted(missing, key=lambda x: deterministic_index(seed + str(x), len(missing)))
            pool.update(missing_sorted[:needed])
        pool_list = sorted(pool)
        if len(pool_list) > 7:
            idx = deterministic_index(seed + "select", len(pool_list))
            if idx + 7 <= len(pool_list):
                numbers = pool_list[idx:idx+7]
            else:
                numbers = pool_list[idx:] + pool_list[:7 - (len(pool_list)-idx)]
        else:
            numbers = pool_list
        numbers.sort()
        stars_str = ','.join(selected)
        return numbers, f"紫微斗数：模拟时间{dt.strftime('%Y-%m-%d %H:%M:%S')}命盘，主星{stars_str}，取对应数字区间生成。"
    
    @staticmethod
    def random_prediction(dt, seed_str):
        methods = [
            ("梅花易数", AncientDivination.meihua_yishu),
            ("周易", AncientDivination.zhouyi),
            ("奇门遁甲", AncientDivination.qimen_dunjia),
            ("紫微斗数", AncientDivination.ziwei_doushu)
        ]
        idx = deterministic_index(seed_str + "random", len(methods))
        name, func = methods[idx]
        numbers, reason = func(dt, seed_str + name)
        return numbers, name, reason
    
    @staticmethod
    def interactive():
        print("\n--- 古代术数预测（模拟版）---")
        print("请选择预测方法：")
        print("1. 梅花易数")
        print("2. 周易")
        print("3. 奇门遁甲")
        print("4. 紫微斗数")
        print("5. 随机一种")
        choice = input("请选择(1-5): ")
        dt = AncientDivination._get_datetime_from_user()
        lottery_type = get_lottery_type()
        seed_str = dt.strftime("%Y%m%d%H%M%S") + "_" + lottery_type
        if choice == '1':
            nums, reason = AncientDivination.meihua_yishu(dt, seed_str)
            method = "梅花易数"
        elif choice == '2':
            nums, reason = AncientDivination.zhouyi(dt, seed_str)
            method = "周易"
        elif choice == '3':
            nums, reason = AncientDivination.qimen_dunjia(dt, seed_str)
            method = "奇门遁甲"
        elif choice == '4':
            nums, reason = AncientDivination.ziwei_doushu(dt, seed_str)
            method = "紫微斗数"
        else:
            nums, method, reason = AncientDivination.random_prediction(dt, seed_str)
        current_year = dt.year
        formatted_nums = NumberAttributes.format_number_list(nums, current_year)
        print(f"\n【{method}预测结果】")
        print(f"推荐号码：{formatted_nums}")
        print(f"推理依据：{reason}")
        print("（注：本预测仅为编程模拟，不具实际效力）")

# ==================== 模块9：智能预测员 ====================
class SmartPredictor:
    STRATEGIES = {
        "平衡选号": lambda seed: BalanceFilter.generate_balanced(seed),
        "梅花易数": lambda seed: AncientDivination.meihua_yishu(datetime.now(), seed)[0],
        "周易": lambda seed: AncientDivination.zhouyi(datetime.now(), seed)[0],
        "奇门遁甲": lambda seed: AncientDivination.qimen_dunjia(datetime.now(), seed)[0],
        "紫微斗数": lambda seed: AncientDivination.ziwei_doushu(datetime.now(), seed)[0],
    }
    
    custom_preferences = {
        "prefer_zodiac": [],
        "prefer_wuxing": [],
        "prefer_bagua": [],
        "exclude_numbers": [],
        "prefer_size": None,
        "prefer_parity": None
    }
    
    @classmethod
    def update_preferences(cls):
        print("\n--- 设置智能预测员自定义偏好 ---")
        print("当前偏好：")
        print(f" 偏好生肖: {cls.custom_preferences['prefer_zodiac'] or '无'}")
        print(f" 偏好五行: {cls.custom_preferences['prefer_wuxing'] or '无'}")
        print(f" 偏好八卦: {cls.custom_preferences['prefer_bagua'] or '无'}")
        print(f" 排除数字: {cls.custom_preferences['exclude_numbers'] or '无'}")
        print(f" 大小偏好: {cls.custom_preferences['prefer_size'] or '无'}")
        print(f" 奇偶偏好: {cls.custom_preferences['prefer_parity'] or '无'}")
        print("\n请输入要修改的项目（数字）：")
        print("1. 偏好生肖（如 鼠,牛,虎 等）")
        print("2. 偏好五行（如 金,木,水,火,土）")
        print("3. 偏好八卦（如 乾,兑,离 等）")
        print("4. 排除数字（如 1,2,3）")
        print("5. 大小偏好（大/小）")
        print("6. 奇偶偏好（奇/偶）")
        print("0. 返回")
        opt = input("请选择: ")
        if opt == '1':
            val = input("输入偏好的生肖，用逗号分隔（例如：马,龙,猴）: ")
            cls.custom_preferences['prefer_zodiac'] = [v.strip() for v in val.split(',') if v.strip()]
        elif opt == '2':
            val = input("输入偏好的五行，用逗号分隔（例如：金,水）: ")
            cls.custom_preferences['prefer_wuxing'] = [v.strip() for v in val.split(',') if v.strip()]
        elif opt == '3':
            val = input("输入偏好的八卦，用逗号分隔（例如：乾,坤）: ")
            cls.custom_preferences['prefer_bagua'] = [v.strip() for v in val.split(',') if v.strip()]
        elif opt == '4':
            val = input("输入要排除的数字，用逗号分隔（例如：7,13,25）: ")
            cls.custom_preferences['exclude_numbers'] = [int(v.strip()) for v in val.split(',') if v.strip().isdigit()]
        elif opt == '5':
            val = input("输入大小偏好（大 或 小）: ")
            if val in ['大','小']:
                cls.custom_preferences['prefer_size'] = val
        elif opt == '6':
            val = input("输入奇偶偏好（奇 或 偶）: ")
            if val in ['奇','偶']:
                cls.custom_preferences['prefer_parity'] = val
        print("偏好已更新。")
    
    @classmethod
    def compute_strategy_weights(cls, lottery_type="default"):
        records = HistoryManager.get_all_records()
        strategy_hits = defaultdict(list)
        for strategy, user_str, draw_str, rec_type in records:
            if not user_str or rec_type != lottery_type:
                continue
            user_nums = set(map(int, user_str.split(',')))
            draw_nums = set(map(int, draw_str.split(',')))
            hit = len(user_nums & draw_nums)
            strategy_hits[strategy].append(hit)
        weights = {}
        for strat in cls.STRATEGIES:
            if strat in strategy_hits and strategy_hits[strat]:
                avg_hit = sum(strategy_hits[strat]) / len(strategy_hits[strat])
                weight = max(0.5, avg_hit / 7.0 * 3)
            else:
                weight = 1.0
            weights[strat] = weight
        return weights
    
    @classmethod
    def apply_preferences(cls, number):
        year = datetime.now().year
        attrs = NumberAttributes.get_full_attrs(number, year)
        if number in cls.custom_preferences['exclude_numbers']:
            return False
        if cls.custom_preferences['prefer_zodiac'] and attrs['zodiac'] not in cls.custom_preferences['prefer_zodiac']:
            return False
        if cls.custom_preferences['prefer_wuxing'] and attrs['wuxing'] not in cls.custom_preferences['prefer_wuxing']:
            return False
        if cls.custom_preferences['prefer_bagua'] and attrs['bagua'] not in cls.custom_preferences['prefer_bagua']:
            return False
        if cls.custom_preferences['prefer_size']:
            size = '大' if number >= 25 else '小'
            if size != cls.custom_preferences['prefer_size']:
                return False
        if cls.custom_preferences['prefer_parity']:
            parity = '奇' if number % 2 else '偶'
            if parity != cls.custom_preferences['prefer_parity']:
                return False
        return True
    
    @classmethod
    def predict(cls, dt=None):
        if dt is None:
            dt = datetime.now()
        lottery_type = get_lottery_type()
        seed_str = dt.strftime("%Y%m%d%H%M%S") + "_" + lottery_type
        print(f"\n【智能预测员】使用时间种子 '{seed_str}' 进行确定性预测...")
        weights = cls.compute_strategy_weights(lottery_type)
        print("各策略当前权重（基于历史表现）：")
        for strat, w in sorted(weights.items(), key=lambda x: -x[1]):
            print(f" {strat}: {w:.2f}")
        
        all_recommendations = []
        for strat_name, func in cls.STRATEGIES.items():
            try:
                nums = func(seed_str + strat_name)
                all_recommendations.append((strat_name, nums, weights[strat_name]))
            except Exception as e:
                print(f"策略 {strat_name} 执行失败: {e}")
                continue
        
        score_counter = defaultdict(float)
        for strat_name, nums, weight in all_recommendations:
            for num in nums:
                score_counter[num] += weight
        
        for num in range(1, 50):
            if not cls.apply_preferences(num):
                score_counter[num] *= 0.1
            else:
                score_counter[num] *= 1.2
        
        sorted_nums = sorted(score_counter.items(), key=lambda x: -x[1])
        top_nums = [num for num, score in sorted_nums if score > 0]
        if len(top_nums) < 7:
            missing = [n for n in range(1,50) if n not in top_nums]
            top_nums.extend(missing[:7-len(top_nums)])
        final_numbers = sorted(top_nums[:7])
        print("\n【智能预测员综合结果】")
        print(f"最终推荐号码：{NumberAttributes.format_number_list(final_numbers, dt.year)}")
        print(f"使用时间：{dt.strftime('%Y-%m-%d %H:%M:%S')} 彩票类型：{lottery_type}")
        print("\n各策略推荐详情：")
        for strat_name, nums, weight in all_recommendations:
            print(f" {strat_name} (权重{weight:.2f}) : {sorted(nums)}")
        print("\n自定义偏好过滤已应用。")
        return final_numbers

# ==================== 公用辅助函数 ====================
def generate_random_numbers(seed_str=""):
    return list(range(1, 8))

def check_match(user, draw):
    return len(set(user) & set(draw))

def prize_level(match_count):
    if match_count == 7:
        return "一等奖"
    elif match_count == 6:
        return "二等奖"
    elif match_count == 5:
        return "三等奖"
    elif match_count == 4:
        return "四等奖"
    elif match_count == 3:
        return "五等奖"
    elif match_count == 2:
        return "六等奖"
    else:
        return "未中奖"

# ==================== 模块10：自然语言智能助手 ====================
class SmartAssistant:
    @staticmethod
    def parse_and_execute(text):
        text = text.strip()
        if not text:
            print("请说点什么...")
            return
        if re.search(r'帮助|help|怎么用|指令', text, re.I):
            print("""
【智能助手支持指令】
- 预测 / 达尔文预测 / 帮我预测下一期号码 → 达尔文预测
- 平衡选号 / 生成平衡号码 → 生成一组平衡号码
- 聪明组合 [数字列表] → 例如：聪明组合 5 12 18 22 33 41 45 48
- 模拟开奖 [策略] → 策略可选：平衡/聪明/随机，例如：模拟开奖 平衡
- 历史 / 历史记录 → 查看最近10期记录
- 统计 / 统计信息 → 查看总期数和奖级分布
- 起卦 / 易经起卦 → 时间起卦
- 黄历 / 今日黄历 → 查询今日黄历
- 属性 [数字] → 例如：属性 7
- 梅花易数 / 周易 / 奇门遁甲 / 紫微斗数 → 调用相应术数预测
- 智能预测 / 综合预测 → 调用智能预测员（需指定时间）
- 设置偏好 → 设置智能预测员的自定义偏好
- 自定义记录 日期时间 号码 → 例如：自定义记录 2026-04-19 20:30 1 2 3 4 5 6 7
- 帮助 / help → 显示本帮助
""")
            return
        if re.search(r'智能预测|综合预测', text):
            print("\n请选择预测时间：")
            print("1. 使用当前时间")
            print("2. 手动输入时间")
            opt = input("请选择(1/2): ")
            if opt == '2':
                try:
                    date_str = input("请输入日期（YYYY-MM-DD）：")
                    time_str = input("请输入时间（HH:MM）：")
                    dt = datetime.strptime(f"{date_str} {time_str}:00", "%Y-%m-%d %H:%M:%S")
                except:
                    print("输入无效，使用当前时间")
                    dt = datetime.now()
            else:
                dt = datetime.now()
            SmartPredictor.predict(dt)
            return
        if re.search(r'设置偏好', text):
            SmartPredictor.update_preferences()
            return
        if re.search(r'预测|达尔文|帮我预测', text):
            lottery_type = get_lottery_type()
            seed_str = datetime.now().strftime("%Y%m%d%H%M%S") + "_" + lottery_type
            DarwinPrediction.query_prediction(seed_str=seed_str)
            return
        if re.search(r'平衡选号|生成平衡号码', text):
            lottery_type = get_lottery_type()
            seed_str = datetime.now().strftime("%Y%m%d%H%M%S") + "_" + lottery_type
            nums = BalanceFilter.generate_balanced(seed_str)
            print(f"平衡号码: {NumberAttributes.format_number_list(nums, datetime.now().year)}")
            return
        if re.search(r'聪明组合', text):
            numbers = re.findall(r'\d+', text)
            if len(numbers) >= 7:
                pool = list(map(int, numbers))
                lottery_type = get_lottery_type()
                seed_str = datetime.now().strftime("%Y%m%d%H%M%S") + "_" + lottery_type
                wheel = WheelGenerator.generate(pool, 7, 4, seed_str=seed_str)
                print(f"从 {len(pool)} 个候选号中生成了 {len(wheel)} 注聪明组合：")
                for i, w in enumerate(wheel, 1):
                    print(f" 注{i}: {NumberAttributes.format_number_list(w, datetime.now().year)}")
            else:
                print("请提供至少7个候选号码，例如：聪明组合 5 12 18 22 33 41 45 48")
            return
        if re.search(r'模拟开奖', text):
            if '平衡' in text:
                strat_key = '平衡'
            elif '聪明' in text:
                strat_key = '聪明'
            else:
                strat_key = '随机'
            draw = generate_random_numbers()
            print(f"开奖号码: {NumberAttributes.format_number_list(draw, datetime.now().year)}")
            lottery_type = get_lottery_type()
            seed_str = datetime.now().strftime("%Y%m%d%H%M%S") + "_" + lottery_type
            if strat_key == '平衡':
                user = BalanceFilter.generate_balanced(seed_str)
                strat = "平衡选号"
            elif strat_key == '聪明':
                print("请先输入候选号码池（空格分隔）:")
                try:
                    pool = list(map(int, input().split()))
                    if len(pool) >= 7:
                        wheel = WheelGenerator.generate(pool, 7, 4, seed_str=seed_str)
                        user = wheel[0] if wheel else generate_random_numbers()
                        strat = f"聪明组合(候选池{len(pool)}个)"
                    else:
                        user = generate_random_numbers()
                        strat = "随机(候选池不足)"
                except:
                    user = generate_random_numbers()
                    strat = "随机(输入错误)"
            else:
                user = generate_random_numbers()
                strat = "纯随机"
            print(f"测试号码: {NumberAttributes.format_number_list(user, datetime.now().year)}")
            match_cnt = check_match(user, draw)
            prize = prize_level(match_cnt)
            print(f"匹配个数: {match_cnt} -> {prize}")
            HistoryManager.save_record(strat, user, draw, match_cnt, prize, datetime.now(), lottery_type)
            print("记录已保存。")
            return
        if re.search(r'历史记录|历史$', text):
            rows = HistoryManager.get_recent(10)
            if not rows:
                print("暂无记录。")
            else:
                print("\n最近10期记录：")
                for row in rows:
                    print(HistoryManager.format_record(row))
            return
        if re.search(r'统计信息|统计$', text):
            total, level_counts = HistoryManager.get_stats()
            print(f"\n总记录期数: {total}")
            print("各奖级次数:")
            for level, cnt in level_counts.items():
                print(f" {level}: {cnt}")
            return
        if re.search(r'起卦|易经起卦', text):
            res = YijingDivination.divination_by_time()
            print(f"起卦时间：{res['time']}")
            print(f"上卦：{res['shang_gua']['name']}{res['shang_gua']['symbol']} 下卦：{res['xia_gua']['name']}{res['xia_gua']['symbol']}")
            print(f"本卦：{res['ben_gua_name']} 动爻：第{res['dong_yao']}爻")
            return
        if re.search(r'黄历|今日黄历', text):
            info = ChineseCalendar.get_daily_info(datetime.now())
            print(ChineseCalendar.format(info))
            return
        if re.search(r'属性\s*(\d+)', text):
            match = re.search(r'属性\s*(\d+)', text)
            num = int(match.group(1))
            if 1 <= num <= 49:
                year_str = input("请输入年份（直接回车使用当前年份）: ").strip()
                year = int(year_str) if year_str else datetime.now().year
                attrs = NumberAttributes.get_full_attrs(num, year)
                print(f"\n数字 {num} 在 {year} 年的属性：")
                print(f" 生肖：{attrs['zodiac']}")
                print(f" 五行：{attrs['wuxing']}")
                print(f" 八卦：{attrs['bagua']} {attrs['symbol']}")
            else:
                print("数字超出范围")
            return
        if re.search(r'梅花易数', text):
            dt = datetime.now()
            lottery_type = get_lottery_type()
            seed_str = dt.strftime("%Y%m%d%H%M%S") + "_" + lottery_type
            nums, reason = AncientDivination.meihua_yishu(dt, seed_str)
            print(f"\n【梅花易数预测结果】\n推荐号码：{NumberAttributes.format_number_list(nums, dt.year)}\n推理依据：{reason}")
            return
        if re.search(r'周易(?!.*起卦)', text):
            dt = datetime.now()
            lottery_type = get_lottery_type()
            seed_str = dt.strftime("%Y%m%d%H%M%S") + "_" + lottery_type
            nums, reason = AncientDivination.zhouyi(dt, seed_str)
            print(f"\n【周易预测结果】\n推荐号码：{NumberAttributes.format_number_list(nums, dt.year)}\n推理依据：{reason}")
            return
        if re.search(r'奇门遁甲', text):
            dt = datetime.now()
            lottery_type = get_lottery_type()
            seed_str = dt.strftime("%Y%m%d%H%M%S") + "_" + lottery_type
            nums, reason = AncientDivination.qimen_dunjia(dt, seed_str)
            print(f"\n【奇门遁甲预测结果】\n推荐号码：{NumberAttributes.format_number_list(nums, dt.year)}\n推理依据：{reason}")
            return
        if re.search(r'紫微斗数', text):
            dt = datetime.now()
            lottery_type = get_lottery_type()
            seed_str = dt.strftime("%Y%m%d%H%M%S") + "_" + lottery_type
            nums, reason = AncientDivination.ziwei_doushu(dt, seed_str)
            print(f"\n【紫微斗数预测结果】\n推荐号码：{NumberAttributes.format_number_list(nums, dt.year)}\n推理依据：{reason}")
            return
        match = re.search(r'自定义记录\s+(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2}:\d{2})\s+([\d\s]+)', text)
        if match:
            date_str, time_str, nums_str = match.groups()
            try:
                dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M:%S")
                draw_nums = list(map(int, nums_str.split()))
                if len(draw_nums) != 7:
                    print("需要7个号码")
                    return
                lottery_type = get_lottery_type()
                HistoryManager.add_custom_record(dt, draw_nums, "自定义", lottery_type)
                print("自定义记录已添加。")
            except Exception as e:
                print(f"添加失败: {e}")
            return
        print("抱歉，我没听懂。输入'帮助'查看支持的指令。")

# ==================== 主程序 ====================
def main():
    HistoryManager.init_db()
    print("=" * 60)
    print("彩票学习工具 - 完全确定性版（支持彩票类型）")
    print("声明：本程序仅供个人编程学习与传统文化研究，严禁用于赌博。")
    print("=" * 60)
    while True:
        print("\n【主菜单】")
        print("1. 生成平衡号码")
        print("2. 聪明组合")
        print("3. 模拟开奖")
        print("4. 自定义添加记录")
        print("5. 查看历史记录")
        print("6. 查看统计信息")
        print("7. 易经起卦")
        print("8. 黄历查询")
        print("9. 号码属性查询")
        print("10. 达尔文预测")
        print("11. 古代术数预测（梅花/周易/奇门/紫微）")
        print("12. 智能助手（自然语言指令）")
        print("13. 智能预测员（学习所有技巧，可指定时间）")
        print("14. 批量导入历史记录（CSV）")
        print("0. 退出")
        choice = input("请选择(0-14): ")
        current_year = datetime.now().year
        if choice == '1':
            lottery_type = get_lottery_type()
            seed_str = datetime.now().strftime("%Y%m%d%H%M%S") + "_" + lottery_type
            nums = BalanceFilter.generate_balanced(seed_str)
            print(f"平衡号码: {NumberAttributes.format_number_list(nums, current_year)}")
            print(f"种子：{seed_str}")
        elif choice == '2':
            try:
                pool = list(map(int, input("输入候选号码池（空格分隔，至少7个）: ").split()))
                if len(pool) < 7:
                    print("候选池不足7个号码！")
                    continue
                lottery_type = get_lottery_type()
                seed_str = datetime.now().strftime("%Y%m%d%H%M%S") + "_" + lottery_type
                wheel = WheelGenerator.generate(pool, pick=7, guarantee=4, seed_str=seed_str)
                print(f"生成了 {len(wheel)} 注聪明组合：")
                for i, w in enumerate(wheel, 1):
                    print(f" 注{i}: {NumberAttributes.format_number_list(w, current_year)}")
            except Exception as e:
                print(f"输入错误: {e}")
        elif choice == '3':
            print("选择策略：a.平衡选号 b.聪明组合 c.纯随机")
            sub = input("请输入(a/b/c): ").lower()
            draw = list(range(1,8))
            print(f"开奖号码: {NumberAttributes.format_number_list(draw, current_year)}")
            lottery_type = get_lottery_type()
            seed_str = datetime.now().strftime("%Y%m%d%H%M%S") + "_" + lottery_type
            if sub == 'a':
                user = BalanceFilter.generate_balanced(seed_str)
                strat = "平衡选号"
            elif sub == 'b':
                pool = list(map(int, input("输入候选号码池: ").split()))
                if len(pool) >= 7:
                    wheel = WheelGenerator.generate(pool, 7, 4, seed_str=seed_str)
                    user = wheel[0] if wheel else list(range(1,8))
                    strat = f"聪明组合(候选池{len(pool)}个)"
                else:
                    user = list(range(1,8))
                    strat = "随机(候选池不足)"
            else:
                user = list(range(1,8))
                strat = "纯随机"
            print(f"测试号码: {NumberAttributes.format_number_list(user, current_year)}")
            match_cnt = check_match(user, draw)
            prize = prize_level(match_cnt)
            print(f"匹配个数: {match_cnt} -> {prize}")
            HistoryManager.save_record(strat, user, draw, match_cnt, prize, datetime.now(), lottery_type)
            print("记录已保存。")
        elif choice == '4':
            print("\n--- 自定义添加历史记录 ---")
            try:
                date_str = input("开奖日期和时间（格式 YYYY-MM-DD HH:MM:SS）: ").strip()
                if not date_str:
                    draw_dt = datetime.now()
                else:
                    draw_dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
                nums_str = input("开奖号码（7个数字，空格分隔）: ")
                draw_nums = list(map(int, nums_str.split()))
                if len(draw_nums) != 7 or len(set(draw_nums)) != 7 or any(n<1 or n>49 for n in draw_nums):
                    print("号码无效")
                    continue
                draw_nums.sort()
                strategy = input("策略名称（回车为'自定义'）: ").strip()
                if not strategy:
                    strategy = "自定义"
                lottery_type = get_lottery_type()
                HistoryManager.add_custom_record(draw_dt, draw_nums, strategy, lottery_type)
                print("自定义记录已添加。")
            except Exception as e:
                print(f"错误: {e}")
        elif choice == '5':
            rows = HistoryManager.get_recent(10)
            if not rows:
                print("暂无记录。")
            else:
                print("\n最近10期记录：")
                for row in rows:
                    print(HistoryManager.format_record(row))
        elif choice == '6':
            total, level_counts = HistoryManager.get_stats()
            print(f"\n总记录期数: {total}")
            print("各奖级次数:")
            for level, cnt in level_counts.items():
                print(f" {level}: {cnt}")
        elif choice == '7':
            print("\n--- 易经起卦 ---")
            print("1. 电脑自动起卦")
            print("2. 时间起卦（当前时间）")
            sub = input("选择(1/2): ")
            if sub == '1':
                lottery_type = get_lottery_type()
                seed = datetime.now().strftime("%Y%m%d%H%M%S") + "_" + lottery_type
                shang = deterministic_index(seed+"shang", 8)+1
                xia = deterministic_index(seed+"xia", 8)+1
                dong = deterministic_index(seed+"dong", 6)+1
                shang_gua = YijingDivination.BA_GUA[shang]
                xia_gua = YijingDivination.BA_GUA[xia]
                ben_name = YijingDivination._get_hexagram_name(shang, xia)
                print(f"上卦：{shang_gua['name']}{shang_gua['symbol']} 下卦：{xia_gua['name']}{xia_gua['symbol']}")
                print(f"本卦：{ben_name} 动爻：第{dong}爻")
            else:
                res = YijingDivination.divination_by_time()
                print(f"起卦时间：{res['time']}")
                print(f"上卦：{res['shang_gua']['name']}{res['shang_gua']['symbol']} 下卦：{res['xia_gua']['name']}{res['xia_gua']['symbol']}")
                print(f"本卦：{res['ben_gua_name']} 动爻：第{res['dong_yao']}爻")
        elif choice == '8':
            print("\n--- 黄历查询 ---")
            date_str = input("请输入日期(YYYY-MM-DD)，直接回车查询今日: ").strip()
            if date_str:
                try:
                    dt = date.fromisoformat(date_str)
                except:
                    print("格式错误，使用今日")
                    dt = date.today()
            else:
                dt = date.today()
            info = ChineseCalendar.get_daily_info(dt)
            print(ChineseCalendar.format(info))
        elif choice == '9':
            try:
                num = int(input("请输入1-49之间的数字: "))
                if 1 <= num <= 49:
                    year_str = input("请输入年份（直接回车使用当前年份）: ").strip()
                    year = int(year_str) if year_str else current_year
                    attrs = NumberAttributes.get_full_attrs(num, year)
                    print(f"\n数字 {num} 在 {year} 年的属性：")
                    print(f" 生肖：{attrs['zodiac']}")
                    print(f" 五行：{attrs['wuxing']}")
                    print(f" 八卦：{attrs['bagua']} {attrs['symbol']}")
                else:
                    print("数字超出范围！")
            except:
                print("输入无效")
        elif choice == '10':
            lottery_type = get_lottery_type()
            seed_str = datetime.now().strftime("%Y%m%d%H%M%S") + "_" + lottery_type
            DarwinPrediction.query_prediction(seed_str=seed_str)
        elif choice == '11':
            AncientDivination.interactive()
        elif choice == '12':
            print("\n【智能助手】请输入自然语言指令（输入'帮助'查看示例）")
            cmd = input(">>> ")
            SmartAssistant.parse_and_execute(cmd)
        elif choice == '13':
            print("\n请选择预测时间：")
            print("1. 使用当前时间")
            print("2. 手动输入时间")
            opt = input("请选择(1/2): ")
            if opt == '2':
                try:
                    date_str = input("请输入日期（YYYY-MM-DD）：")
                    time_str = input("请输入时间（HH:MM）：")
                    dt = datetime.strptime(f"{date_str} {time_str}:00", "%Y-%m-%d %H:%M:%S")
                except:
                    print("输入无效，使用当前时间")
                    dt = datetime.now()
            else:
                dt = datetime.now()
            SmartPredictor.predict(dt)
        elif choice == '14':
            print("\n--- 批量导入历史记录（CSV） ---")
            csv_file = input("请输入CSV文件路径: ").strip()
            if not csv_file:
                print("文件路径不能为空")
                continue
            print("\n请选择彩票类型：")
            print("1. 默认（default）")
            print("2. 自定义输入")
            type_opt = input("请选择(1/2): ")
            if type_opt == '2':
                lottery_type = input("请输入彩票类型标识符: ").strip() or "default"
            else:
                lottery_type = "default"
            strategy_name = input("请输入策略名称（回车默认为'批量导入'）: ").strip()
            if not strategy_name:
                strategy_name = "批量导入"
            print(f"\n正在导入文件: {csv_file}")
            print(f"彩票类型: {lottery_type}")
            print(f"策略名称: {strategy_name}")
            success, fail, errors = HistoryManager.batch_import_from_csv(csv_file, lottery_type, strategy_name)
            print(f"\n导入完成！")
            print(f"成功: {success} 条")
            print(f"失败: {fail} 条")
            if errors:
                print("\n错误详情：")
                for err in errors[:10]:  # 只显示前10条错误
                    print(f"  - {err}")
                if len(errors) > 10:
                    print(f"  ... 还有 {len(errors)-10} 条错误未显示")
        elif choice == '0':
            print("感谢学习，再见！")
            break
        else:
            print("无效选项")

if __name__ == "__main__":
    main()

