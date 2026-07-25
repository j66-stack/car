import traceback
import cv2
import numpy as np
import re
import threading
from ocrutil import getcn
from db_unit import handle_plate_data, get_parking_vehicles, get_longest_parking_vehicle
from config import *
#日志记录
def log_error(msg):
    with open("error.log", "a", encoding="utf-8") as f:
        f.write(msg + "\n")


longest_parking_info = None
plate_text = "暂无车牌"
db_tip = ""

PROVINCES = [
    "京", "津", "沪", "渝",
    "冀", "晋", "辽", "吉", "黑",
    "苏", "浙", "皖", "闽", "赣", "鲁",
    "豫", "鄂", "湘", "粤", "琼",
    "川", "贵", "云", "藏",
    "陕", "甘", "青", "宁", "新",
    "蒙", "桂", "台"
]

#省份选择器配置
PROVINCE_ITEM_HEIGHT = 28      #每个省份的高度
PROVINCE_VISIBLE_ITEMS = 5     #一次显示多少个省份

#车牌正则表达式和校验函数
PLATE_PATTERN = re.compile(r'^[\u4e00-\u9fa5][A-Z][A-Z0-9]{5,6}$')


def is_valid_plate(plate_text):
    #校验车牌是否有效
    if not plate_text or plate_text == "暂无车牌":
        return False
    plate_clean = plate_text.strip()
    return bool(PLATE_PATTERN.match(plate_clean))

pygame.init()
screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))
pygame.display.set_caption("智能停车场车牌识别计费系统")
clock = pygame.time.Clock()

#摄像头
cap = None
camera_open = False
current_frame = None

#手动录入变量
manual_input = ""
manual_province = "湘"
manual_active = False
manual_result = ""
manual_result_timer = 0
province_selector_open = False
province_selected_index = 0

#按钮区域定义
btn_y_base = CAMERA_H + 30
btn_open = pygame.Rect(20, btn_y_base, 160, 42)
btn_close = pygame.Rect(200, btn_y_base, 160, 42)
btn_recognize = pygame.Rect(380, btn_y_base, 180, 42)
btn_income = pygame.Rect(580, btn_y_base, 140, 42)

#车辆数据
vehicle_data = []
remaining_spaces = total_spaces


def load_vehicle_data():
    global vehicle_data, remaining_spaces, longest_parking_info
    vehicles, in_park_count = get_parking_vehicles(5)
    vehicle_data = vehicles
    remaining_spaces = total_spaces - in_park_count
    longest_parking_info = get_longest_parking_vehicle()


def draw_status_bar():
    #绘制顶部状态栏
    title = font_title.render("智能停车场车牌识别计费系统", True, DARK_BLUE)
    screen.blit(title, (CAMERA_W + (PANEL_W - title.get_width()) // 2, 20))

    pygame.draw.line(screen, BORDER_COLOR,
                     (CAMERA_W + 20, 60),
                     (WINDOW_W - 20, 60), 2)

    info_y = 80
    total_text = font_big.render(f"共有车位：{total_spaces}", True, DARK_GRAY)
    screen.blit(total_text, (CAMERA_W + 40, info_y))

    remaining_text = font_big.render(
        f"剩余车位：{remaining_spaces}",
        True, GREEN if remaining_spaces > 10 else ORANGE
    )
    screen.blit(remaining_text, (CAMERA_W + 260, info_y))

    pygame.draw.line(screen, BORDER_COLOR,
                     (CAMERA_W + 20, 115),
                     (WINDOW_W - 20, 115), 1)


def draw_vehicle_table():
    #绘制车辆信息表格
    table_x = CAMERA_W + 30
    table_y = 135
    table_w = PANEL_W - 60
    row_h = 35
    header_h = 35

    data_count = len(vehicle_data) if vehicle_data else 1
    table_height = header_h + data_count * row_h

    pygame.draw.rect(screen, WHITE, (table_x, table_y, table_w, table_height), border_radius=5)
    pygame.draw.rect(screen, BORDER_COLOR, (table_x, table_y, table_w, table_height), width=1, border_radius=5)

    #表头
    header_rect = pygame.Rect(table_x, table_y, table_w, header_h)
    pygame.draw.rect(screen, TABLE_HEADER, header_rect, border_radius=5)
    col1_x = table_x + 30
    col2_x = table_x + table_w // 2 + 20
    header1 = font_big.render("车牌号", True, WHITE)
    header2 = font_big.render("入场时间", True, WHITE)
    screen.blit(header1, (col1_x, table_y + 8))
    screen.blit(header2, (col2_x, table_y + 8))

    #表格数据
    display_data = vehicle_data if vehicle_data else [{"plate": "暂无数据", "time": "--"}]
    for i, data in enumerate(display_data):
        row_y = table_y + header_h + i * row_h
        if i % 2 == 0:
            pygame.draw.rect(screen, TABLE_ROW1, (table_x, row_y, table_w, row_h))
        else:
            pygame.draw.rect(screen, TABLE_ROW2, (table_x, row_y, table_w, row_h))
        pygame.draw.line(screen, BORDER_COLOR,
                         (table_x, row_y + row_h),
                         (table_x + table_w, row_y + row_h), 1)

        plate_display = data["plate"] if data["plate"] else "未知"
        time_display = data["time"] if data["time"] else "--"
        plate_text_small = font_small.render(plate_display, True, BLACK)
        time_text = font_small.render(time_display, True, DARK_GRAY)
        screen.blit(plate_text_small, (col1_x, row_y + 8))
        screen.blit(time_text, (col2_x, row_y + 8))


def draw_province_selector(area_x, area_y, area_w):
    global manual_province, province_selector_open, province_selected_index
    #省份选择按钮
    selector_x = area_x + 10
    selector_y = area_y + 25
    selector_w = 42
    selector_h = 32

    pygame.draw.rect(screen, WHITE, (selector_x, selector_y, selector_w, selector_h))
    pygame.draw.rect(screen, BLUE if manual_active else BORDER_COLOR,
                     (selector_x, selector_y, selector_w, selector_h), width=2, border_radius=3)

    #省份简称文字位置
    province_render = font_text.render(manual_province, True, BLACK)
    screen.blit(province_render, (selector_x + (selector_w - province_render.get_width()) // 2 - 5, selector_y + 5))

    #下拉箭头
    arrow_text = font_small.render("▼", True, DARK_GRAY)
    screen.blit(arrow_text, (selector_x + selector_w - 16, selector_y + 9))

    #默认返回值（选择器未打开时）
    result = (selector_x, selector_y, selector_w, selector_h,
              None, None, None, None,
              None, None, None, None,
              False)

    if province_selector_open:
        item_h = PROVINCE_ITEM_HEIGHT
        visible_items = PROVINCE_VISIBLE_ITEMS
        #列表位置
        list_x = selector_x - 5
        list_y = selector_y + selector_h + 2
        list_w = 80
        total_items = len(PROVINCES)
        display_items = min(total_items, visible_items)
        list_h = display_items * item_h + 4
        pygame.draw.rect(screen, WHITE, (list_x, list_y, list_w, list_h))
        pygame.draw.rect(screen, BORDER_COLOR, (list_x, list_y, list_w, list_h), width=1, border_radius=3)

        #计算滚动偏移
        scroll_offset = 0
        if province_selected_index >= visible_items:
            scroll_offset = province_selected_index - visible_items + 1
        if scroll_offset > total_items - visible_items:
            scroll_offset = total_items - visible_items

        #绘制省份列表
        for i in range(display_items):
            idx = i + scroll_offset
            if idx >= total_items:
                break

            item_rect = pygame.Rect(list_x + 2, list_y + 2 + i * item_h, list_w - 4, item_h - 2)
            if idx == province_selected_index:
                pygame.draw.rect(screen, BLUE, item_rect, border_radius=2)

            prov = PROVINCES[idx]
            color = WHITE if idx == province_selected_index else BLACK
            prov_render = font_text.render(prov, True, color)
            screen.blit(prov_render, (item_rect.x + (item_rect.w - prov_render.get_width()) // 2,
                                      item_rect.y + 2))

        #绘制滚动条
        has_scrollbar = total_items > visible_items
        scrollbar_x = list_x + list_w + 2 if has_scrollbar else None
        scrollbar_y = list_y if has_scrollbar else None
        scrollbar_w = 8 if has_scrollbar else 0
        scrollbar_h = list_h if has_scrollbar else 0

        if has_scrollbar:
            pygame.draw.rect(screen, LIGHT_GRAY, (scrollbar_x, scrollbar_y, scrollbar_w, scrollbar_h), border_radius=3)
            thumb_ratio = visible_items / total_items
            thumb_height = max(16, int(scrollbar_h * thumb_ratio))
            thumb_pos = (scroll_offset / (total_items - visible_items)) * (scrollbar_h - thumb_height)
            thumb_rect = pygame.Rect(scrollbar_x, scrollbar_y + thumb_pos, scrollbar_w, thumb_height)
            pygame.draw.rect(screen, BLUE, thumb_rect, border_radius=3)

        result = (selector_x, selector_y, selector_w, selector_h,
                  list_x, list_y, list_w, list_h,
                  scrollbar_x, scrollbar_y, scrollbar_w, scrollbar_h,
                  has_scrollbar)

    return result


def draw_manual_input_area():
    global manual_input, manual_active, manual_result

    area_x = CAMERA_W + 30
    area_y = 135 + 35 + 35 * 5 + 15
    area_w = PANEL_W - 60
    area_h = 75
    pygame.draw.rect(screen, WHITE, (area_x, area_y, area_w, area_h), border_radius=5)
    pygame.draw.rect(screen, BORDER_COLOR, (area_x, area_y, area_w, area_h), width=1, border_radius=5)
    label = font_small.render("手动录入车牌：", True, DARK_GRAY)
    screen.blit(label, (area_x + 10, area_y + 5))

    #省份选择器
    result = draw_province_selector(area_x, area_y, area_w)
    (selector_x, selector_y, selector_w, selector_h,
     list_x, list_y, list_w, list_h,
     scrollbar_x, scrollbar_y, scrollbar_w, scrollbar_h,
     has_scrollbar) = result

    #输入框
    input_x = selector_x + selector_w + 4
    input_y = area_y + 25
    input_w = area_w - 20 - selector_w - 10 - 100 - 8
    input_h = 32
    border_color = BLUE if manual_active else BORDER_COLOR
    pygame.draw.rect(screen, WHITE, (input_x, input_y, input_w, input_h))
    pygame.draw.rect(screen, border_color, (input_x, input_y, input_w, input_h), width=2, border_radius=3)
    display_text = manual_input
    if manual_active and pygame.time.get_ticks() % 1000 < 500:
        display_text += "|"
    input_render = font_text.render(display_text, True, BLACK)
    screen.blit(input_render, (input_x + 5, input_y + 5))

    #录入按钮
    btn_x = input_x + input_w + 10
    btn_y = input_y
    btn_w = 90
    btn_h = input_h
    btn_rect = pygame.Rect(btn_x, btn_y, btn_w, btn_h)
    pygame.draw.rect(screen, GREEN, btn_rect, border_radius=5)
    btn_text = font_btn.render("手动录入", True, WHITE)
    screen.blit(btn_text, (btn_x + 15, btn_y + 6))

    if manual_result:
        result_color = GREEN if "" in manual_result or "已录入" in manual_result or "离场" in manual_result else ORANGE
        if "⚠️" in manual_result or "失败" in manual_result:
            result_color = RED
        result_render = font_small.render(manual_result, True, result_color)
        screen.blit(result_render, (area_x + 10, area_y + area_h - 22))

    return (btn_rect, input_x, input_y, input_w, input_h,
            selector_x, selector_y, selector_w, selector_h,
            list_x, list_y, list_w, list_h,
            scrollbar_x, scrollbar_y, scrollbar_w, scrollbar_h,
            has_scrollbar)


def draw_longest_parking_info():
    global longest_parking_info

    if not longest_parking_info:
        return

    info_y = WINDOW_H - 135
    info_x = CAMERA_W + 30
    info_w = PANEL_W - 60

    title_text = f"在库最久：{longest_parking_info['plate']}"
    title_render = font_big.render(title_text, True, DARK_BLUE)
    screen.blit(title_render, (info_x, info_y))

    box_y = info_y + 28
    box_h = 65
    box_w = info_w
    box_x = info_x

    pygame.draw.rect(screen, GREEN, (box_x, box_y, box_w, box_h), width=2, border_radius=4)
    time_label = font_text.render(f"入库时间：{longest_parking_info['enter_time']}", True, DARK_GRAY)
    screen.blit(time_label, (box_x + 15, box_y + 8))
    duration_text = f"已停时长：{longest_parking_info['duration']}"
    duration_render = font_text.render(duration_text, True, DARK_GRAY)
    screen.blit(duration_render, (box_x + 15, box_y + 35))


def draw_camera_frame():
    cam_rect = pygame.Rect(0, 0, CAMERA_W, CAMERA_H)
    pygame.draw.rect(screen, BLACK, cam_rect)
    pygame.draw.rect(screen, BORDER_COLOR, cam_rect, width=2)

    if not camera_open:
        hint_text = font_text.render("请点击「打开摄像头」", True, WHITE)
        screen.blit(hint_text, (CAMERA_W // 2 - 120, CAMERA_H // 2 - 15))
        hint2 = font_tip.render("摄像头未开启", True, (150, 150, 150))
        screen.blit(hint2, (CAMERA_W // 2 - 70, CAMERA_H // 2 + 30))


def draw_result_panel():
    panel_x = 20
    panel_y = CAMERA_H + 90
    panel_w = CAMERA_W - 40
    panel_h = 110
    pygame.draw.rect(screen, WHITE, (panel_x, panel_y, panel_w, panel_h), border_radius=8)
    pygame.draw.rect(screen, BORDER_COLOR, (panel_x, panel_y, panel_w, panel_h), width=1, border_radius=8)
    title = font_big.render("识别结果", True, DARK_GRAY)
    screen.blit(title, (panel_x + 15, panel_y + 8))
    if plate_text != "暂无车牌":
        plate_display = font_text.render(plate_text, True, BLUE)
    else:
        plate_display = font_text.render(plate_text, True, DARK_GRAY)
    screen.blit(plate_display, (panel_x + 15, panel_y + 38))

    tip_render = font_small.render(db_tip, True, (100, 100, 100))
    screen.blit(tip_render, (panel_x + 15, panel_y + 72))


def get_full_plate():
    return manual_province + manual_input


def run_camera_app():
    global cap, camera_open, current_frame, plate_text, db_tip, running
    global vehicle_data, remaining_spaces, manual_input, manual_active, manual_result
    global manual_province, province_selector_open, province_selected_index

    try:
        log_error("=== run_camera_app 开始 ===")

        cap = None
        camera_open = False
        current_frame = None
        plate_text = "暂无车牌"
        db_tip = ""
        manual_input = ""
        manual_active = False
        manual_result = ""
        manual_province = "湘"
        province_selector_open = False
        province_selected_index = PROVINCES.index("湘") if "湘" in PROVINCES else 0
        running = True
        log_error("变量初始化完成")

        log_error("开始加载车辆数据...")
        load_vehicle_data()
        log_error("车辆数据加载完成")

        log_error("进入主循环...")
        while running:
            if not pygame.display.get_init():
                log_error("Pygame 已关闭，退出循环")
                running = False
                break
            try:
                #绘制背景
                screen.fill(LIGHT_GRAY)
                left_bg = pygame.Rect(0, 0, CAMERA_W + 10, WINDOW_H)
                pygame.draw.rect(screen, WHITE, left_bg)
                right_bg = pygame.Rect(CAMERA_W + 10, 0, PANEL_W - 10, WINDOW_H)
                pygame.draw.rect(screen, LIGHT_GRAY, right_bg)
                #绘制手动录入区域并获取控件位置
                (btn_rect, input_x, input_y, input_w, input_h,
                 selector_x, selector_y, selector_w, selector_h,
                 list_x, list_y, list_w, list_h,
                 scrollbar_x, scrollbar_y, scrollbar_w, scrollbar_h,
                 has_scrollbar) = draw_manual_input_area()

                #事件处理
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        running = False
                    #鼠标滚轮事件
                    elif event.type == pygame.MOUSEWHEEL:
                        if province_selector_open:
                            if event.y > 0:
                                if province_selected_index > 0:
                                    province_selected_index -= 1
                                    manual_province = PROVINCES[province_selected_index]
                            elif event.y < 0:
                                if province_selected_index < len(PROVINCES) - 1:
                                    province_selected_index += 1
                                    manual_province = PROVINCES[province_selected_index]

                    elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        mx, my = pygame.mouse.get_pos()
                        #检查是否点击了省份选择器
                        if (selector_x is not None and
                                selector_x <= mx <= selector_x + selector_w and
                                selector_y <= my <= selector_y + selector_h):
                            province_selector_open = not province_selector_open
                            continue

                        #检查是否点击了省份列表项
                        if province_selector_open and list_x is not None:
                            if (list_x <= mx <= list_x + list_w and
                                    list_y <= my <= list_y + list_h):
                                item_h = PROVINCE_ITEM_HEIGHT
                                visible_items = PROVINCE_VISIBLE_ITEMS
                                idx = (my - list_y - 2) // item_h
                                scroll_offset = 0
                                if province_selected_index >= visible_items:
                                    scroll_offset = province_selected_index - visible_items + 1
                                if scroll_offset > len(PROVINCES) - visible_items:
                                    scroll_offset = len(PROVINCES) - visible_items
                                actual_idx = idx + scroll_offset
                                if 0 <= actual_idx < len(PROVINCES):
                                    manual_province = PROVINCES[actual_idx]
                                    province_selected_index = actual_idx
                                    province_selector_open = False
                                    manual_active = True
                                    continue

                        #如果点击了其他地方，关闭省份选择器
                        province_selector_open = False
                        #打开摄像头
                        if btn_open.collidepoint(mx, my):
                            if not camera_open:
                                try:
                                    cap = None
                                    for i in range(3):
                                        print(f"尝试打开摄像头 {i}...")
                                        test_cap = cv2.VideoCapture(i)
                                        if test_cap.isOpened():
                                            cap = test_cap
                                            print(f"成功打开摄像头 {i}")
                                            break
                                        else:
                                            test_cap.release()

                                    if cap is None:
                                        db_tip = "未找到可用摄像头，请检查连接"
                                    else:
                                        cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_W)
                                        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_H)
                                        ret, test_frame = cap.read()
                                        if ret and test_frame is not None:
                                            camera_open = True
                                            plate_text = "暂无车牌"
                                            db_tip = "摄像头已开启"
                                            load_vehicle_data()
                                        else:
                                            cap.release()
                                            cap = None
                                            db_tip = "摄像头打开但无法读取画面"
                                except Exception as e:
                                    db_tip = f"打开失败: {str(e)}"

                        #关闭摄像头
                        elif btn_close.collidepoint(mx, my):
                            if camera_open and cap is not None:
                                cap.release()
                                cap = None
                                camera_open = False
                                current_frame = None
                                plate_text = "暂无车牌"
                                db_tip = "摄像头已关闭"
                                load_vehicle_data()

                        #抓拍识别
                        elif btn_recognize.collidepoint(mx, my):
                            if camera_open and current_frame is not None:
                                try:
                                    cv2.imwrite(FILE_SAVE_PATH, current_frame)
                                    db_tip = "正在识别..."
                                    try:
                                        plate_text = getcn()
                                    except Exception as ocr_error:
                                        db_tip = f"OCR识别失败: {str(ocr_error)}"
                                        plate_text = "暂无车牌"
                                        continue
                                    if is_valid_plate(plate_text):
                                        clean_plate = plate_text.strip()
                                        status, msg = handle_plate_data(clean_plate)
                                        db_tip = msg
                                        plate_text = clean_plate
                                        load_vehicle_data()
                                    else:
                                        db_tip = "未识别到有效车牌"
                                        plate_text = "暂无车牌"
                                except Exception as e:
                                    db_tip = f"识别异常: {str(e)}"
                            elif not camera_open:
                                db_tip = "请先打开摄像头！"
                            else:
                                db_tip = "等待画面加载..."

                        #收入统计
                        elif btn_income.collidepoint(mx, my):
                            try:
                                from income_chart import show_income_chart_with_selection
                                t = threading.Thread(target=show_income_chart_with_selection, daemon=True)
                                t.start()
                            except Exception as e:
                                db_tip = f"打开收入统计失败: {str(e)}"

                        #点击输入框 -> 激活
                        elif input_x <= mx <= input_x + input_w and input_y <= my <= input_y + input_h:
                            manual_active = True
                            manual_result = ""

                        #点击录入按钮
                        elif btn_rect.collidepoint(mx, my):
                            full_plate = get_full_plate()
                            if full_plate.strip() and manual_input.strip():
                                if is_valid_plate(full_plate):
                                    status, msg = handle_plate_data(full_plate)
                                    manual_result = msg
                                    load_vehicle_data()
                                    manual_input = ""
                                else:
                                    manual_result = "无效车牌格式，请重新输入"
                            else:
                                manual_result = "请输入车牌号"

                        #点击其他地方 -> 取消激活
                        else:
                            manual_active = False

                    #           键盘事件
                    elif event.type == pygame.KEYDOWN:
                        if manual_active:
                            if event.unicode and ord(event.unicode) >= 128:
                                continue
                            if event.key == pygame.K_RETURN:
                                full_plate = get_full_plate()
                                if full_plate.strip() and manual_input.strip():
                                    if is_valid_plate(full_plate):
                                        status, msg = handle_plate_data(full_plate)
                                        manual_result = msg
                                        load_vehicle_data()
                                        manual_input = ""
                                    else:
                                        manual_result = "无效车牌格式，请重新输入"
                                else:
                                    manual_result = "请输入车牌号"
                            elif event.key == pygame.K_BACKSPACE:
                                manual_input = manual_input[:-1]
                            elif event.key == pygame.K_ESCAPE:
                                manual_active = False
                                manual_input = ""
                                province_selector_open = False
                            elif event.key == pygame.K_TAB:
                                pass
                            else:
                                #只允许输入大写字母和数字，自动转大写
                                char = event.unicode.upper()
                                if char.isalnum() and len(manual_input) < 7:
                                    manual_input += char

                #读取摄像头画面
                if camera_open and cap is not None:
                    ret, frame = cap.read()
                    if ret and frame is not None:
                        current_frame = frame
                        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        surf = pygame.surfarray.make_surface(np.rot90(frame_rgb))
                        surf = pygame.transform.flip(surf, True, False)
                        screen.blit(surf, (0, 0))
                    else:
                        db_tip = "摄像头断开，尝试重连..."
                        cap.release()
                        cap = None
                        camera_open = False
                else:
                    draw_camera_frame()

                #绘制按钮
                pygame.draw.rect(screen, BLUE, btn_open, border_radius=6)
                txt_open = font_btn.render("打开摄像头", True, WHITE)
                screen.blit(txt_open, (btn_open.x + 25, btn_open.y + 10))

                pygame.draw.rect(screen, RED, btn_close, border_radius=6)
                txt_close = font_btn.render("关闭摄像头", True, WHITE)
                screen.blit(txt_close, (btn_close.x + 25, btn_close.y + 10))

                pygame.draw.rect(screen, GREEN, btn_recognize, border_radius=6)
                txt_rec = font_btn.render("抓拍识别车牌", True, WHITE)
                screen.blit(txt_rec, (btn_recognize.x + 20, btn_recognize.y + 10))

                pygame.draw.rect(screen, ORANGE, btn_income, border_radius=6)
                txt_income = font_btn.render("收入统计", True, WHITE)
                screen.blit(txt_income, (btn_income.x + 28, btn_income.y + 10))

                draw_result_panel()
                draw_status_bar()
                draw_vehicle_table()
                draw_longest_parking_info()

                pygame.display.update()
                clock.tick(30)

            except Exception as e:
                log_error(f"主循环异常: {str(e)}")
                log_error(traceback.format_exc())
    except Exception as e:
        log_error(f"run_camera_app 崩溃: {str(e)}")
        log_error(traceback.format_exc())
        if cap is not None:
            cap.release()
        cv2.destroyAllWindows()
        pygame.quit()
        raise


if __name__ == "__main__":
    run_camera_app()