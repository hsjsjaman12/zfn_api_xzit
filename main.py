import base64
import os
import sys
from pprint import pprint
from zfn_api import Client

def main():
    # 配置参数 - 建议将敏感信息通过环境变量或配置文件获取
    base_url = os.getenv("JWGLXT_BASE_URL", "http://jwglxt.xzit.edu.cn/jwglxt/xtgl")
    #或用IP版（两种都能生效，选一个就行）
    # base_url = "http://218.3.178.51/jwglxt/xtgl"
    
    cookies = {}  # 若已有登录cookies可直接传入，否则留空
    raspisanie = []  # 上下课时间，默认使用库中定义的时间
    ignore_type = []  # 学业生涯数据中需要忽略的根类型
    detail_category_type = []  # 需要详细获取分类的课程类型
    timeout = 10  # 延长超时时间，避免网络波动导致失败

    try:
        # 初始化客户端
        stu = Client(
            cookies=cookies,
            base_url=base_url,
            raspisanie=raspisanie,
            ignore_type=ignore_type,
            detail_category_type=detail_category_type,
            timeout=timeout
        )

        # 登录（若无cookies）
        if not cookies:
            username = input("请输入学号：")# 提供默认值方便测试
            password = input("请输入密码：")
            
            # 首次登录（可能需要验证码）
            login_result = stu.login(username, password)
            if login_result["code"] == 1001:
                # 需要验证码：保存验证码图片并手动输入
                verify_data = login_result["data"]
                try:
                    with open("kaptcha.png", "wb") as f:
                        f.write(base64.b64decode(verify_data.pop("kaptcha_pic")))
                    print("验证码已保存为 kaptcha.png，请查看并输入")
                    verify_data["kaptcha"] = input("请输入验证码：").strip()
                    # 提交验证码完成登录
                    login_result = stu.login_with_kaptcha(**verify_data)
                except Exception as e:
                    print(f"处理验证码时出错：{str(e)}")
                    return

            if login_result["code"] != 1000:
                print(f"登录失败：{login_result['msg']}")
                return
            print("登录成功！")
            # 提示用户保存cookies以便下次使用
            print("建议保存以下cookies供下次使用：")
            pprint(login_result["data"]["cookies"])
            

        # 调用功能接口示例
        print("\n===== 个人信息 =====")
        info = stu.get_info()
        pprint(info)


        #----------------welcome after--------------------------#

        # 获取成绩（可自定义学期）
        year = input("\n请输入查询成绩的年份（默认2024）：") or 2024
        term = input("请输入查询成绩的学期（默认1）：") or 1
        print(f"\n===== {year}年第{term}学期成绩 =====")
        grade = stu.get_grade(int(year), int(term))
        pprint(grade)

        # 获取课表（可自定义学期）
        print(f"\n===== {year}年第{term}学期课表 =====")
        schedule = stu.get_schedule(int(year), int(term))
        pprint(schedule)

        # 导出课表为PDF
        print("\n正在导出课表为PDF...")
        pdf_result = stu.get_schedule_pdf(int(year), int(term))
        if pdf_result["code"] == 1000:
            with open("课表.pdf", "wb") as f:
                f.write(pdf_result["data"])
            print("课表已成功导出为 课表.pdf")
        else:
            print(f"导出课表失败：{pdf_result['msg']}")

    except Exception as e:
        print(f"程序运行出错：{str(e)}", file=sys.stderr)
        return

if __name__ == "__main__":
    main()
