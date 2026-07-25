import pygame

pygame.init()

#窗口配置
WINDOW_W = 1400
WINDOW_H = 700
CAMERA_W = 740
CAMERA_H = 480
PANEL_W = WINDOW_W - CAMERA_W

#收费标准：每天费用（元）
MONEY_PER_DAY = 10

#停车场配置
total_spaces = 10
FILE_SAVE_PATH = "file/temp.png"

#颜色常量
WHITE = (255, 255, 255)
GRAY = (200, 200, 200)
DARK_GRAY = (80, 80, 80)
LIGHT_GRAY = (240, 240, 240)
BLUE = (30, 144, 255)
DARK_BLUE = (20, 80, 160)
BLACK = (0, 0, 0)
RED = (220, 0, 0)
GREEN = (0, 160, 0)
ORANGE = (255, 140, 0)
BORDER_COLOR = (180, 180, 180)
TABLE_HEADER = (50, 50, 80)
TABLE_ROW1 = (245, 245, 250)
TABLE_ROW2 = (235, 235, 240)

#字体
font_btn = pygame.font.SysFont("SimHei", 18)
font_text = pygame.font.SysFont("SimHei", 22)
font_tip = pygame.font.SysFont("SimHei", 16)
font_title = pygame.font.SysFont("SimHei", 28)
font_big = pygame.font.SysFont("SimHei", 20)
font_small = pygame.font.SysFont("SimHei", 14)