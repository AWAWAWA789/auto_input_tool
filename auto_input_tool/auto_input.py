import pyautogui
import pyperclip
import time
import threading
import tkinter as tk
from tkinter import scrolledtext, messagebox, filedialog
from pynput import mouse


class AutoInputApp:
    """自动输入工具 - 支持暂停/继续/从头输入"""
    
    # 常量配置
    WINDOW_TITLE = "自动输入工具 Pro"
    WINDOW_SIZE = "800x650"
    COUNTDOWN_SECONDS = 3
    INPUT_DELAY = 0.05
    ENCODINGS = ['utf-8', 'utf-8-sig', 'gbk', 'gb2312', 'gb18030', 'latin-1']
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(self.WINDOW_TITLE)
        self.root.geometry(self.WINDOW_SIZE)
        
        # 状态变量
        self.is_running = False
        self.stop_flag = False
        self.current_index = 0
        self.full_text = ""
        self.pending_start_index = 0
        self.mouse_listener = None
        
        # 创建界面
        self.create_widgets()
        self.setup_shortcuts()
    
    def create_widgets(self):
        """创建界面组件"""
        # 顶部框架 - 文本区域
        top_frame = tk.Frame(self.root)
        top_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        tk.Label(top_frame, text="输入内容:", font=("微软雅黑", 10)).pack(anchor=tk.W)
        self.text_area = scrolledtext.ScrolledText(top_frame, height=18, width=70, font=("Consolas", 10))
        self.text_area.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        
        # 中部框架 - 状态信息
        mid_frame = tk.Frame(self.root)
        mid_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # 进度条
        self.progress_bar = tk.Canvas(mid_frame, height=20, bg="#e0e0e0", highlightthickness=0)
        self.progress_bar.pack(fill=tk.X, pady=(0, 5))
        
        # 状态标签
        self.status_label = tk.Label(mid_frame, text="就绪", fg="blue", font=("微软雅黑", 9))
        self.status_label.pack()
        
        # 底部框架 - 按钮
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # 按钮样式
        btn_style = {"font": ("微软雅黑", 10), "width": 12, "height": 1}
        
        self.start_btn = tk.Button(btn_frame, text="开始输入", command=self.start_input, 
                                   bg="#66BB6A", fg="white", **btn_style)
        self.start_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = tk.Button(btn_frame, text="停止", command=self.stop_or_continue, 
                                  bg="#EF5350", fg="white", state=tk.DISABLED, **btn_style)
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        self.set_start_btn = tk.Button(btn_frame, text="设为起点", command=self.set_start_position,
                                       bg="#AB47BC", fg="white", state=tk.DISABLED, **btn_style)
        self.set_start_btn.pack(side=tk.LEFT, padx=5)
        
        self.file_btn = tk.Button(btn_frame, text="从文件加载", command=self.load_file,
                                  bg="#42A5F5", fg="white", **btn_style)
        self.file_btn.pack(side=tk.LEFT, padx=5)
    
    def setup_shortcuts(self):
        """设置快捷键"""
        # 绑定鼠标点击事件到文本框
        self.text_area.bind('<ButtonRelease-1>', self.on_text_click)
    
    def on_text_click(self, event):
        """处理文本框点击事件"""
        # 只在停止状态下允许设置起始位置
        if self.is_running:
            return
        
        # 获取点击位置的索引
        click_index = self.text_area.index(f"@{event.x},{event.y}")
        
        # 转换为字符索引
        line, col = map(int, click_index.split('.'))
        
        # 获取文本内容
        self.full_text = self.text_area.get("1.0", "end-1c")
        
        # 计算字符索引
        lines = self.full_text.split('\n')
        char_index = 0
        
        for i in range(line - 1):
            if i < len(lines):
                char_index += len(lines[i]) + 1  # +1 for newline
        
        char_index += min(col, len(lines[line - 1]) if line - 1 < len(lines) else 0)
        
        # 确保索引在有效范围内
        char_index = min(char_index, len(self.full_text))
        
        # 记录待设置的起始位置
        self.pending_start_index = char_index
        
        # 启用"设为起点"按钮
        self.set_start_btn.config(state=tk.NORMAL)
        
        # 高亮该位置
        if char_index < len(self.full_text):
            self.highlight_char(char_index)
            self.status_label.config(text=f"点击位置: {char_index}，点击'设为起点'确认", fg="blue")
        else:
            self.status_label.config(text=f"点击位置: 末尾，点击'设为起点'确认", fg="blue")
    
    def set_start_position(self):
        """设置起始位置"""
        if not hasattr(self, 'pending_start_index'):
            return
        
        self.current_index = self.pending_start_index
        
        if self.current_index < len(self.full_text):
            self.highlight_char(self.current_index)
            self.status_label.config(text=f"已设置起始位置: {self.current_index}", fg="green")
        else:
            self.status_label.config(text=f"已设置起始位置: 末尾", fg="green")
        
        # 禁用按钮
        self.set_start_btn.config(state=tk.DISABLED)
    
    def load_file(self):
        """加载文件"""
        filepath = filedialog.askopenfilename(
            title="选择文本文件",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )
        
        if not filepath:
            return
        
        content = self._read_file_with_encoding(filepath)
        
        if content is not None:
            self.text_area.delete(1.0, tk.END)
            self.text_area.insert(tk.END, content)
            self.status_label.config(text=f"已加载: {filepath.split('/')[-1]}", fg="green")
        else:
            messagebox.showerror("错误", "无法读取文件，编码格式不支持!")
    
    def _read_file_with_encoding(self, filepath):
        """尝试多种编码读取文件"""
        for encoding in self.ENCODINGS:
            try:
                with open(filepath, 'r', encoding=encoding) as f:
                    return f.read()
            except (UnicodeDecodeError, UnicodeError):
                continue
        return None
    
    def highlight_char(self, index):
        """高亮指定位置的字符"""
        self.text_area.tag_remove("highlight", "1.0", tk.END)
        
        if index < 0 or index >= len(self.full_text):
            return
        
        # 计算行列位置
        line = self.full_text[:index].count('\n') + 1
        col = index - self.full_text[:index].rfind('\n') - 1
        
        start = f"{line}.{col}"
        end = f"{line}.{col + 1}"
        
        self.text_area.tag_add("highlight", start, end)
        self.text_area.tag_config("highlight", background="#FFEB3B", foreground="black", relief="solid")
        self.text_area.see(start)
        self.text_area.update()
    
    def update_progress(self, current, total):
        """更新进度条"""
        if total == 0:
            return
        
        self.progress_bar.delete("progress")
        width = self.progress_bar.winfo_width()
        progress_width = int(width * current / total)
        
        self.progress_bar.create_rectangle(0, 0, progress_width, 20, fill="#66BB6A", tags="progress")
        self.progress_bar.create_text(width // 2, 10, text=f"{current}/{total} ({current*100//total}%)", 
                                       fill="black", tags="progress")
    
    def countdown(self, seconds, callback):
        """倒计时"""
        if seconds > 0:
            self.status_label.config(text=f"{seconds}秒后开始输入，请切换到目标窗口...", fg="orange")
            self.root.after(1000, lambda: self.countdown(seconds - 1, callback))
        else:
            callback()
    
    def start_input(self):
        """开始输入"""
        self.full_text = self.text_area.get(1.0, tk.END).strip()
        
        if not self.full_text:
            messagebox.showwarning("警告", "请输入内容!")
            return
        
        self.current_index = 0
        self.text_area.tag_remove("highlight", "1.0", tk.END)
        self.update_progress(0, len(self.full_text))
        
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL, text="停止", bg="#EF5350")
        self.set_start_btn.config(state=tk.DISABLED)
        
        self.countdown(self.COUNTDOWN_SECONDS, self._do_start)
    
    def _do_start(self):
        """执行开始"""
        self.is_running = True
        self.stop_flag = False
        threading.Thread(target=self.run_input, daemon=True).start()
    
    def _do_continue(self):
        """执行继续"""
        self.is_running = True
        self.stop_flag = False
        threading.Thread(target=self.run_input, daemon=True).start()
    
    def start_listeners(self):
        """启动鼠标监听器"""
        def on_mouse_click(x, y, button, pressed):
            if pressed and self.is_running:
                self.stop_flag = True
        
        self.mouse_listener = mouse.Listener(on_click=on_mouse_click)
        self.mouse_listener.start()
    
    def stop_listeners(self):
        """停止鼠标监听器"""
        if self.mouse_listener:
            self.mouse_listener.stop()
            self.mouse_listener = None
    
    def stop_or_continue(self):
        """停止或继续"""
        if self.is_running:
            self.stop_flag = True
        else:
            self.continue_input()
    
    def stop_input(self):
        """停止输入"""
        self.is_running = False
        self.stop_listeners()
        self.start_btn.config(state=tk.NORMAL, text="从头输入", bg="#66BB6A")
        self.stop_btn.config(state=tk.NORMAL, text="继续", bg="#FFA726")
        self.set_start_btn.config(state=tk.NORMAL)
        
        if self.current_index > 0:
            self.highlight_char(self.current_index - 1)
            self.status_label.config(text=f"已停止于位置 {self.current_index} ({self.current_index*100//len(self.full_text)}%)", fg="red")
        else:
            self.status_label.config(text="已停止", fg="red")
    
    def continue_input(self):
        """继续输入"""
        if self.current_index >= len(self.full_text):
            self.status_label.config(text="输入已完成", fg="green")
            return
        
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL, text="停止", bg="#EF5350")
        self.set_start_btn.config(state=tk.DISABLED)
        
        self.countdown(self.COUNTDOWN_SECONDS, self._do_continue)
    
    def run_input(self):
        """运行输入（在子线程中）"""
        old_clipboard = pyperclip.paste()
        total_len = len(self.full_text)
        
        try:
            chars = list(self.full_text)
            skip_count = self.current_index
            first_char_input = False
            
            i = 0
            while i < len(chars):
                char = chars[i]
                
                # 跳过已输入的字符
                if skip_count > 0:
                    skip_count -= 1
                    i += 1
                    continue
                
                # 输入字符
                if char == '\n':
                    pyautogui.press('enter')
                elif char == '\t':
                    pyautogui.press('tab')
                elif char == ' ':
                    pyautogui.press('space')
                else:
                    pyperclip.copy(char)
                    pyautogui.hotkey('ctrl', 'v')
                    time.sleep(self.INPUT_DELAY)
                
                self.current_index += 1
                i += 1
                
                # 第一个字符输入后启动监听器
                if not first_char_input:
                    first_char_input = True
                    self.start_listeners()
                
                # 输入字符后再检查停止标志
                if self.stop_flag:
                    self._save_state_and_exit(old_clipboard)
                    return
                
                # 更新进度（每10个字符更新一次）
                if self.current_index % 10 == 0:
                    self.root.after(0, lambda idx=self.current_index: self.update_progress(idx, total_len))
            
            # 完成
            pyperclip.copy(old_clipboard)
            self.is_running = False
            self.root.after(0, self.on_complete)
            
        except Exception as e:
            pyperclip.copy(old_clipboard)
            self.is_running = False
            self.root.after(0, lambda: self.on_error(str(e)))
    
    def _save_state_and_exit(self, old_clipboard):
        """保存状态并退出"""
        self.stop_listeners()
        self.root.after(0, self.stop_input)
        pyperclip.copy(old_clipboard)
    
    def on_complete(self):
        """完成回调"""
        self.stop_listeners()
        self.start_btn.config(state=tk.NORMAL, text="开始输入", bg="#66BB6A")
        self.stop_btn.config(state=tk.DISABLED)
        self.set_start_btn.config(state=tk.DISABLED)
        self.status_label.config(text="输入完成!", fg="green")
        self.text_area.tag_remove("highlight", "1.0", tk.END)
        self.update_progress(len(self.full_text), len(self.full_text))
    
    def on_error(self, error_msg):
        """错误回调"""
        self.stop_listeners()
        self.start_btn.config(state=tk.NORMAL, text="开始输入", bg="#66BB6A")
        self.stop_btn.config(state=tk.DISABLED)
        self.set_start_btn.config(state=tk.DISABLED)
        self.status_label.config(text=f"发生错误: {error_msg}", fg="red")
    
    def run(self):
        """运行应用"""
        self.root.mainloop()


if __name__ == "__main__":
    app = AutoInputApp()
    app.run()
