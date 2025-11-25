import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, Listbox, MULTIPLE
import webbrowser
from zfn_api import Client
import base64
from PIL import Image, ImageTk
import io
import json
import os
import threading
import time
from datetime import datetime
import re
import urllib.parse as parse
import winsound  # 用于播放音效（Windows系统）

# --- 基础配置 ---
CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
SOUND_ENABLE = True  # 是否启用音效
DEBUG_MODE = True

# 音效文件路径（请确保这些文件存在于项目根目录的sounds文件夹中）
SOUND_DIR = os.path.join(CONFIG_DIR, "sounds")
PASS_SOUND = os.path.join(SOUND_DIR, "pass.wav")       # 重修全部及格音效
FAIL_SOUND = os.path.join(SOUND_DIR, "fail.wav")       # 重修存在不及格音效
ENROLL_SUCCESS_SOUND = os.path.join(SOUND_DIR, "enroll_success.wav")  # 选课成功音效
ENROLL_FAIL_SOUND = os.path.join(SOUND_DIR, "enroll_fail.wav")        # 选课失败音效

class JWGLApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("正方教务系统 - 综合工具（终极版）")
        self.geometry("600x700")
        self.stu_client = None
        self.login_data = None
        self.logged_in = False
        self.username = ""

        self.grab_running = False
        self.grab_thread = None
        self.selected_course = None
        self.course_list_data = []
        self.block_names = {}
        self.link_tags = {}  # 存储超链接标签与URL的映射

        # 初始化音效文件夹
        self.init_sound_folder()

        self.auto_login()
        self.create_widgets()
        if self.logged_in and DEBUG_MODE:
            print("[调试] 登录成功，尝试获取板块名字（如非选课阶段，此步骤可能失败）")
            threading.Thread(target=self.fetch_block_names, daemon=True).start()

    def init_sound_folder(self):
        """初始化音效文件夹，若不存在则创建"""
        if not os.path.exists(SOUND_DIR):
            os.makedirs(SOUND_DIR)
            print(f"[提示] 已创建音效文件夹：{SOUND_DIR}")
            print("[提示] 请将音效文件（pass.wav、fail.wav、enroll_success.wav、enroll_fail.wav）放入该文件夹")

    def play_sound(self, sound_path):
        """播放音效（单独线程播放，避免阻塞UI）"""
        if not SOUND_ENABLE:
            return
        if not os.path.exists(sound_path):
            print(f"[警告] 音效文件不存在：{sound_path}")
            return

        def _play():
            try:
                winsound.PlaySound(sound_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
            except Exception as e:
                print(f"[错误] 播放音效失败：{e}")

        threading.Thread(target=_play, daemon=True).start()

    def auto_login(self):
        if DEBUG_MODE:
            print(f"[调试] 检查配置文件: {CONFIG_FILE}")
        try:
            if os.path.exists(CONFIG_FILE):
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
                        if DEBUG_MODE:
                            print("[调试] 验证cookies有效性...")
                        try:
                            test_result = self.stu_client.get_info()
                            if test_result.get("code") == 1000:
                                self.logged_in = True
                                if DEBUG_MODE:
                                    print(f"[调试] 自动登录成功：{self.username}")
                            else:
                                if DEBUG_MODE:
                                    print(f"[调试] cookies失效：{test_result.get('msg', '未知错误')}")
                                os.remove(CONFIG_FILE)
                        except Exception as e:
                            if DEBUG_MODE:
                                print(f"[调试] 验证cookies异常：{e}")
                            os.remove(CONFIG_FILE)
            else:
                if DEBUG_MODE:
                    print("[调试] 无配置文件，跳过自动登录")
        except Exception as e:
            if DEBUG_MODE:
                print(f"[调试] 自动登录失败：{e}")
            if os.path.exists(CONFIG_FILE):
                try:
                    os.remove(CONFIG_FILE)
                except:
                    pass

    def save_cookies(self, username, cookies):
        try:
            config = {"username": username, "cookies": cookies}
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            if DEBUG_MODE:
                print(f"[调试] cookies保存至: {CONFIG_FILE}")
        except PermissionError:
            messagebox.showerror("错误", "保存登录状态失败：无写入权限，请以管理员身份运行")
        except Exception as e:
            messagebox.showerror("错误", f"保存登录状态失败: {e}")

    def delete_cookies(self):
        try:
            if os.path.exists(CONFIG_FILE):
                os.remove(CONFIG_FILE)
                if DEBUG_MODE:
                    print("[调试] 已删除配置文件")
        except PermissionError:
            messagebox.showerror("错误", "退出登录失败：无删除权限，请以管理员身份运行")
        except Exception as e:
            if DEBUG_MODE:
                print(f"[调试] 删除配置文件失败：{e}")
        finally:
            self.stu_client = None
            self.logged_in = False
            self.username = ""
            self.update_widgets_state()

    def create_widgets(self):
        # 状态栏（固定在顶部）
        self.status_var = tk.StringVar(value="未登录" if not self.logged_in else f"已登录：{self.username}")
        self.status_label = ttk.Label(self, textvariable=self.status_var, anchor="w")
        self.status_label.pack(side="top", padx=10, pady=5, fill="x")

        # 登录框
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

        self.captcha_frame = ttk.LabelFrame(self, text="验证码")
        self.captcha_label = ttk.Label(self.captcha_frame)
        self.captcha_var = tk.StringVar()
        self.captcha_entry = ttk.Entry(self.captcha_frame, textvariable=self.captcha_var)

        self.login_button = ttk.Button(self.login_frame, text="登录", command=self.login)
        self.login_button.grid(row=2, column=0, columnspan=2, pady=10)

        # 功能选择框
        self.functions_frame = ttk.LabelFrame(self, text="功能选择")
        
        # 第一行
        self.info_button = ttk.Button(self.functions_frame, text="查看个人信息", command=self.show_info, width=20)
        self.schedule_button = ttk.Button(self.functions_frame, text="查看课表", command=self.show_schedule, width=20)
        self.info_button.grid(row=0, column=0, padx=5, pady=5)
        self.schedule_button.grid(row=0, column=1, padx=5, pady=5)

        # 第二行
        self.grades_button = ttk.Button(self.functions_frame, text="查询需重修课程", command=self.show_failed_grades, width=20)
        self.enroll_button = ttk.Button(self.functions_frame, text="进入选课抢课", command=self.show_enroll_tab, width=20)
        self.grades_button.grid(row=1, column=0, padx=5, pady=5)
        self.enroll_button.grid(row=1, column=1, padx=5, pady=5)
        
        # 第三行
        self.bounty_button = ttk.Button(self.functions_frame, text="悬赏榜", command=self.show_bounty, width=20)
        self.about_button = ttk.Button(self.functions_frame, text="关于", command=self.show_about, width=20)
        self.bounty_button.grid(row=2, column=0, padx=5, pady=5)
        self.about_button.grid(row=2, column=1, padx=5, pady=5)

        # 第四行
        self.logout_button = ttk.Button(self.functions_frame, text="退出登录", command=self.delete_cookies, width=43)
        self.logout_button.grid(row=3, column=0, columnspan=2, padx=5, pady=5)
        
        self.functions_frame.pack(padx=10, pady=10, fill="both", expand=True)

        # 选课界面
        self.enroll_tab_frame = ttk.LabelFrame(self, text="正方系统选课抢课")
        ttk.Label(self.enroll_tab_frame, text="选课板块:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.block_var = tk.StringVar(value="1")
        self.block_combo = ttk.Combobox(self.enroll_tab_frame, textvariable=self.block_var,
                                        values=[f"板块{i}" for i in range(1, 11)], state="readonly")
        self.block_combo.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.get_courses_btn = ttk.Button(self.enroll_tab_frame, text="获取该板块课程", command=self.fetch_block_courses)
        self.get_courses_btn.grid(row=0, column=2, padx=5, pady=5)
        ttk.Label(self.enroll_tab_frame, text="可选课程列表:").grid(row=1, column=0, columnspan=3, padx=5, pady=5, sticky="w")
        self.course_listbox = Listbox(self.enroll_tab_frame, height=8, selectmode=MULTIPLE)
        self.course_listbox.grid(row=2, column=0, columnspan=3, padx=5, pady=5, sticky="nsew")
        self.course_scroll = ttk.Scrollbar(self.enroll_tab_frame, command=self.course_listbox.yview)
        self.course_listbox.config(yscrollcommand=self.course_scroll.set)
        self.course_scroll.grid(row=2, column=3, sticky="ns")
        ttk.Label(self.enroll_tab_frame, text="刷新间隔(秒):").grid(row=3, column=0, padx=5, pady=5, sticky="w")
        self.interval_var = tk.StringVar(value="2.0")
        self.interval_entry = ttk.Entry(self.enroll_tab_frame, textvariable=self.interval_var)
        self.interval_entry.grid(row=3, column=1, padx=5, pady=5, sticky="ew")
        self.start_grab_btn = ttk.Button(self.enroll_tab_frame, text="开始抢选中课程", command=self.start_grab, state="disabled")
        self.start_grab_btn.grid(row=3, column=2, padx=5, pady=5)
        self.stop_grab_btn = ttk.Button(self.enroll_tab_frame, text="停止抢课", command=self.stop_grab, state="disabled")
        self.stop_grab_btn.grid(row=3, column=3, padx=5, pady=5)
        self.back_btn = ttk.Button(self.enroll_tab_frame, text="返回功能选择", command=self.back_to_functions)
        self.back_btn.grid(row=4, column=0, columnspan=4, pady=5)
        ttk.Label(self.enroll_tab_frame, text="抢课日志:").grid(row=5, column=0, columnspan=4, padx=5, pady=5, sticky="w")
        self.log_text = scrolledtext.ScrolledText(self.enroll_tab_frame, height=12, wrap=tk.WORD)
        self.log_text.grid(row=6, column=0, columnspan=4, padx=5, pady=5, sticky="nsew")
        self.log_text.config(state="disabled")

        try:
            self.enroll_tab_frame.grid_columnconfigure(1, weight=1)
            self.enroll_tab_frame.grid_rowconfigure(2, weight=1)
            self.enroll_tab_frame.grid_rowconfigure(6, weight=1)
            self.functions_frame.grid_columnconfigure(0, weight=1)
            self.functions_frame.grid_columnconfigure(1, weight=1)
        except:
            pass

        self.update_widgets_state()

    def update_widgets_state(self):
        try:
            if self.logged_in:
                self.login_frame.pack_forget()
                self.enroll_tab_frame.pack_forget()
                self.functions_frame.pack(padx=10, pady=10, fill="both", expand=True)
                self.status_var.set(f"已登录：{self.username}")
            else:
                self.functions_frame.pack_forget()
                self.enroll_tab_frame.pack_forget()
                self.login_frame.pack(padx=10, pady=10, fill="x")
                self.status_var.set("未登录")
        except Exception as e:
            if DEBUG_MODE:
                print(f"[调试] 更新UI状态失败：{e}")

    def show_enroll_tab(self):
        try:
            self.functions_frame.pack_forget()
            self.enroll_tab_frame.pack(padx=10, pady=10, fill="both", expand=True)
            self.status_var.set("选课模式 - 先选择板块并获取课程")
        except Exception as e:
            if DEBUG_MODE:
                print(f"[调试] 切换选课界面失败：{e}")
            messagebox.showerror("错误", "切换界面失败，请重试")

    def back_to_functions(self):
        try:
            if self.grab_running:
                self.stop_grab()
            self.enroll_tab_frame.pack_forget()
            self.functions_frame.pack(padx=10, pady=10, fill="both", expand=True)
            self.status_var.set(f"已登录：{self.username}")
        except Exception as e:
            if DEBUG_MODE:
                print(f"[调试] 返回功能界面失败：{e}")
            messagebox.showerror("错误", "返回界面失败，请重试")

    def login(self):
        if self.logged_in:
            messagebox.showinfo("提示", "已登录，无需重复操作")
            return
        username = self.username_var.get().strip()
        password = self.password_var.get().strip()
        kaptcha = self.captcha_var.get().strip()
        if not username or not password:
            messagebox.showerror("错误", "学号/密码不能为空")
            return
        if not self.stu_client:
            base_url = "http://218.3.178.51/jwglxt/xtgl"
            try:
                self.stu_client = Client(base_url=base_url, timeout=20)
            except Exception as e:
                messagebox.showerror("错误", f"初始化失败：{e}")
                return
        try:
            if self.login_data and kaptcha:
                self.login_data["kaptcha"] = kaptcha
                login_result = self.stu_client.login_with_kaptcha(**self.login_data)
            else:
                login_result = self.stu_client.login(username, password)
            if login_result["code"] == 1001:
                self.login_data = login_result["data"]
                self.captcha_frame.pack(padx=10, pady=5, fill="x")
                try:
                    image_data = base64.b64decode(login_result["data"]["kaptcha_pic"])
                    image = Image.open(io.BytesIO(image_data))
                    image.thumbnail((150, 50), Image.Resampling.LANCZOS)
                    photo = ImageTk.PhotoImage(image)
                    self.captcha_label.config(image=photo)
                    self.captcha_label.image = photo
                except Exception as e:
                    if DEBUG_MODE:
                        print(f"[调试] 显示验证码失败：{e}")
                    self.captcha_label.config(text="验证码加载失败，请手动刷新")
                self.captcha_label.pack(side="left", padx=5)
                self.captcha_entry.pack(side="right", padx=5, fill="x", expand=True)
                self.login_button.config(text="提交验证码")
                self.username_entry.config(state="disabled")
                self.password_entry.config(state="disabled")
            elif login_result["code"] == 1000:
                self.logged_in = True
                self.username = username
                self.save_cookies(username, login_result["data"]["cookies"])
                self.captcha_frame.pack_forget()
                self.update_widgets_state()
                messagebox.showinfo("成功", "登录成功！")
                if DEBUG_MODE:
                    print("[调试] 开始获取板块名字")
                threading.Thread(target=self.fetch_block_names, daemon=True).start()
            else:
                messagebox.showerror("失败", f"{login_result['msg']}（错误码：{login_result['code']}）")
        except Exception as e:
            messagebox.showerror("错误", f"登录异常：{str(e)}")
            if DEBUG_MODE:
                print(f"[调试] 登录异常详情：{e}")
            self.stu_client = None

    def fetch_block_names(self):
        if not self.stu_client:
            return
        self.log("正在获取板块名字...")
        try:
            url_head = parse.urljoin(
                self.stu_client.base_url,
                "xsxk/zzxkyzb_cxZzxkYzbIndex.html?gnmkdm=N253512&layout=default"
            )
            req_head_data = self.stu_client.sess.get(
                url_head,
                headers=self.stu_client.headers,
                cookies=self.stu_client.cookies,
                timeout=self.stu_client.timeout
            )
            if req_head_data.status_code != 200:
                self.log(f"获取板块名字失败：教务系统异常，状态码: {req_head_data.status_code}")
                return
            doc = self.stu_client.pq(req_head_data.text)
            block_tab_texts = [tab.text().strip() for tab in doc("a[role='tab']").items() if tab.text().strip()]
            for i, text in enumerate(block_tab_texts):
                self.block_names[i+1] = text
            updated_options = []
            for i in range(1, 11):
                if i in self.block_names:
                    updated_options.append(f"{self.block_names[i]}({i})")
                else:
                    updated_options.append(f"板块{i}")
            self.block_combo["values"] = updated_options
            self.log(f"成功获取{len(self.block_names)}个板块名字")
        except AttributeError as e:
            if DEBUG_MODE:
                print(f"[调试] 板块名字获取异常（非选课阶段可能出现）: {e}")
            self.log("获取板块名字失败：当前可能非选课阶段或教务系统接口变更。")
        except Exception as e:
            self.log(f"获取板块名字异常：{str(e)}")
            if DEBUG_MODE:
                print(f"[调试] 板块名字获取异常：{e}")

    def show_info(self):
        if not self.logged_in or not self.stu_client:
            messagebox.showerror("错误", "请先登录")
            return
        try:
            info_result = self.stu_client.get_info()
            if info_result["code"] == 1000:
                info_data = info_result["data"]
                info_str = [
                    "===== 个人信息 =====",
                    f"学号：{info_data.get('sid', '未知')}",
                    f"姓名：{info_data.get('name', '未知')}",
                    f"学院：{info_data.get('college_name', '未知')}",
                    f"专业：{info_data.get('major_name', '未知')}",
                    f"班级：{info_data.get('class_name', '未知')}"
                ]
                messagebox.showinfo("个人信息", "\n".join(info_str))
            else:
                messagebox.showerror("失败", f"获取信息失败：{info_result['msg']}")
        except KeyError as e:
            messagebox.showerror("错误", f"数据格式异常：缺少字段{str(e)}")
        except Exception as e:
            messagebox.showerror("错误", f"异常：{str(e)}")
            if DEBUG_MODE:
                print(f"[调试] 个人信息获取异常：{e}")

    def _get_current_school_year_term(self):
        now = datetime.now()
        current_month = now.month
        if current_month >= 9:
            return now.year, 1
        else:
            return now.year - 1, 2

    def show_schedule(self):
        if not self.logged_in or not self.stu_client:
            messagebox.showerror("错误", "请先登录")
            return
        year, term = self._get_current_school_year_term()
        self.status_var.set(f"正在查询 {year}-{year+1}学年第{term}学期 课表...")
        def _query_schedule():
            try:
                schedule_result = self.stu_client.get_schedule(year, term)
                self.after(0, lambda: self.on_schedule_fetched(schedule_result, year, term))
            except Exception as e:
                self.after(0, lambda err=e: messagebox.showerror("错误", f"查询课表异常: {err}"))
                self.after(0, lambda: self.status_var.set(f"已登录：{self.username}"))
        threading.Thread(target=_query_schedule, daemon=True).start()

    def on_schedule_fetched(self, result, year, term):
        self.status_var.set(f"已登录：{self.username}")
        if result["code"] == 1000:
            schedule_data = result["data"]
            courses = schedule_data.get("courses", [])
            if not courses:
                messagebox.showinfo("课表", f"{year}-{year+1}学年第{term}学期暂无课程数据")
                return
            schedule_str = [f"===== {year}-{year+1}学年第{term}学期课表 ====="]
            weekday_map = {1: "周一", 2: "周二", 3: "周三", 4: "周四", 5: "周五", 6: "周六", 7: "周日"}
            for idx, course in enumerate(courses, 1):
                course_name = course.get("title", "未知课程")
                teacher = course.get("teacher", "未知")
                weekday = weekday_map.get(course.get("weekday"), "未知")
                class_time = course.get("time", "未知")
                place = course.get("place", "未知地点")
                schedule_str.append(
                    f"{idx}. {course_name}\n"
                    f"   教师：{teacher} | 时间：{weekday} {class_time}\n"
                    f"   地点：{place}"
                )
            full_schedule = "\n".join(schedule_str)
            if len(full_schedule) > 800:
                top = tk.Toplevel(self)
                top.title("课表详情")
                top.geometry("600x600")
                text = tk.Text(top, wrap="word")
                text.insert("end", full_schedule)
                text.config(state="disabled")
                scroll = ttk.Scrollbar(top, command=text.yview)
                text.config(yscrollcommand=scroll.set)
                text.pack(side="left", fill="both", expand=True)
                scroll.pack(side="right", fill="y")
            else:
                messagebox.showinfo("课表", full_schedule)
        elif result["code"] == 1005:
            messagebox.showinfo("课表", f"{year}-{year+1}学年第{term}学期暂无课程数据")
        elif result["code"] == 1006:
            messagebox.showerror("错误", "登录已过期，请重新登录")
        else:
            messagebox.showerror("失败", f"获取课表失败：{result['msg']}")

    def fetch_block_courses(self):
        if not self.logged_in or not self.stu_client:
            messagebox.showerror("错误", "请先登录")
            return
        self.course_listbox.delete(0, tk.END)
        self.course_list_data.clear()
        selected_text = self.block_var.get()
        try:
            block_num = re.findall(r"\d+", selected_text)[0]
            block = int(block_num)
        except:
            messagebox.showerror("错误", "请选择有效的板块")
            return
        self.log(f"正在获取【{selected_text}】的课程列表...")
        try:
            year, _ = self._get_current_school_year_term()
            term = 1
            courses_result = self.stu_client.get_block_courses(year, term, block)
            if courses_result["code"] != 1000:
                self.log(f"获取课程失败：{courses_result['msg']}")
                messagebox.showerror("失败", f"获取课程列表失败：{courses_result['msg']}")
                return
            self.course_list_data = courses_result["data"].get("courses", [])
            if not self.course_list_data:
                messagebox.showinfo("提示", f"【{selected_text}】暂无可选课程")
                return
            for idx, course in enumerate(self.course_list_data, 1):
                course_name = course.get("title", "未知课程")
                teacher = course.get("teacher", "未知教师")
                self.course_listbox.insert(tk.END, f"{idx}. {course_name}（{teacher}）")
            self.start_grab_btn.config(state="normal")
            self.log(f"成功获取{len(self.course_list_data)}门课程")
        except KeyError as e:
            messagebox.showerror("错误", f"数据格式异常：缺少字段{str(e)}")
            self.log(f"数据格式异常：缺少字段{str(e)}")
        except Exception as e:
            messagebox.showerror("错误", f"解析课程列表异常：{str(e)}")
            self.log(f"异常：{str(e)}")
            if DEBUG_MODE:
                print(f"[调试] 课程获取异常：{e}")

    def show_failed_grades(self):
        if not self.logged_in or not self.stu_client:
            messagebox.showerror("错误", "请先登录！")
            return
        year, term = self._get_current_school_year_term()
        if term == 1:
            query_year = year - 1
            query_term = 2
        else:
            query_year = year
            query_term = 1
        self.status_var.set(f"正在查询 {query_year}-{query_year+1}学年第{query_term}学期 成绩...")
        def _query_grades():
            try:
                result = self.stu_client.get_grade(query_year, query_term)
                self.after(0, lambda: self.on_grades_fetched(result, query_year, query_term))
            except AttributeError:
                try:
                    result = self.stu_client.get_grades(query_year, query_term)
                    self.after(0, lambda: self.on_grades_fetched(result, query_year, query_term))
                except Exception as e:
                    self.after(0, lambda err=e: messagebox.showerror("错误", f"查询成绩异常: 请检查zfn_api版本, {err}"))
                    self.after(0, lambda: self.status_var.set(f"已登录：{self.username}"))
            except Exception as e:
                self.after(0, lambda err=e: messagebox.showerror("错误", f"查询成绩异常: {err}"))
                self.after(0, lambda: self.status_var.set(f"已登录：{self.username}"))
        threading.Thread(target=_query_grades, daemon=True).start()

    def on_grades_fetched(self, result, year, term):
        self.status_var.set(f"已登录：{self.username}")
        try:
            if result["code"] == 1000:
                data = result.get("data", [])
                all_courses = []
                if isinstance(data, str):
                    self.log(f"注意：成绩数据是字符串格式，尝试解析...")
                    if DEBUG_MODE:
                        print(f"[调试] 原始成绩字符串: {data}")
                    try:
                        parsed_data = json.loads(data)
                        if isinstance(parsed_data, list):
                            all_courses = parsed_data
                        elif isinstance(parsed_data, dict):
                            all_courses = parsed_data.get('courses', parsed_data)
                    except json.JSONDecodeError:
                        messagebox.showinfo("查询结果", f"教务系统返回信息: {data}")
                        return
                elif isinstance(data, dict):
                    self.log(f"注意：成绩数据是字典格式，尝试提取课程列表...")
                    all_courses = data.get('courses', [data])
                elif isinstance(data, list):
                    all_courses = data
                else:
                    messagebox.showerror("错误", f"查询成绩成功，但返回的数据格式未知: {type(data)}")
                    return

                if not all_courses:
                    messagebox.showinfo("提示", f"{year}-{year+1}学年第{term}学期未查询到成绩信息。")
                    return

                failed_courses = []
                for course in all_courses:
                    if not isinstance(course, dict): continue
                    score = course.get("grade", course.get("score", 0))
                    try:
                        score_num = float(score)
                        if score_num < 60:
                            failed_courses.append(course)
                    except (ValueError, TypeError):
                        if score is None: score_str = "None"
                        else: score_str = str(score).lower()
                        if score_str in ["不及格", "不合格", "未通过", "fail"]:
                            failed_courses.append(course)

                # 播放对应音效
                if not failed_courses:
                    self.play_sound(PASS_SOUND)  # 播放及格音效                    
                    messagebox.showinfo("恭喜", f"{year}-{year+1}学年第{term}学期所有课程成绩均及格！")

                else:
                    self.play_sound(FAIL_SOUND)  # 播放不及格音效                    
                    result_text = f"以下是{year}-{year+1}学年第{term}学期成绩低于60分的课程（需要重修）：\n\n"
                    total_credit = 0
                    for i, course in enumerate(failed_courses, 1):
                        course_name = course.get("title", course.get("course_name", "未知课程"))
                        credit = course.get("credit", 0)
                        score = course.get("grade", course.get("score", "未知"))
                        result_text += f"{i}. {course_name}\n   学分: {credit}   成绩: {score}\n\n"
                        total_credit += float(credit) if credit and str(credit).replace(".", "").isdigit() else 0
                    result_text += f"\n需重修课程总数: {len(failed_courses)} 门\n需重修总学分: {total_credit} 学分"

                    top = tk.Toplevel(self)
                    top.title("需重修课程列表")
                    top.geometry("450x400")
                    text_widget = tk.Text(top, wrap="word", font=("SimHei", 12))
                    text_widget.insert("end", result_text)
                    text_widget.config(state="disabled")
                    scrollbar = ttk.Scrollbar(top, command=text_widget.yview)
                    text_widget.config(yscrollcommand=scrollbar.set)
                    text_widget.pack(side="left", fill="both", expand=True, padx=10, pady=10)
                    scrollbar.pack(side="right", fill="y")

            else:
                messagebox.showerror("失败", f"查询成绩失败：{result.get('msg', '未知错误')}")
        except KeyError as e:
            messagebox.showerror("错误", f"数据格式异常：缺少字段{str(e)}")
            if DEBUG_MODE:
                print(f"[调试] 成绩数据缺少字段: {e}, 原始数据: {result}")
        except Exception as e:
            messagebox.showerror("错误", f"处理成绩异常：{str(e)}")
            if DEBUG_MODE:
                print(f"[调试] 成绩处理异常：{e}")

    def log(self, message):
        def _log():
            try:
                timestamp = datetime.now().strftime("%H:%M:%S")
                self.log_text.config(state="normal")
                self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
                self.log_text.see(tk.END)
                self.log_text.config(state="disabled")
            except Exception as e:
                if DEBUG_MODE:
                    print(f"[调试] 日志输出失败：{e}")
        self.after(0, _log)

    def start_grab(self):
        selected_indices = self.course_listbox.curselection()
        if not selected_indices:
            messagebox.showerror("错误", "请先选择要抢的课程")
            return
        if self.grab_running:
            messagebox.showinfo("提示", "抢课已在运行中")
            return
        try:
            self.selected_course = self.course_list_data[int(selected_indices[0])]
        except:
            messagebox.showerror("错误", "选择课程失败，请重新获取课程列表")
            return
        course_name = self.selected_course.get("title", "未知课程")
        class_id = self.selected_course.get("class_id", "")
        do_id = self.selected_course.get("do_id", "")
        if not class_id or not do_id:
            messagebox.showerror("错误", "课程ID缺失，无法抢课")
            return
        try:
            interval = float(self.interval_var.get().strip())
            if interval < 0.5:
                interval = 0.5
                self.interval_var.set("0.5")
        except:
            interval = 2.0
            self.interval_var.set("2.0")
        self.grab_running = True
        self.start_grab_btn.config(state="disabled")
        self.stop_grab_btn.config(state="normal")
        self.log(f"开始抢课：{course_name}")
        self.log(f"刷新间隔：{interval}秒")
        self.grab_thread = threading.Thread(
            target=self.grab_course_loop,
            args=(class_id, do_id, course_name, interval),
            daemon=True
        )
        self.grab_thread.start()

    def stop_grab(self):
        self.grab_running = False
        try:
            self.start_grab_btn.config(state="normal")
            self.stop_grab_btn.config(state="disabled")
            self.log("抢课已停止")
        except Exception as e:
            if DEBUG_MODE:
                print(f"[调试] 停止抢课失败：{e}")

    def grab_course_loop(self, class_id, do_id, course_name, interval):
        while self.grab_running:
            try:
                self.log(f"查询{course_name}剩余名额...")
                try:
                    status_result = self.stu_client.get_course_status(class_id, do_id)
                except AttributeError:
                    status_result = self.stu_client.check_course_status(class_id, do_id)
                if status_result["code"] != 1000:
                    self.log(f"查询失败：{status_result['msg']}")
                    time.sleep(interval)
                    continue
                capacity = status_result["data"].get("capacity", 0)
                selected = status_result["data"].get("selected_number", 0)
                remaining = capacity - selected
                self.log(f"状态：总{capacity} | 已选{selected} | 剩余{remaining}")
                if remaining > 0:
                    self.log(f"发现{remaining}个空位！尝试选课...")
                    try:
                        select_result = self.stu_client.select_course(class_id, do_id)
                    except AttributeError:
                        select_result = self.stu_client.choose_course(class_id, do_id)
                    if select_result["code"] == 1000:
                        self.log(f"🎉 {course_name} 抢课成功！")
                        self.play_sound(ENROLL_SUCCESS_SOUND)  # 播放选课成功音效
                        self.grab_running = False
                        self.after(0, lambda: messagebox.showinfo("成功", f"{course_name} 抢课成功！"))
                        break
                    else:
                        self.log(f"选课失败：{select_result['msg']}")
                        self.play_sound(ENROLL_FAIL_SOUND)  # 播放选课失败音效
                time.sleep(interval)
            except Exception as e:
                self.log(f"异常：{str(e)}")
                if DEBUG_MODE:
                    print(f"[调试] 抢课循环异常：{e}")
                time.sleep(interval)
        self.after(0, self.stop_grab)

    def show_about(self):
        about_window = tk.Toplevel(self)
        about_window.title("关于")
        about_window.geometry("400x300")
        about_window.resizable(False, False)

        # 创建文本框
        text_box = tk.Text(about_window, wrap="word", font=("SimHei", 12), state="normal")
        text_box.pack(expand=True, fill="both", padx=20, pady=20)
        
        # 插入普通文本
        text_box.insert(tk.END, "教务系统综合工具 v1.0\n\n")
        text_box.insert(tk.END, "一款集查询、选课于一体的便捷工具\n\n")
        text_box.insert(tk.END, "开发者：")
        
        # 插入超链接（创建唯一标签）
        link_tag = "link_github"
        github_url = "https://github.com/hsjsjaman12"  # 替换为你的GitHub地址
        self.link_tags[link_tag] = github_url
        text_box.insert(tk.END, "hsjsjaman12", link_tag)
        text_box.insert(tk.END, "\n\n")
        text_box.insert(tk.END, "欢迎 使用这个工具")

        # 配置超链接样式
        text_box.tag_configure(link_tag, foreground="blue", underline=True)
        
        # 绑定点击事件
        def on_link_click(event):
            # 获取当前位置的所有标签
            tags = text_box.tag_names(tk.CURRENT)
            for tag in tags:
                if tag in self.link_tags:
                    url = self.link_tags[tag]
                    webbrowser.open_new(url)
                    break

        text_box.bind("<Button-1>", on_link_click)
        
        # 设置文本框只读
        text_box.config(state="disabled")

        # 关闭按钮
        close_btn = ttk.Button(about_window, text="关闭", command=about_window.destroy)
        close_btn.pack(pady=10)

    def show_bounty(self):
        bounty_window = tk.Toplevel(self)
        bounty_window.title("悬赏榜")
        bounty_window.geometry("500x400")

        # 创建带滚动条的文本框
        text_frame = ttk.Frame(bounty_window)
        text_frame.pack(expand=True, fill="both", padx=10, pady=10)
        
        text_box = tk.Text(text_frame, wrap="word", font=("SimHei", 11), state="normal")
        scrollbar = ttk.Scrollbar(text_frame, command=text_box.yview)
        text_box.config(yscrollcommand=scrollbar.set)
        
        text_box.pack(side="left", expand=True, fill="both")
        scrollbar.pack(side="right", fill="y")
        
        # 悬赏榜内容（可自行修改）
        bounty_content = """【悬赏榜】

1. 姜某，跟jumping一样
   

2. 某某，跟。。。一样
   
   

3. 卜拉卜阿勒
   
   

（以上内容仅为示例，可根据实际情况修改）"""
        
        text_box.insert(tk.END, bounty_content)
        text_box.config(state="disabled")

        # 关闭按钮
        close_btn = ttk.Button(bounty_window, text="关闭", command=bounty_window.destroy)
        close_btn.pack(pady=5)

if __name__ == "__main__":
    try:
        import _locale
        _locale._getdefaultlocale = (lambda *args: ['en_US', 'utf8'])
    except:
        pass
    app = JWGLApp()
    def on_close():
        try:
            app.destroy()
        except:
            os._exit(0)
    app.protocol("WM_DELETE_WINDOW", on_close)
    app.mainloop()