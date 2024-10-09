import json
import os
import subprocess
import time

import requests
# 首先导入模块
from lxml import etree
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from loguru import logger
from tqdm import tqdm
import aigc

video_info_api_url = "https://api.bilibili.com/x/web-interface/view?bvid=_BV_"
video_subtitle_api_url = "https://api.bilibili.com/x/player/wbi/v2?aid=_AID_&cid=_CID_"
video_title, video_aid, video_total_p, video_cid_list = "", 0, 0, []

# 设置Chrome选项，开启无头模式
options = Options()
options.add_argument("--headless")  # 启用无头模式
options.add_argument("--disable-gpu")  # 禁用GPU硬件加速
options.add_argument('blink-settings=imagesEnabled=false')  # 不加载图片, 提升速度
options.add_experimental_option('excludeSwitches', ['enable-automation'])
options.add_argument('log-level=3')
# 初始化WebDriver，传入配置的选项
driver = webdriver.Chrome(options=options)


def login_bilibili():
    driver.get("https://www.bilibili.com/")
    driver.implicitly_wait(10)
    # 等待登陆按钮可点击
    element = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.CLASS_NAME, "header-login-entry"))
    )
    element.click()

    element = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.CLASS_NAME, "login-sns-name"))
    )
    element.click()

    element = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.CLASS_NAME, "web_qrcode_img"))
    )
    # 定位图片元素，这里使用XPath作为示例
    image_element = driver.find_element(By.XPATH, '/html/body/div[1]/span[1]/div[1]/div[3]/div[1]/img')
    # 获取图片的源文件URL
    image_url = image_element.get_attribute('src')
    response = requests.get(image_url)

    image_path = os.getcwd() + '/b_image.png'
    if response.status_code == 200:
        # 保存图片到本地
        with open(image_path, 'wb') as f:
            f.write(response.content)
    else:
        logger.error(f"图片下载失败，状态码：{response.status_code}")

    subprocess.run(['start', image_path], shell=True)

    logger.info("[info] - 等待登陆...（使用微信扫码登陆，登陆成功后关闭二维码图片）")
    element = WebDriverWait(driver, 1000).until(
        EC.invisibility_of_element_located((By.CLASS_NAME, "web_qrcode_img"))
    )
    logger.success("[info] - 登陆成功")


def get_video_param(BV):
    global video_title, video_aid, video_total_p, video_cid_list
    driver.get(video_info_api_url.replace("_BV_", BV))
    driver.implicitly_wait(10)
    page_source = driver.page_source
    xml_obj = etree.HTML(page_source)
    json_raw_str = xml_obj.xpath("/html/body/pre/text()")[0]

    if len(json_raw_str) != 0:
        json_data = json.loads(json_raw_str)
        if json_data["message"] != "0":
            logger.error("出现了一些问题：{}".format(json_data["message"]))
            return False
        # 视频数据
        video_title = json_data["data"]["title"]
        video_aid = json_data["data"]["aid"]
        video_total_p = json_data["data"]["videos"]
        if video_total_p > 1:
            for elem_p in json_data["data"]["pages"]:
                video_cid_list.append([elem_p["cid"], elem_p["part"]])
        logger.info("-" * 50)
        logger.success("\n- 视频标题：{}\n- 视频aid：{}\n- 视频总P数：{}".format(video_title, video_aid, video_total_p))
        logger.info("-" * 50)
    return True


def get_video_subtitle_url_list():
    global video_title, video_aid, video_total_p, video_cid_list
    # print(video_title, video_aid, video_total_p, video_cid_list)
    # 字幕数据
    if video_total_p > 1:
        for idx, elem in tqdm(enumerate(video_cid_list), desc='Get Video Subtitle URL'):
            tqdm.write(str(idx) + " - cid:" + str(video_cid_list[idx][0]))

            driver.get(video_subtitle_api_url.replace("_AID_", str(video_aid)).replace("_CID_", str(elem[0])))
            driver.implicitly_wait(10)
            page_source = driver.page_source
            xml_obj = etree.HTML(page_source)
            json_raw_str = xml_obj.xpath("/html/body/pre/text()")[0]
            if len(json_raw_str) != 0:
                json_data = json.loads(json_raw_str)

                json_data_base_data = json_data["data"]
                if json_data_base_data.get("subtitle") is not None:
                    subtitle_list = json_data_base_data["subtitle"]["subtitles"]
                    if len(subtitle_list) != 0:
                        video_cid_list[idx].append("https:" + subtitle_list[0]["subtitle_url"])
                    else:
                        tqdm.write("cid:" + str(video_cid_list[idx][0]) + " Not Found Subtitle")
                        video_cid_list[idx].append("")
                else:
                    tqdm.write("cid:" + str(video_cid_list[idx][0]) + " Not Found Subtitle")
                    video_cid_list[idx].append("")
            time.sleep(1.5)
    driver.quit()


def get_video_subtitle_json(save_json=False):
    global video_cid_list
    total_count, success_count, failed_count = len(video_cid_list), 0, 0
    cur_dir = os.getcwd()
    for idx, elem in enumerate(video_cid_list):
        if str(elem[2]).strip() != "":
            response = requests.get(elem[2])
            subtitle_file_json = cur_dir + "/subtitle_json" + '/{}_&_{}.json'.format(video_title, elem[1])
            subtitle_file_txt = cur_dir + "/subtitle_txt" + '/{}_&_{}.txt'.format(video_title, elem[1])
            logger.info("[info] - 下载 {}_{}".format(video_title, elem[1]))
            if response.status_code == 200:
                if save_json:
                    logger.info("[info] - 写入json文件")
                    with open(subtitle_file_json, 'w') as f:
                        f.write(response.text)

                logger.info("[info] - 转为txt文件")
                with open(subtitle_file_txt, 'w', encoding="utf-8") as f:
                    for e in json.loads(response.text)["body"]:
                        f.write('{}{}'.format(e["content"], "\n").encode('utf-8').decode("utf-8"))
                success_count = success_count + 1
        else:
            logger.error(f"字幕下载失败")
            failed_count = failed_count + 1
        time.sleep(3)
    return "总计：{}个，下载成功：{}个，下载失败：{}个".format(total_count, success_count, failed_count)


def main():
    BV = "BV1zX4y1c74i"
    res = get_video_param(BV)
    if not res:
        logger.error("获取视频参数异常，视频ID: {}".format(BV))
        return
    time.sleep(3)
    login_bilibili()
    time.sleep(5)
    get_video_subtitle_url_list()
    time.sleep(3)
    logger.info(get_video_subtitle_json())
    logger.success("下载完成")


if __name__ == '__main__':
    main()
