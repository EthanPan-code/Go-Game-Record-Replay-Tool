import pygame
import sys
import copy
import re
import tkinter as tk
from tkinter import filedialog
import ctypes


# 設定棋盤大小與格數
BOARD_SIZE = 19
CELL_SIZE = 30
MARGIN = 40
WINDOW_SIZE = CELL_SIZE * (BOARD_SIZE - 1) + MARGIN * 2
BUTTON_HEIGHT = 40
TOTAL_WINDOW_HEIGHT = WINDOW_SIZE + BUTTON_HEIGHT + 10 # 增加按鈕區域的高度

# 顏色常數
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (100, 100, 100)
RED = (255, 0, 0)
BGCOLOR = (240, 200, 120)
BUTTON_COLOR = (180, 180, 180)
BUTTON_HIGHLIGHT = (150, 150, 150)
TEXT_COLOR = BLACK

# 初始化pygame
pygame.init()
screen = pygame.display.set_mode((WINDOW_SIZE, TOTAL_WINDOW_HEIGHT)) # 使用新的視窗高度
pygame.display.set_caption("圍棋打譜")
clock = pygame.time.Clock()
font = pygame.font.Font("edukai-5.0.ttf", 20)
button_font = pygame.font.Font("edukai-5.0.ttf", 18)
hundred_font = pygame.font.Font("edukai-5.0.ttf", 15)

user32 = ctypes.WinDLL('user32', use_last_error=True)
previous_hkl = user32.GetKeyboardLayout(0)
def switch_to_previous_input(previous_hkl):
    user32 = ctypes.WinDLL('user32', use_last_error=True)
    user32.ActivateKeyboardLayout(previous_hkl, 0)
# 強制切換輸入法為英文（美式鍵盤）
def switch_to_english_input():
    # 0x0409 是英文（美式）語系的代碼
    hwnd = pygame.display.get_wm_info()['window']
    user32 = ctypes.WinDLL('user32', use_last_error=True)
    hkl = user32.LoadKeyboardLayoutW('00000409', 1)  # 00000409 = 英文(美式)
    user32.ActivateKeyboardLayout(hkl, 0)
switch_to_english_input()


# 建立棋盤資料
board = [[None for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
move_history = []
redo_stack = []
current_player = "black"
previous_board = None  # 用來處理劫爭
show_move_numbers = False
review_mode = False
review_index = 0
auto_play = False
auto_play_timer = 0
auto_play_delay = 1000  # 毫秒為單位（0.5 秒）
review_new_moves = []
saved_move_history = []
saved_board = []
last_move_pos = None

# 座標標記
letters = [chr(ord('A') + i) for i in range(BOARD_SIZE + 1) if chr(ord('A') + i) != 'I']

# 星位點位置
hoshi_points = [(3, 3), (9, 3), (15, 3),
                (3, 9), (9, 9), (15, 9),
                (3, 15), (9, 15), (15, 15)]

# 按鈕設定
BUTTON_WIDTH = 100
BUTTON_MARGIN = 10
BUTTON_Y = WINDOW_SIZE + 10

undo_button_rect = pygame.Rect(BUTTON_MARGIN, BUTTON_Y, BUTTON_WIDTH, BUTTON_HEIGHT - 10)
save_button_rect = pygame.Rect(WINDOW_SIZE - (BUTTON_MARGIN * 2 + BUTTON_WIDTH), BUTTON_Y, BUTTON_WIDTH, BUTTON_HEIGHT - 10)
load_button_rect = pygame.Rect(WINDOW_SIZE - (BUTTON_MARGIN + BUTTON_WIDTH)-125, BUTTON_Y, BUTTON_WIDTH, BUTTON_HEIGHT - 10)
toggle_numbers_button_rect = pygame.Rect(WINDOW_SIZE // 2 - BUTTON_WIDTH // 2, BUTTON_Y, BUTTON_WIDTH, BUTTON_HEIGHT - 10)
review_button_rect = pygame.Rect(BUTTON_MARGIN * 2 + BUTTON_WIDTH, BUTTON_Y, BUTTON_WIDTH+10, BUTTON_HEIGHT - 10)

# 畫出按鈕
def draw_buttons():
    def draw_button(rect, text, highlight):
        color = BUTTON_HIGHLIGHT if highlight else BUTTON_COLOR
        pygame.draw.rect(screen, color, rect)
        text_surface = button_font.render(text, True, TEXT_COLOR)
        text_rect = text_surface.get_rect(center=rect.center)
        screen.blit(text_surface, text_rect)

    mouse_pos = pygame.mouse.get_pos()
    draw_button(undo_button_rect, "復原", undo_button_rect.collidepoint(mouse_pos))
    draw_button(save_button_rect, "另存新檔", save_button_rect.collidepoint(mouse_pos))
    draw_button(load_button_rect, "載入", load_button_rect.collidepoint(mouse_pos))
    if show_move_numbers:
        draw_button(toggle_numbers_button_rect, "隱藏步數", toggle_numbers_button_rect.collidepoint(mouse_pos))
    else:
        draw_button(toggle_numbers_button_rect, "顯示步數", toggle_numbers_button_rect.collidepoint(mouse_pos))
    if review_mode:
        draw_button(review_button_rect, "複盤模式ON", review_button_rect.collidepoint(mouse_pos))
    else:
        draw_button(review_button_rect, "複盤模式OFF", review_button_rect.collidepoint(mouse_pos))

# 畫出棋盤
def draw_board():
    screen.fill(BGCOLOR)
    for i in range(BOARD_SIZE):
        pygame.draw.line(screen, BLACK,
                         (MARGIN, MARGIN + i * CELL_SIZE),
                         (WINDOW_SIZE - MARGIN, MARGIN + i * CELL_SIZE))
        pygame.draw.line(screen, BLACK,
                         (MARGIN + i * CELL_SIZE, MARGIN),
                         (MARGIN + i * CELL_SIZE, WINDOW_SIZE - MARGIN))

    # 畫座標
    for i in range(BOARD_SIZE):
        letter = letters[i]
        text = font.render(letter, True, BLACK)
        screen.blit(text, (MARGIN + i * CELL_SIZE - 5, WINDOW_SIZE - MARGIN + 5))
        screen.blit(text, (MARGIN + i * CELL_SIZE - 5, 5))

        number = str(BOARD_SIZE - i)
        text = font.render(number, True, BLACK)
        screen.blit(text, (5, MARGIN + i * CELL_SIZE - 5))
        screen.blit(text, (WINDOW_SIZE - MARGIN + 5, MARGIN + i * CELL_SIZE - 5))

    for x, y in hoshi_points:
        px = MARGIN + x * CELL_SIZE
        py = MARGIN + y * CELL_SIZE
        pygame.draw.circle(screen, BLACK, (px, py), 3)

# 畫出所有棋子與步數

def draw_move_number(mx, my, num, text_color, surface=screen):
    if num < 10:
        num_text = font.render(str(num), True, text_color)
        surface.blit(num_text, (MARGIN + mx * CELL_SIZE - 5, MARGIN + my * CELL_SIZE - 10))
    elif num < 100:
        num_text = font.render(str(num), True, text_color)
        surface.blit(num_text, (MARGIN + mx * CELL_SIZE - 10, MARGIN + my * CELL_SIZE - 10))
    else:
        num_text = hundred_font.render(str(num), True, text_color)
        surface.blit(num_text, (MARGIN + mx * CELL_SIZE - 12, MARGIN + my * CELL_SIZE - 8))
 
def draw_stones():
    for y in range(BOARD_SIZE):
        for x in range(BOARD_SIZE):
            if board[y][x]:
                pos = (MARGIN + x * CELL_SIZE, MARGIN + y * CELL_SIZE)
                color = BLACK if board[y][x] == "black" else WHITE
                pygame.draw.circle(screen, color, pos, CELL_SIZE // 2 - 2)
                if board[y][x] == "white":
                    pygame.draw.circle(screen, BLACK, pos, CELL_SIZE // 2 - 2, 1)
                if last_move_pos and last_move_pos == (x, y) and show_move_numbers == False and review_mode == False:
                    pygame.draw.circle(screen, RED, pos, CELL_SIZE // 2 -1, 2)  # 畫一個稍大的空心圓    

    if show_move_numbers:
        if review_mode and len(review_new_moves) >= 1:
            # 複盤模式且有新下的子：畫新落子步數
            for index, (mx, my, color) in enumerate(review_new_moves):
                num = index + 1
                text_color = WHITE if color == "black" else BLACK
                draw_move_number(mx, my, num, text_color, surface=screen)

        else:
            # 一般模式 或 複盤中但還沒新落子：畫正常的 move_history 步數
            max_index = review_index if review_mode else len(move_history)        
            for index in range(max_index):
                mx, my, color = move_history[index]
                num = index + 1
                text_color = WHITE if color == "black" else BLACK
                draw_move_number(mx, my, num, text_color, surface=screen)
            





# 畫出預覽棋子
def draw_hover_stone():
    mouse_x, mouse_y = pygame.mouse.get_pos()
    grid_pos = get_pos_from_mouse((mouse_x, mouse_y))
    if grid_pos:
        x, y = grid_pos
        if board[y][x] is None and mouse_y < WINDOW_SIZE:
            pos = (MARGIN + x * CELL_SIZE, MARGIN + y * CELL_SIZE)
            color = (50, 50, 50) if current_player == "black" else (200, 200, 200)
            pygame.draw.circle(screen, color, pos, CELL_SIZE // 2 - 2)
            if current_player == "white":
                pygame.draw.circle(screen, BLACK, pos, CELL_SIZE // 2 - 2, 1)

# 計算滑鼠點擊位置所對應的格子
def get_pos_from_mouse(pos):
    x, y = pos
    grid_x = round((x - MARGIN) / CELL_SIZE)
    grid_y = round((y - MARGIN) / CELL_SIZE)
    if 0 <= grid_x < BOARD_SIZE and 0 <= grid_y < BOARD_SIZE:
        return grid_x, grid_y
    return None




# 檢查連通區域與氣
def get_group(board, x, y, color, visited):
    group = []
    queue = [(x, y)]
    while queue:
        cx, cy = queue.pop()
        if (cx, cy) in visited:
            continue
        visited.add((cx, cy))
        group.append((cx, cy))
        for dx, dy in [(-1,0), (1,0), (0,-1), (0,1)]:
            nx, ny = cx + dx, cy + dy
            if 0 <= nx < BOARD_SIZE and 0 <= ny < BOARD_SIZE:
                if board[ny][nx] == color and (nx, ny) not in visited:
                    queue.append((nx, ny))
    return group

def count_liberties(board, group):
    liberties = set()
    for x, y in group:
        for dx, dy in [(-1,0), (1,0), (0,-1), (0,1)]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < BOARD_SIZE and 0 <= ny < BOARD_SIZE:
                if board[ny][nx] is None:
                    liberties.add((nx, ny))
    return len(liberties)

# 嘗試落子與處理提子（含劫爭）
def try_move(x, y, color):
    global previous_board, last_move_pos
    if board[y][x] is not None:
        return False

    test_board = copy.deepcopy(board)
    test_board[y][x] = color

    opponent = "white" if color == "black" else "black"
    captured = []
    for dx, dy in [(-1,0), (1,0), (0,-1), (0,1)]:
        nx, ny = x + dx, y + dy
        if 0 <= nx < BOARD_SIZE and 0 <= ny < BOARD_SIZE:
            if test_board[ny][nx] == opponent:
                visited = set()
                group = get_group(test_board, nx, ny, opponent, visited)
                if count_liberties(test_board, group) == 0:
                    captured.extend(group)


    for cx, cy in captured:
        test_board[cy][cx] = None

    visited = set()
    self_group = get_group(test_board, x, y, color, visited)
    if count_liberties(test_board, self_group) == 0:
        return False

    if previous_board is not None and test_board == previous_board:
        return False

    previous_board = copy.deepcopy(board)
    for cy in range(BOARD_SIZE):
        for cx in range(BOARD_SIZE):
            board[cy][cx] = test_board[cy][cx]
    move_history.append((x, y, color))
    redo_stack.clear()
    last_move_pos = (x, y)
    return True

# 執行悔棋
def undo_move():
    global current_player, previous_board, last_move_pos
    if move_history:
        redo_stack.append(move_history.pop())
        reset_board_from_history()
        current_player = "white" if current_player == "black" else "black"
        if move_history:
            last_move_pos = (move_history[-1][0], move_history[-1][1])
        else:
            last_move_pos = None
    else:
        last_move_pos = None

# 執行重做
def redo_move():
    global current_player, last_move_pos
    if redo_stack:
        x, y, color = redo_stack.pop()
        try_move(x, y, color)
        current_player = "white" if current_player == "black" else "black"
    if move_history:
        last_move_pos = (move_history[-1][0], move_history[-1][1])
    else:
        last_move_pos = None

# 根據歷史重建棋盤
def reset_board_from_history():
    global board, previous_board, last_move_pos
    board = [[None for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
    previous_board = None
    for x, y, color in move_history:
        test_board = copy.deepcopy(board)
        test_board[y][x] = color
        opponent = "white" if color == "black" else "black"
        captured = []
        for dx, dy in [(-1,0), (1,0), (0,-1), (0,1)]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < BOARD_SIZE and 0 <= ny < BOARD_SIZE:
                if test_board[ny][nx] == opponent:
                    visited = set()
                    group = get_group(test_board, nx, ny, opponent, visited)
                    if count_liberties(test_board, group) == 0:
                        captured.extend(group)
        for cx, cy in captured:
            test_board[cy][cx] = None
        board = test_board
    previous_board = copy.deepcopy(board)
    if move_history:
        last_move_pos = (move_history[-1][0], move_history[-1][1])
    else:
        last_move_pos = None

def reset_board_to_index(index):
    global board, previous_board
    board = [[None for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
    previous_board = None
    for i in range(index):
        x, y, color = move_history[i]
        test_board = copy.deepcopy(board)
        test_board[y][x] = color
        opponent = "white" if color == "black" else "black"
        captured = []
        for dx, dy in [(-1,0), (1,0), (0,-1), (0,1)]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < BOARD_SIZE and 0 <= ny < BOARD_SIZE:
                if test_board[ny][nx] == opponent:
                    visited = set()
                    group = get_group(test_board, nx, ny, opponent, visited)
                    if count_liberties(test_board, group) == 0:
                        captured.extend(group)
        for cx, cy in captured:
            test_board[cy][cx] = None
        board = test_board
    previous_board = copy.deepcopy(board)



# 儲存棋譜為 SGF 檔案
def save_sgf():
    try:
        root = tk.Tk()
        root.withdraw()
        file_path = filedialog.asksaveasfilename(defaultextension=".sgf", filetypes=[("SGF Files", "*.sgf")])
        if not file_path:
            return  # 如果按取消就不存
        sgf = f"(;GM[1]FF[4]SZ[{BOARD_SIZE}]"
        for x, y, color in move_history:
            col = chr(ord('a') + x)
            row = chr(ord('a') + y)
            sgf += f";{'B' if color == 'black' else 'W'}[{col}{row}]"
        sgf += ")"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(sgf)
        print("棋譜已儲存為", file_path)
    except Exception as e:
        print("儲存 SGF 發生錯誤：", e)


# 載入 SGF 檔案（開啟檔案選擇器）
def load_sgf():
    global move_history, redo_stack, current_player, last_move_pos
    try:
        root = tk.Tk()
        root.withdraw()
        file_path = filedialog.askopenfilename(filetypes=[("SGF Files", "*.sgf")])
        if not file_path:
            return
        with open(file_path, "r", encoding="utf-8") as f:
            sgf_content = f.read()
        moves = re.findall(r';([BW])\[([a-s])([a-s])\]', sgf_content)
        move_history = []
        redo_stack = []
        for color, x_str, y_str in moves:
            x = ord(x_str) - ord('a')
            y = ord(y_str) - ord('a')
            move_history.append((x, y, 'black' if color == 'B' else 'white'))
        current_player = 'black' if len(move_history) % 2 == 0 else 'white'
        reset_board_from_history()
        if move_history:
            last_move_pos = (move_history[-1][0], move_history[-1][1])
        else:
            last_move_pos = None
        print("已載入 SGF 棋譜：", file_path)
    except Exception as e:
        print("載入 SGF 發生錯誤：", e)


def export_board_image():
    try:
        root = tk.Tk()
        root.withdraw()
        file_path = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG Images", "*.png")])
        if not file_path:
            return  # 使用者取消就不存

        # 建立一個新的 Surface，只畫棋盤和棋子，不含 hover
        board_surface = pygame.Surface((WINDOW_SIZE, WINDOW_SIZE))

        # 1. 畫棋盤背景與格線
        board_surface.fill(BGCOLOR)
        for i in range(BOARD_SIZE):
            pygame.draw.line(board_surface, BLACK,
                             (MARGIN, MARGIN + i * CELL_SIZE),
                             (WINDOW_SIZE - MARGIN, MARGIN + i * CELL_SIZE))
            pygame.draw.line(board_surface, BLACK,
                             (MARGIN + i * CELL_SIZE, MARGIN),
                             (MARGIN + i * CELL_SIZE, WINDOW_SIZE - MARGIN))

        # 2. 座標標記
        for i in range(BOARD_SIZE):
            letter = letters[i]
            text = font.render(letter, True, BLACK)
            board_surface.blit(text, (MARGIN + i * CELL_SIZE - 5, WINDOW_SIZE - MARGIN + 5))
            board_surface.blit(text, (MARGIN + i * CELL_SIZE - 5, 5))

            number = str(BOARD_SIZE - i)
            text = font.render(number, True, BLACK)
            board_surface.blit(text, (5, MARGIN + i * CELL_SIZE - 5))
            board_surface.blit(text, (WINDOW_SIZE - MARGIN + 5, MARGIN + i * CELL_SIZE - 5))

        # 3. 畫星位
        for x, y in hoshi_points:
            px = MARGIN + x * CELL_SIZE
            py = MARGIN + y * CELL_SIZE
            pygame.draw.circle(board_surface, BLACK, (px, py), 3)

        # 4. 畫棋子
        for y in range(BOARD_SIZE):
            for x in range(BOARD_SIZE):
                if board[y][x]:
                    pos = (MARGIN + x * CELL_SIZE, MARGIN + y * CELL_SIZE)
                    color = BLACK if board[y][x] == "black" else WHITE
                    pygame.draw.circle(board_surface, color, pos, CELL_SIZE // 2 - 2)
                    if board[y][x] == "white":
                        pygame.draw.circle(board_surface, BLACK, pos, CELL_SIZE // 2 - 2, 1)

        # 5. 若顯示步數，標上號碼
        if show_move_numbers:
            if review_mode and len(review_new_moves) > 0:
                # 複盤且有新落子
                for index, (mx, my, color) in enumerate(review_new_moves):
                    num = index + 1
                    text_color = WHITE if color == "black" else BLACK
                    draw_move_number(mx, my, num, text_color, surface=board_surface)
            else:
                # 正常畫 move_history
                max_index = review_index if review_mode else len(move_history)
                for index in range(max_index):
                    mx, my, color = move_history[index]
                    num = index + 1
                    text_color = WHITE if color == "black" else BLACK
                    draw_move_number(mx, my, num, text_color, surface=board_surface)

        # 儲存圖檔
        pygame.image.save(board_surface, file_path)
        print(f"已將棋盤匯出為 {file_path}")
    except Exception as e:
        print("儲存 PNG 發生錯誤：", e)






# 主迴圈
while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            switch_to_previous_input(previous_hkl)
            pygame.quit()
            sys.exit()

        elif event.type == pygame.MOUSEBUTTONDOWN:
            pos = pygame.mouse.get_pos()
            if undo_button_rect.collidepoint(pos):
                if review_mode and len(review_new_moves) > 0:
                    # 複盤模式，撤銷新下的子
                    last_move = review_new_moves.pop()
                    x, y, _ = last_move
                    board[y][x] = None
                    current_player = "white" if current_player == "black" else "black"
                elif review_mode == False:
                    # 正常模式撤銷
                    undo_move()
            elif save_button_rect.collidepoint(pos):
                save_sgf()
            elif load_button_rect.collidepoint(pos):
                load_sgf()
            elif toggle_numbers_button_rect.collidepoint(pos):
                show_move_numbers = not show_move_numbers
            elif review_button_rect.collidepoint(pos):
                if not review_mode:
                    # 要開啟複盤，先儲存目前的狀態
                    saved_move_history = copy.deepcopy(move_history)
                    saved_board = copy.deepcopy(board)
                    review_new_moves = []
                    review_index = len(move_history)
                    review_mode = True
                    auto_play = False
                else:
                    # 要結束複盤，回復原本的棋盤
                    move_history = saved_move_history
                    board = saved_board
                    review_new_moves = []
                    reset_board_from_history()
                    review_mode = False
                    auto_play = False

            elif event.button == 1: 
                grid_pos = get_pos_from_mouse(pos)
                if grid_pos:
                    x, y = grid_pos
                    if not review_mode:
                        if try_move(x, y, current_player):
                            current_player = "white" if current_player == "black" else "black"
                    elif auto_play == False:
                        # 複盤模式也可以下子
                        if board[y][x] is None:
                            color = current_player
                            board[y][x] = color
                            review_new_moves.append((x, y, color))
                            current_player = "white" if current_player == "black" else "black"




        elif event.type == pygame.KEYDOWN:
            switch_to_english_input()
            mods = pygame.key.get_mods()
            if mods & pygame.KMOD_CTRL:
                if event.key == pygame.K_z:
                    if review_mode and len(review_new_moves) > 0:
                        # 複盤模式，撤銷新下的子
                        last_move = review_new_moves.pop()
                        x, y, _ = last_move
                        board[y][x] = None
                        current_player = "white" if current_player == "black" else "black"
                    elif review_mode == False:
                        # 正常模式撤銷
                        undo_move()

                elif event.key == pygame.K_y:
                    redo_move()
                elif event.key == pygame.K_s and (mods & pygame.KMOD_SHIFT):
                    save_sgf()
                elif event.key == pygame.K_l:
                    load_sgf()
                elif event.key == pygame.K_p:
                    export_board_image()
            if review_mode:
                if event.key == pygame.K_LEFT:
                    if review_index > 0:
                        review_index -= 1
                        reset_board_to_index(review_index)
                elif event.key == pygame.K_RIGHT:
                    if review_index < len(move_history):
                        review_index += 1
                        reset_board_to_index(review_index)
                elif event.key == pygame.K_SPACE and len(review_new_moves) == 0:
                    if review_index == len(move_history):
                        review_index = 0
                    auto_play = not auto_play



        
    draw_board()
    draw_stones()
    draw_buttons() # 畫出按鈕
    draw_hover_stone()
    if review_mode:
        info_text = font.render(f"複盤中：第 {review_index}/{len(move_history)} 手", True, BLACK)
        screen.blit(info_text, (WINDOW_SIZE // 2 - 80, WINDOW_SIZE + BUTTON_HEIGHT - 55))
    pygame.display.flip()
    if review_mode and auto_play:
        auto_play_timer += clock.get_time()
        if auto_play_timer >= auto_play_delay:
            auto_play_timer = 0
            if review_index < len(move_history):
                review_index += 1
                reset_board_to_index(review_index)
            else:
                auto_play = False  # 播放完就停住

    clock.tick(60)

