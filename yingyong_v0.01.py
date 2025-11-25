import tkinter as tk
from tkinter import ttk, messagebox
from zfn_api import Client
import base64
from PIL import Image, ImageTk
import io
import json
import os

# --- 核心修改：使用绝对路径 ---
# 获取当前脚本所在的目录
CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

class JWGLApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("教务系统查询工具")
        self.geometry("450x400")
        self.stu_client = None
        self.login_data = None
        self.logged_in = False
        self.username = ""

        # 尝试加载本地cookies并自动登录
        self.auto_login()
        self.create_widgets()

    def auto_login(self):
        """加载本地cookies并尝试自动登录"""
        print(f"[调试] 正在检查配置文件: {CONFIG_FILE}")
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    self.username = config.get("username", "")
                    cookies = config.get("cookies", {})
                    if cookies and self.username:
                        base_url = "http://jwglxt.xzit.edu.cn/jwglxt/xtgl"
                        self.stu_client = Client(
                            cookies=cookies,
                            base_url=base_url,
                            timeout=20
                        )
                        # 验证cookies是否有效
                        print("[调试] 验证cookies有效性...")
                        test_result = self.stu_client.get_info()
                        if test_result.get("code") == 1000:
                            self.logged_in = True
                            print(f"[调试] 自动登录成功！用户: {self.username}")
                        else:
                            print(f"[调试] cookies失效。错误: {test_result.get('msg')}")
                            os.remove(CONFIG_FILE)
            except Exception as e:
                print(f"[调试] 自动登录失败: {e}")
                if os.path.exists(CONFIG_FILE):
                    os.remove(CONFIG_FILE)
        else:
            print("[调试] 未找到配置文件，跳过自动登录。")

    def save_cookies(self, username, cookies):
        """保存cookies到本地"""
        config = {
            "username": username,
            "cookies": cookies
        }
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            print(f"[调试] cookies已保存到: {CONFIG_FILE}")
        except Exception as e:
            messagebox.showerror("错误", f"保存登录状态失败: {e}")

    def delete_cookies(self):
        """删除本地cookies（退出登录）"""
        if os.path.exists(CONFIG_FILE):
            os.remove(CONFIG_FILE)
            print("[调试] 已删除配置文件。")
        self.stu_client = None
        self.logged_in = False
        self.username = ""
        self.update_widgets_state()

    def create_widgets(self):
        # 登录框架
        self.login_frame = ttk.LabelFrame(self, text="登录")
        self.login_frame.pack(padx=10, pady=10, fill="x")

        ttk.Label(self.login_frame, text="学号:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.username_var = tk.StringVar(value=self.username)
        self.username_entry = ttk.Entry(self.login_frame, textvariable=self.username_var)
        self.username_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(self.login_frame, text="密码:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.password_var = tk.StringVar()
        self.password_entry = ttk.Entry(self.login_frame, textvariable=self.password_var, show="*")
        self.password_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        # 验证码框架
        self.captcha_frame = ttk.LabelFrame(self, text="验证码")
        self.captcha_label = ttk.Label(self.captcha_frame)
        self.captcha_var = tk.StringVar()
        self.captcha_entry = ttk.Entry(self.captcha_frame, textvariable=self.captcha_var)

        self.login_button = ttk.Button(self.login_frame, text="登录", command=self.login)
        self.login_button.grid(row=2, column=0, columnspan=2, pady=10)

        # 功能按钮框架
        self.functions_frame = ttk.LabelFrame(self, text="功能")
        self.info_button = ttk.Button(self.functions_frame, text="查看个人信息", command=self.show_info)
        self.schedule_button = ttk.Button(self.functions_frame, text="查看课表", command=self.show_schedule)
        self.logout_button = ttk.Button(self.functions_frame, text="退出登录", command=self.delete_cookies)

        # 状态栏
        self.status_var = tk.StringVar(value="未登录" if not self.logged_in else f"已登录：{self.username}")
        self.status_label = ttk.Label(self, textvariable=self.status_var, anchor="w")
        self.status_label.pack(padx=10, pady=5, fill="x")

        self.update_widgets_state()

    def update_widgets_state(self):
        """根据登录状态更新控件状态"""
        if self.logged_in:
            self.login_frame.pack_forget()
            self.functions_frame.pack(padx=10, pady=10, fill="x", expand=True)
            self.info_button.pack(pady=8, padx=10, fill="x")
            self.schedule_button.pack(pady=8, padx=10, fill="x")
            self.logout_button.pack(pady=8, padx=10, fill="x")
            self.status_var.set(f"已登录：{self.username}")
        else:
            self.functions_frame.pack_forget()
            self.login_frame.pack(padx=10, pady=10, fill="x")
            self.username_entry.config(state="normal")
            self.password_entry.config(state="normal")
            self.login_button.config(state="normal")
            self.status_var.set("未登录")

    # --- 核心修改：简化登录逻辑 ---
    def login(self):
        # 如果已经登录，直接返回
        if self.logged_in:
            messagebox.showinfo("提示", "您已登录，无需重复操作。")
            return

        username = self.username_var.get().strip()
        password = self.password_var.get().strip()
        kaptcha = self.captcha_var.get().strip()

        print(f"[调试] 登录按钮触发。学号: '{username}', 密码长度: {len(password)}, 验证码: '{kaptcha}'")

        # 首次登录，必须有学号和密码
        if not self.login_data and (not username or not password):
            messagebox.showerror("错误", "学号和密码不能为空！")
            return

        # 提交验证码时，必须有验证码
        if self.login_data and not kaptcha:
            messagebox.showerror("错误", "请输入验证码！")
            return

        if not self.stu_client:
            base_url = "http://jwglxt.xzit.edu.cn/jwglxt/xtgl"
            self.stu_client = Client(base_url=base_url, timeout=20)

        try:
            # 如果有验证码信息，说明是第二次登录
            if self.login_data and kaptcha:
                self.login_data["kaptcha"] = kaptcha
                login_result = self.stu_client.login_with_kaptcha(**self.login_data)
            else:
                # 第一次登录，尝试获取验证码
                login_result = self.stu_client.login(username, password)

            if login_result["code"] == 1001:
                # 需要验证码，显示验证码界面
                self.login_data = login_result["data"]
                self.captcha_frame.pack(padx=10, pady=5, fill="x")
                image_data = base64.b64decode(login_result["data"]["kaptcha_pic"])
                image = Image.open(io.BytesIO(image_data))
                image.thumbnail((150, 50), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(image)
                self.captcha_label.config(image=photo)
                self.captcha_label.image = photo
                self.captcha_label.pack(side="left", padx=5)
                self.captcha_entry.pack(side="right", padx=5, fill="x", expand=True)
                self.login_button.config(text="提交验证码")
                self.username_entry.config(state="disabled")
                self.password_entry.config(state="disabled")

            elif login_result["code"] == 1000:
                # 登录成功
                self.logged_in = True
                self.username = username
                self.save_cookies(username, login_result["data"]["cookies"])
                self.captcha_frame.pack_forget()
                self.update_widgets_state()
                messagebox.showinfo("成功", "登录成功！")

            else:
                messagebox.showerror("失败", f"{login_result['msg']}（错误码：{login_result['code']}）")

        except Exception as e:
            messagebox.showerror("错误", f"登录异常：{str(e)}")
            self.stu_client = None
    def show_info(self):
        """根据你提供的真实数据结构，正确显示个人信息"""
        if not self.logged_in or not self.stu_client:
            messagebox.showerror("错误", "请先登录系统")
            return

        try:
            # 调用API获取个人信息
            info_result = self.stu_client.get_info()
            
            if info_result["code"] == 1000:
                info_data = info_result["data"]  # 提取数据部分
                
                # 严格按照你提供的字段名构建信息（一一对应）
                info_str = [
                    "===== 个人基本信息 =====",
                    f"学号：{info_data.get('sid', '未知')}",  # 对应你的 'sid' 字段
                    f"姓名：{info_data.get('name', '未知')}",  # 对应你的 'name' 字段
                    f"出生日期：{info_data.get('birthday', '未知')}",  # 对应 'birthday'
                    f"身份证号：{info_data.get('id_number', '未知')}",  # 对应 'id_number'
                    f"民族：{info_data.get('nationality', '未知')}",  # 对应 'nationality'
                    f"政治面貌：{info_data.get('politics_status', '未知')}",  # 对应 'politics_status'
                    "",
                    "===== 学籍信息 =====",
                    f"学院：{info_data.get('college_name', '未知')}",  # 对应 'college_name'
                    f"专业：{info_data.get('major_name', '未知')}",  # 对应 'major_name'
                    f"班级：{info_data.get('class_name', '未知')}",  # 对应 'class_name'
                    f"学历：{info_data.get('education', '未知')}",  # 对应 'education'
                    f"入学时间：{info_data.get('enrollment_date', '未知')}",  # 对应 'enrollment_date'
                    f"状态：{info_data.get('status', '未知')}",  # 对应 'status'
                    "",
                    "===== 联系方式 =====",
                    f"手机号：{info_data.get('phone_number', '未知')}",  # 对应 'phone_number'
                    f"准考证号：{info_data.get('candidate_number', '未知')}"  # 对应 'candidate_number'
                ]
                
                # 显示信息（用换行符拼接）
                messagebox.showinfo("个人信息", "\n".join(info_str))
            else:
                messagebox.showerror("失败", f"获取信息失败：{info_result['msg']}")
        
        except Exception as e:
            messagebox.showerror("错误", f"获取信息异常：{str(e)}")

    def show_schedule(self):
        """显示课表信息（基于提供的 get_schedule 方法结构）"""
        if not self.logged_in or not self.stu_client:
            messagebox.showerror("错误", "请先登录系统")
            return

        # 默认查询2024年第1学期（可根据需要调整）
        default_year = 2024
        default_term = 1  # 1=上学期，2=下学期

        try:
            # 调用API获取课表（使用默认年份和学期）
            schedule_result = self.stu_client.get_schedule(default_year, default_term)
            
            # 处理API返回的各种状态
            if schedule_result["code"] == 1000:
                schedule_data = schedule_result["data"]  # 提取课表数据
                courses = schedule_data.get("courses", [])  # 课程列表
                
                if not courses:
                    messagebox.showinfo("课表", f"{default_year}年第{default_term}学期暂无课程")
                    return
                
                # 准备课表信息字符串
                schedule_str = [
                    f"===== {default_year}年第{default_term}学期课表 =====",
                    f"学号：{schedule_data.get('sid', '未知')}",
                    f"姓名：{schedule_data.get('name', '未知')}",
                    f"课程总数：{schedule_data.get('count', 0)}\n"
                ]
                
                # 星期转换（1=周一，2=周二...7=周日）
                weekday_map = {1: "周一", 2: "周二", 3: "周三", 4: "周四", 5: "周五", 6: "周六", 7: "周日"}
                
                # 遍历课程，拼接信息
                for idx, course in enumerate(courses, 1):
                    # 从课程数据中提取字段（严格对应 get_schedule 返回的结构）
                    course_name = course.get("title", "未知课程")  # 课程名
                    teacher = course.get("teacher", "未知教师")    # 教师
                    weekday = weekday_map.get(course.get("weekday"), "未知星期")  # 星期
                    class_time = course.get("time", "未知时间")    # 上课时间（如"1-2节"）
                    weeks = course.get("weeks", "未知周次")        # 周次（如"1-16周"）
                    place = course.get("place", "未知地点")        # 上课地点
                    credit = course.get("credit", "未知学分")      # 学分
                    
                    # 添加到课表字符串
                    schedule_str.append(
                        f"{idx}. {course_name}\n"
                        f"   教师：{teacher} | 学分：{credit}\n"
                        f"   时间：{weekday} {class_time} | 周次：{weeks}\n"
                        f"   地点：{place}\n"
                    )
                
                # 合并所有信息
                full_schedule = "\n".join(schedule_str)
                
                # 课表过长时用滚动窗口显示（超过800字符）
                if len(full_schedule) > 800:
                    top = tk.Toplevel(self)
                    top.title(f"{default_year}年第{default_term}学期课表")
                    top.geometry("600x600")  # 窗口大小
                    
                    # 添加文本框和滚动条
                    text_widget = tk.Text(top, wrap="word", font=("SimHei", 10))
                    text_widget.insert("end", full_schedule)
                    text_widget.config(state="disabled")  # 只读
                    
                    scrollbar = ttk.Scrollbar(top, command=text_widget.yview)
                    text_widget.config(yscrollcommand=scrollbar.set)
                    
                    # 布局
                    text_widget.pack(side="left", fill="both", expand=True, padx=5, pady=5)
                    scrollbar.pack(side="right", fill="y")
                else:
                    # 内容较短时直接用消息框显示
                    messagebox.showinfo("课表", full_schedule)
            
            # 处理API返回的错误
            elif schedule_result["code"] == 1005:
                messagebox.showinfo("课表", f"{default_year}年第{default_term}学期暂无课程数据")
            elif schedule_result["code"] == 1006:
                messagebox.showerror("错误", "登录已过期，请重新登录")
            elif schedule_result["code"] == 2333:
                messagebox.showerror("错误", "教务系统异常，请稍后再试")
            else:
                messagebox.showerror("失败", f"获取课表失败：{schedule_result['msg']}")
        
        except Exception as e:
            messagebox.showerror("错误", f"获取课表异常：{str(e)}")



if __name__ == "__main__":
    app = JWGLApp()
    app.mainloop()