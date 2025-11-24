import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import time
from datetime import datetime

class JWGLApp(tk.Tk):
    def __init__(self):
        super().__init__()
        # 省略已实现的初始化代码（登录、个人信息等）
        # ...

        # 抢课相关变量
        self.grab_running = False  # 抢课线程是否运行
        self.grab_thread = None    # 抢课线程
        self.grab_logs = []        # 抢课日志

        # 添加抢课功能UI
        self.create_grab_widgets()

    def create_grab_widgets(self):
        """创建抢课功能相关控件"""
        self.grab_frame = ttk.LabelFrame(self, text="抢课功能")
        # 初始隐藏，登录后显示
        self.grab_frame.pack(padx=10, pady=10, fill="x", expand=True)

        # 课程信息输入
        ttk.Label(self.grab_frame, text="教学班ID (class_id):").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.class_id_var = tk.StringVar()
        ttk.Entry(self.grab_frame, textvariable=self.class_id_var).grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(self.grab_frame, text="执行ID (do_id):").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.do_id_var = tk.StringVar()
        ttk.Entry(self.grab_frame, textvariable=self.do_id_var).grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        # 抢课参数
        ttk.Label(self.grab_frame, text="刷新间隔(秒):").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.interval_var = tk.StringVar(value="2")  # 默认2秒刷新一次
        ttk.Entry(self.grab_frame, textvariable=self.interval_var).grid(row=2, column=1, padx=5, pady=5, sticky="ew")

        # 按钮
        self.start_grab_btn = ttk.Button(self.grab_frame, text="开始抢课", command=self.start_grab)
        self.start_grab_btn.grid(row=3, column=0, padx=5, pady=10)

        self.stop_grab_btn = ttk.Button(self.grab_frame, text="停止抢课", command=self.stop_grab, state="disabled")
        self.stop_grab_btn.grid(row=3, column=1, padx=5, pady=10)

        # 抢课日志
        ttk.Label(self.grab_frame, text="抢课日志:").grid(row=4, column=0, columnspan=2, padx=5, pady=5, sticky="w")
        self.log_text = scrolledtext.ScrolledText(self.grab_frame, height=10, wrap=tk.WORD)
        self.log_text.grid(row=5, column=0, columnspan=2, padx=5, pady=5, sticky="nsew")
        self.log_text.config(state="disabled")

        # 自适应布局
        self.grab_frame.grid_columnconfigure(1, weight=1)
        self.grab_frame.grid_rowconfigure(5, weight=1)

    def log(self, message):
        """添加抢课日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_msg = f"[{timestamp}] {message}\n"
        self.grab_logs.append(log_msg)
        
        # 在UI中显示日志
        self.log_text.config(state="normal")
        self.log_text.insert(tk.END, log_msg)
        self.log_text.see(tk.END)  # 滚动到最新日志
        self.log_text.config(state="disabled")

    def start_grab(self):
        """开始抢课线程"""
        if self.grab_running:
            messagebox.showinfo("提示", "抢课已在运行中")
            return

        # 验证输入
        class_id = self.class_id_var.get().strip()
        do_id = self.do_id_var.get().strip()
        interval = self.interval_var.get().strip()

        if not class_id or not do_id:
            messagebox.showerror("错误", "教学班ID和执行ID不能为空")
            return

        try:
            interval = float(interval)
            if interval < 0.5:
                raise ValueError("间隔不能小于0.5秒")
        except ValueError:
            messagebox.showerror("错误", "请输入有效的刷新间隔（数字）")
            return

        # 更新状态
        self.grab_running = True
        self.start_grab_btn.config(state="disabled")
        self.stop_grab_btn.config(state="normal")
        self.log(f"开始抢课 - 教学班ID: {class_id}, 执行ID: {do_id}, 间隔: {interval}秒")

        # 启动抢课线程
        self.grab_thread = threading.Thread(
            target=self.grab_course_loop,
            args=(class_id, do_id, interval),
            daemon=True
        )
        self.grab_thread.start()

    def stop_grab(self):
        """停止抢课线程"""
        self.grab_running = False
        self.start_grab_btn.config(state="normal")
        self.stop_grab_btn.config(state="disabled")
        self.log("已停止抢课")

    def grab_course_loop(self, class_id, do_id, interval):
        """抢课循环（后台线程）"""
        while self.grab_running:
            try:
                # 1. 先查询课程余量（关键：监控是否有空位）
                course_status = self.check_course_status(class_id, do_id)
                if course_status["code"] != 1000:
                    self.log(f"查询课程状态失败: {course_status['msg']}")
                    time.sleep(interval)
                    continue

                # 解析课程状态
                capacity = course_status["data"].get("capacity", 0)  # 总容量
                selected = course_status["data"].get("selected_number", 0)  # 已选人数
                remaining = capacity - selected  # 剩余名额

                self.log(f"课程状态 - 总容量: {capacity}, 已选: {selected}, 剩余: {remaining}")

                # 2. 有剩余名额时尝试抢课
                if remaining > 0:
                    self.log("发现剩余名额，尝试抢课...")
                    result = self.select_course(class_id, do_id)
                    
                    if result["code"] == 1000:
                        self.log("🎉 抢课成功！")
                        self.grab_running = False  # 成功后自动停止
                        # 主线程显示成功消息
                        self.after(0, lambda: messagebox.showinfo("成功", "抢课成功！"))
                        break
                    else:
                        self.log(f"抢课失败: {result['msg']}（错误码: {result['code']}）")

                # 3. 等待下一次检查
                time.sleep(interval)

            except Exception as e:
                self.log(f"抢课出错: {str(e)}")
                time.sleep(interval)

        # 循环结束后更新UI状态
        self.after(0, lambda: self.stop_grab())

    def check_course_status(self, class_id, do_id):
        """查询课程状态（余量、已选人数等）
        实际实现需根据API文档调整，这里是示例逻辑
        """
        try:
            # 假设API有查询课程状态的方法
            # 参考字段: capacity(容量), selected_number(已选人数)
            result = self.stu_client.get_course_status(class_id, do_id)
            return result
        except Exception as e:
            return {"code": 999, "msg": f"查询失败: {str(e)}"}

    def select_course(self, class_id, do_id):
        """发送选课请求
        实际参数需根据API文档调整，参考选课相关字段
        """
        try:
            # 构造选课参数（根据提供的JSON字段）
            select_params = {
                "class_id": class_id,       # 教学班ID
                "do_id": do_id,             # 执行ID
                "kklxdm": "",               # 板块课ID（可选）
                "teacher_id": "",           # 教师ID（可选）
                # 其他可能需要的参数...
            }

            # 调用API选课方法
            result = self.stu_client.select_course(** select_params)
            return result
        except Exception as e:
            return {"code": 999, "msg": f"选课请求失败: {str(e)}"}

    # 省略已实现的其他方法（login, show_info, show_schedule等）
    # ...