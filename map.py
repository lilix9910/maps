import base64
import json
import os
import random
import re
import time
import cv2
import pandas as pd
import requests
from PIL import Image
from urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

headers = {
    "Host": "10.188.58.188:30001",
    "User-Agent":
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/109.0",
    "Accept": "application/json, text/plain, */*",
    "Authorization": "Bearer uac1678690699965pge742pF4T5g9QgIjk9pDLqGPe258eMS",
    "Referer": "https://10.188.58.188:30001/plat/countryList",
}


def get_map(city_code):
    # 获取现在所有小区json
    with open("./%s.json" % city_code, mode="r", encoding="utf-8") as f:
        address_list = f.read()
    address_list = json.loads(re.sub("'", '"', address_list))

    # 判断文件夹是否存在
    if not os.path.exists(f'./{city_code}'):
        # 如果不存在则创建文件夹
        os.makedirs(f'./{city_code}')

    # 开始遍历
    for add_l in address_list:
        if add_l['originDrawingNum'] > 0 or add_l['designDrawingNum'] > 0:
            address_name = add_l['standardAddressName']
            address_id = add_l['standardAddressId']
            try:
                print("{}_{} 开始处理:".format(address_name, address_id))

                url = (
                    "https://10.188.58.188:30001/api/ninelevelAddressManagement/page?"
                    "pageNo=1&pageSize=10&housingDevelopmentId=" + address_id +
                    "&buildingNum=&unitNum=&houseNum=")
                resp_json = requests.get(url=url,
                                         headers=headers,
                                         verify=False).json()
                rows = resp_json['data']['rows']
                # print(rows)
                if len(rows) > 0:
                    for row in rows:
                        # print(row)
                        map_data = row.get('originalDrawingPathUrl', '')
                        if len(map_data) > 0:
                            img_data = base64.urlsafe_b64decode(
                                row['originalDrawingPathUrl'][22:])
                            # print(row['routePathName'])
                            route_path_name = row['routePathName']
                            route_path_name = route_path_name[
                                route_path_name.find("/", 5) +
                                1:route_path_name.
                                find("/",
                                     route_path_name.find("/", 5) + 1)]
                            # print(route_path_name)
                            # route_path_name = row['routePathName'][8:10]
                            img_name = "./{}/{}_{}_{}_{}_{}.png".format(
                                city_code,
                                route_path_name,
                                address_name + address_id,
                                row['houseTypeName'],
                                row['squareMeters'],
                                row['standardAddressId'],
                            )

                            with open(img_name, 'wb') as f:
                                f.write(img_data)

                print("{}_{} 任务完成!".format(address_name, address_id))

            except Exception as e:

                print("{}_{} 检索出错!".format(address_name, address_id))
                print(str(e))

            time.sleep(3)
    print("任务完成!")


def get_map_by_name(name, districtCountyCode_list):
    for districtCountyCode in districtCountyCode_list:
        url = "https://10.188.58.188:30001/api/ninelevelAddressManagement/getHousingDevelopmentNameList"
        params = {
            "cityCode": '3100000',
            "districtCountyCode": districtCountyCode,
            "housingDevelopmentName": name,
        }
        resp = requests.get(url=url,
                            params=params,
                            headers=headers,
                            verify=False)

        if resp.json().get('code') == 200:
            for lst in resp.json().get('data', []):
                sub_address_id_list = []
                standard_address_id = lst.get('standard_address_id')
                # 查看是否有足够的上传模板
                url = (
                    "https://10.188.58.188:30001/api/ninelevelAddressManagement/page?pageNo=1&pageSize=10"
                    "&housingDevelopmentId=" + standard_address_id +
                    "&buildingNum=&unitNum=&houseNum= ")
                response = requests.get(url, headers=headers, verify=False)

                sub_address_id_list = [
                    row['standardAddressId']
                    for row in response.json()['data']['rows']
                    if row['originalDrawingPath'] == ''
                ][:3]
                print(
                    name,
                    "----",
                    standard_address_id,
                    '----',
                    sub_address_id_list,
                )

                # 可供上传的户型图模板数量足够
                if len(sub_address_id_list) == 3:
                    return sub_address_id_list

    # 可供上传的户型图模板数量不足
    with open('./update.log', 'a+', encoding='utf-8') as f:
        f.write(name + "----" + "可供上传的户型图模板数量不足" + '\n')
    return []


def get_address_id(city_code):
    """
    "雄安"----"3000000",
    "邯郸"----"3100000",
    "石家庄"----"3110000",
    "保定"----"3120000",
    "张家口"----"3130000",
    "承德"----"3140000",
    "唐山"----"3150000",
    "廊坊"----"3160000",
    "沧州"----"3170000",
    "邢台"----"3190000",
    "秦皇岛"----"3350000",
    "衡水"----"17297346"
    :param city_code:
    :return:
    """
    result = list()
    i = 1
    while True:
        print("处理第 %d 页:" % i)
        url = (
            "https://10.188.58.188:30001/api/ninelevelAddressManagement/getStatisticsPage?pageNo="
            + str(i) + "&pageSize=500&cityCode=" + city_code +
            "&housingDevelopmentId=")
        resp_json = requests.get(url=url, headers=headers, verify=False).json()
        print(resp_json)
        resp_list = resp_json["data"]["records"]
        if len(resp_json["data"]["records"]) > 0:
            result += resp_list
        else:
            break
        i += 1

    with open('./%s.json' % city_code, 'w+', encoding='utf-8') as f:
        f.write(str(result))


def upload_map(name, sub_address_id_list):

    while True:
        # 随机取出3图片
        file_path_list = get_random_png_file(
            dir_path='邯郸市',
            suffix='png',
            prefix='',
            include_str=name,
            exclude_str='0室',
            number=3,
        )

        # 找到3张,跳出循环
        if len(file_path_list) == 3:
            print("找到3张图片:\n", '\n'.join(file_path_list))
            break
        # 没找到<随机取出3张
        else:
            file_path_list = get_random_png_file(
                dir_path='邯郸市',
                suffix='png',
                prefix='',
                include_str='',
                exclude_str='0室',
                number=3,
            )
            break

    for sub_address_id, file_path in zip(sub_address_id_list, file_path_list):
        print('+-+' * 9)
        print("开始处理:", sub_address_id, file_path)

        house_type = file_path.split('_')[-2][:1]
        square_meters = file_path.split('_')[-1][:-4]
        # 图片黑白化 并 重新像素大小800*800 生成新文件 temp_black.png
        upload_name = file_path.split('_')[-2] + file_path.split(
            '_')[-1] + ".png"

        # 图片转黑白800*800
        des_path = './temp_800_800.png'
        png_to_black(png_path=file_path, des_path=des_path)

        files = {'file': (upload_name, open(des_path, 'rb'), 'image/png')}
        data = {'standardAddressId': sub_address_id}

        # 发送请求
        url = 'https://10.188.58.188:30001/api/ninelevelAddressManagement/uploadOriginalDrawing'
        response = requests.post(url,
                                 headers=headers,
                                 files=files,
                                 data=data,
                                 verify=False)
        print('预提交图片:', response)

        # 保存户型图
        url = (
            'https://10.188.58.188:30001/api/ninelevelAddressManagement/updateHouseType'
        )
        data = {
            "id": "",
            "houseType": house_type,
            "squareMeters": square_meters,
            "originalDrawingPath":
            f"picdata/originalDrawing/{sub_address_id}-OriginalDrawing.png",
            "addressId": sub_address_id,
            "relatId": "",
        }
        response = requests.post(url, headers=headers, json=data, verify=False)
        print('保存图片:', response.text)
        # 将处理结果写到文件里
        with open('./update.log', 'a+', encoding='utf-8') as f:
            f.write(name + "----" + sub_address_id + '----' +
                    file_path[file_path.rfind('\\') + 1:] + '----' +
                    response.text + '\n')
        time.sleep(3)

    print("全部执行完成.")


# 处理图片
def png_to_black(png_path, des_path):
    with Image.open(png_path) as im:
        # 转为黑白模式
        im = im.convert('L')
        # 改变图片的像素大小
        im_resized = im.resize((800, 800))
        # 定义要剪切保留的区域
        left = 0
        top = 0
        right = 800
        bottom = 760
        # 剪切图片
        im_crop = im_resized.crop((left, top, right, bottom))
        # 再次改变图片的像素大小
        im_crop = im_crop.resize((800, 800))
        # 保存为黑白图片
        im_crop.save(des_path)


# 常规马赛克
def do_mosaic(img, x, y, w, h, neighbor=9):
    """
    :param rgb_img
    :param int x :  马赛克左顶点
    :param int y:  马赛克左顶点
    :param int w:  马赛克宽
    :param int h:  马赛克高
    :param int neighbor:  马赛克每一块的宽
    """
    for i in range(0, h, neighbor):
        for j in range(0, w, neighbor):
            rect = [j + x, i + y]
            color = img[i + y][j + x].tolist()  # 关键点1 tolist
            left_up = (rect[0], rect[1])
            x2 = rect[0] + neighbor - 1  # 关键点2 减去一个像素
            y2 = rect[1] + neighbor - 1
            if x2 > x + w:
                x2 = x + w
            if y2 > y + h:
                y2 = y + h
            right_down = (x2, y2)
            cv2.rectangle(img, left_up, right_down, color, -1)  # 替换为为一个颜值值

    return img


def get_random_png_file(
    dir_path,
    suffix='',
    prefix='',
    include_str='',
    exclude_str='',
    number=1,
    exclude_dir_list=[],
):
    """
    找到满足条件的number个文件\n
    :param dir_path: 路径,包括子路径
    :param suffix: 后缀
    :param prefix: 前缀
    :param include_str: 文件名内包含
    :param exclude_str: 文件名内不包含
    :param number: 数量
    :param exclude_dir_list: 排除文件夹列表
    :return: 文件名列表
    """
    file_dict = {}
    for root, dirs, files in os.walk(dir_path):
        # 排除指定的子文件夹
        for exclude_dir in exclude_dir_list:
            if exclude_dir in dirs:
                dirs.remove(exclude_dir)
        for file in files:
            if (file.endswith(suffix) and file.startswith(prefix)
                    and include_str in file and exclude_str not in file):
                file_path = os.path.join(root, file)
                file_size = os.path.getsize(file_path)
                file_tuple = (file_path, file_size)
                file_dict.setdefault(file_size, []).append(file_tuple)

    # 从字典中随机取出number个不同大小的文件,并保证文件大小不一样, 文件大小大于50k, 分辨率大于790
    file_list = []
    while len(file_list) < number and len(file_dict) > 0:
        file_size = random.choice(list(file_dict.keys()))
        file_tuple = random.choice(file_dict[file_size])
        # 文件大于10k, 并且文件大小不相等
        if file_tuple not in file_list and file_tuple[1] > 10 * 1024:
            # 打开图片文件 获取像素大小信息
            # im = Image.open(file_tuple[0])
            # width, height = im.size
            # if width > 790 and height > 790:
            file_list.append(file_tuple)

    return [file_name for file_name, _ in file_list]


def lian_jia_get(city_tuple):
    city_code, city_name = city_tuple
    # 判断第一次处理,是没有的就创建文件
    if not os.path.exists(f'./lianjia_house_{city_name}_id.txt'):
        with open(f'./lianjia_house_{city_name}_id.txt', 'w') as f:
            f.write("house_id,house_remark,result\n")

    df_map_house_id = pd.read_csv(f'./lianjia_house_{city_name}_id.txt',
                                  encoding='UTF-8')
    house_id_list = df_map_house_id['house_id'].to_list()
    # 列表去重
    house_name_list = list(
        set([
            x.split(" ")[1] for x in df_map_house_id['house_remark'].to_list()
        ]))
    # 列表乱序排列
    random.shuffle(house_name_list)
    # 列表倒序
    house_name_list.reverse()

    # 判断第一次处理,是没有的就随便塞进去几个关键字
    if len(house_name_list) == 0:
        house_name_list = ['小区', '家园', '家属楼', '城', '里']
    lian_jia_headers = {
        "accept":
        "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,"
        "application/signed-exchange;v=b3;q=0.7",
        "cookie":
        "qunhe-jwt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCIsInYiOiIwIn0"
        ".eyJleHAiOjE2NzkzODg0MDU5OTYsInNfaWQiOiJmMGU3YzJjMGIwMzExMWVkOTg1Yjc1NWMxNGI2MzA2NSIsImtfaWQiOiIz"
        "Rk80TURTOEtJMTgiLCJ1dCI6MiwiYyI6MTY3Njc5NjQwNTk5NiwiZSI6MTY3OTM4ODQwNTk5NiwidXYiOjAsImlhZSI6ZmFsc2"
        "UsImlwdSI6dHJ1ZSwiaW0iOmZhbHNlLCJsbyI6InpoX0NOIiwidWwiOiJGQVNUIiwiciI6IkNOIn0.cffh6tIgnFJnGHRJ9YuUi"
        "WYJT1wwrsNTglfhamh4v80; qhdi=f0e1f6ceb03111eda4f14f3304a26cd4; kjl_usercityid=175",
        "dnt":
        "1",
        "referer":
        "https://www.kujiale.cn/huxing/result/76-57ce-1-0?area_level=3&word_from=1&precise=0&num=15&start=0",
        "sec-ch-ua":
        '"Chromium";v="110", "Not A(Brand";v="24", "Microsoft Edge";v="110"',
        "sec-ch-ua-mobile":
        "?0",
        "sec-ch-ua-platform":
        "Windows",
        "sec-fetch-dest":
        "document",
        "sec-fetch-mode":
        "navigate",
        "sec-fetch-site":
        "same-origin",
        "sec-fetch-user":
        "?1",
        "upgrade-insecure-requests":
        "1",
        "user-agent":
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/110.0.0.0 Safari/537.36 Edg/110.0.1587.41",
    }
    current_process = 0
    all_process = len(house_name_list)
    for house_name in house_name_list:
        current_process += 1
        print(f"开始检索 {house_name}, 进度 {current_process}/{all_process}:")
        search_text = "-".join([f"{ord(c):04x}" for c in house_name])
        start_number = 0
        while True:
            url = (
                f"https://www.kujiale.cn/huxing/result/{city_code}-{search_text}-0-0?word_from=1"
                f"&area_Level=3&precise=0&num=15&start=" +
                str(start_number * 15))

            print(f"处理第 {start_number} 页数据.")
            resp = requests.get(url=url, headers=lian_jia_headers, proxies={'http': None, 'https': None})
            if start_number == 0:
                house_number = re.search(r'酷家乐户型库为您提供了(\d+)个', resp.text)
                house_number = house_number.group(1)
                print(f"一共找到 {house_number} 个户型图.")

            result_list = re.findall(
                r'tpl-huxingtu result-card j_cell  j_result_card.*?position:absolute;top:0;left:0;opacity:0;',
                resp.text,
                flags=re.S,
            )

            print(f"本次找到了 {len(result_list)} 条户型图.")
            if len(result_list) == 0:
                break

            for result in result_list:
                house_id = re.search(r'"/huxing/detail/(.*?)"', result)
                house_remark = re.search(r'alt="(.*?)"', result)
                if house_id and house_remark:
                    if house_id.group(1) not in house_id_list:
                        with open(
                                f'./lianjia_house_{city_name}_id.txt',
                                mode='a+',
                                encoding='utf-8',
                        ) as f:
                            house_id_list.append(house_id.group(1))
                            print(house_id.group(1), house_remark.group(1))
                            f.write(
                                house_id.group(1) + ',' +
                                re.sub(r'/|,', '-', house_remark.group(1)) +
                                ',' + '\n')
                    else:
                        print(f"{house_id.group(1)}已在列表中.")
                else:
                    print(result)
                    print("house_id house_remark 匹配失败.")

            start_number += 1
            if start_number * 15 > int(house_number):
                break

            time.sleep(3)


def lian_jia_download(city_tuple):
    _, city_name = city_tuple
    lian_jia_headers = {
        "accept":
        "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,"
        "application/signed-exchange;v=b3;q=0.7",
        "cookie":
        """qunhe-jwt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCIsInYiOiIwIn0.eyJleHAiOjE2NzkzODg0MDU5OTYsInNfaWQiOiJmMGU3YzJjMGIwMzExMWVkOTg1Yjc1NWMxNGI2MzA2NSIsImtfaWQiOiIzRk80TURTOEtJMTgiLCJ1dCI6MiwiYyI6MTY3Njc5NjQwNTk5NiwiZSI6MTY3OTM4ODQwNTk5NiwidXYiOjAsImlhZSI6ZmFsc2UsImlwdSI6dHJ1ZSwiaW0iOmZhbHNlLCJsbyI6InpoX0NOIiwidWwiOiJGQVNUIiwiciI6IkNOIn0.cffh6tIgnFJnGHRJ9YuUiWYJT1wwrsNTglfhamh4v80; qhdi=f0e1f6ceb03111eda4f14f3304a26cd4; kjl_usercityid=175""",
        "dnt":
        "1",
        "referer":
        "https://www.kujiale.cn/huxing/result/76-57ce-1-0?area_level=3&word_from=1&precise=0&num=15&start=0",
        "sec-ch-ua":
        '"Chromium";v="110", "Not A(Brand";v="24", "Microsoft Edge";v="110"',
        "sec-ch-ua-mobile":
        "?0",
        "sec-ch-ua-platform":
        "Windows",
        "sec-fetch-dest":
        "document",
        "sec-fetch-mode":
        "navigate",
        "sec-fetch-site":
        "same-origin",
        "sec-fetch-user":
        "?1",
        "upgrade-insecure-requests":
        "1",
        "user-agent":
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/110.0.0.0 Safari/537.36 Edg/110.0.1587.41",
        "x-requested-with":
        "XMLHttpRequest",
    }
    df_map_house_id = pd.read_csv(
        f'./lianjia_house_{city_name}_id.txt',
        encoding='UTF-8',
        dtype=str,
        na_values=[''],
    )
    df_map_house_id = df_map_house_id.fillna('')

    if not os.path.exists(city_name):
        os.makedirs(city_name)

    for _, row in df_map_house_id.iterrows():
        house_id = row['house_id']
        house_remark = re.split(' +', row['house_remark'])
        house_name = house_remark[1]
        house_stype = house_remark[-2]
        house_area = house_remark[-1][:-2]
        download_name = f"{house_id}_{house_name}_{house_stype}_{house_area}"

        # 已经处理过的跳过
        if row['result'] != '':
            continue

        url = f"https://www.kujiale.cn/dis/api/floorplan2dweb/{house_id}?c=false&st=0&b=false&at=0&f=true&n=true&a=false&old=false&pt=2"

        resp = requests.get(
            url=url,
            headers=lian_jia_headers,
            proxies={  # type: ignore
                "http": None,
                "https": None
            })
        if resp.status_code != 200:
            row['result'] = "get_status_code_not_200"
            print('get_status_code_not_200')
            continue

        if house_id in resp.text:
            url = f"http:{resp.text}"
            # 下载图片
            resp = requests.get(url=url)
            if resp.status_code == 200:
                # 小于50的 大于200的面积 和 0厅0卫0厨 的不处理
                if '0厅0卫0厨' in download_name or float(
                        download_name.split('_')[-1]) > 200 or float(
                            download_name.split('_')[-1]) < 50:
                    print(f"{download_name} 不处理.")
                    row['result'] = "no use"
                    continue
                with open(f"./{city_name}/{download_name}.png", "wb") as f:
                    f.write(resp.content)
                    print(f"./{city_name}/{download_name}.png 下载完成.")
                    row['result'] = "200"
            else:
                row['result'] = "download_status_code_not_200"
        else:
            row['result'] = "house_id_not_in_response"

        df_map_house_id.to_csv(f'./lianjia_house_{city_name}_id.txt',
                               index=False,
                               encoding='utf-8')
        time.sleep(0.5)


if __name__ == '__main__':

    # lian_jia_get(('76', '邯郸市'))
    # lian_jia_download(('76', '邯郸市'))

    # lian_jia_get(('240', '郑州市'))
    # lian_jia_download(('240', '郑州市'))

    while True:
        lian_jia_get(('223', '济南市'))
        lian_jia_get(('84', '太原市'))

    # lian_jia_download(('84', '太原市'))
    # lian_jia_download(('223', '济南市'))

    # =====================================================
    # 上传图片
    # area_dict = {
    #     "邯郸县": "3100100",
    #     "丛台区": "3100101",
    #     "复兴区": "3100102",
    #     "邯山区": "3100103",
    #     "高开区": "3100104",
    #     "武安分公司": "3100300",
    #     "峰峰分公司": "3100400",
    #     "涉县分公司": "3100500",
    #     "大名分公司": "3100600",
    #     "磁县分公司": "3100700",
    #     "魏县分公司": "3100800",
    #     "成安分公司": "3100900",
    #     "永年分公司": "3101000",
    #     "肥乡分公司": "3101100",
    #     "邱县分公司": "3101200",
    #     "临漳分公司": "3101300",
    #     "鸡泽分公司": "3101400",
    #     "曲周分公司": "3101500",
    #     "广平分公司": "3101600",
    #     "馆陶分公司": "3101700",
    # }

    # search_list = [
    #     ('三十一中学家属院', ''),
    # ]

    # for search_turple in search_list:
    #     name, districtCountyCode = search_turple[0], area_dict.get(
    #         search_turple[1], '')

    #     if districtCountyCode == '':
    #         districtCountyCode_list = [
    #             '3100101', '3100102', '3100103', '3100104', '3100100'
    #         ]
    #     else:
    #         districtCountyCode_list = [districtCountyCode]

    #     print(name, districtCountyCode_list)
    #     sub_address_id_list = get_map_by_name(
    #         name=name, districtCountyCode_list=districtCountyCode_list)
    #     print(sub_address_id_list)

    # if len(sub_address_id_list) == 3:
    # upload_map(
    #     name=name,
    #     sub_address_id_list=sub_address_id_list,
    # )

# =====================================================

# =====================================================
# 重传图片
# dest = """"""
# import re

# log_list = dest.split('\n')
# for log in log_list:
#     result_list = log.split("----")
#     house_type = ''.join(result_list[2].split("_")[2])
#     area = ''.join(result_list[2].split("_")[3][:-4])
#     # print(result_list[0], house_type, area, house_type + area)

#     sub_address_id = result_list[1]
#     file_path = result_list[2]
#     name = result_list[0]

#     print('+-+' * 20)
#     sub_address_id = str(sub_address_id)
#     print("开始处理:", name, sub_address_id, file_path)
#     house_type = file_path.split('_')[-2][:1]
#     square_meters = file_path.split('_')[-1][:-4]
#     # 图片黑白化 并 重新像素大小800*800 生成新文件 temp_black.png
#     upload_name = file_path.split('_')[-2] + file_path.split(
#         '_')[-1] + ".png"
#     png_to_black(file_path, des_path='temp_800_800.png')

#     files = {
#         'file': (upload_name, open('temp_800_800.png', 'rb'), 'image/png')
#     }
#     data = {'standardAddressId': sub_address_id}

#     # 发送请求
#     url = 'https://10.188.58.188:30001/api/ninelevelAddressManagement/uploadOriginalDrawing'
#     response = requests.post(url,
#                              headers=headers,
#                              files=files,
#                              data=data,
#                              verify=False)
#     print('预提交图片:', response)

#     # 保存户型图
#     url = (
#         'https://10.188.58.188:30001/api/ninelevelAddressManagement/updateHouseType'
#     )
#     data = {
#         "id": "",
#         "houseType": house_type,
#         "squareMeters": square_meters,
#         "originalDrawingPath":
#         f"picdata/originalDrawing/{sub_address_id}-OriginalDrawing.png",
#         "addressId": sub_address_id,
#         "relatId": "",
#     }
#     response = requests.post(url, headers=headers, json=data, verify=False)
#     print('保存图片:', response.text)
#     # 将处理结果写到文件里
#     with open('./update.log', 'a+', encoding='utf-8') as f:
#         f.write(name + "----" + sub_address_id + '----' +
#                 file_path[file_path.rfind('\\') + 1:] + '----' +
#                 response.text + '\n')
#     time.sleep(3)

# print("全部执行完成.")
# upload_map(
#     [
#         '地税局家属楼',
#         '康奈小区A座',
#         '陵东街50号院',
#         '沙口集新民居',
#         '老商业局家属楼',
#         '豆庄小区',
#         '浴新南180饭店院',
#         '老人行家属院',
#     ]
# )

# """
#     "雄安"----"3000000",
#     "邯郸"----"3100000",
#     "石家庄"----"3110000",
#     "保定"----"3120000",
#     "张家口"----"3130000",
#     "承德"----"3140000",
#     "唐山"----"3150000",
#     "廊坊"----"3160000",
#     "沧州"----"3170000",
#     "邢台"----"3190000",
#     "秦皇岛"----"3350000",
#     "衡水"----"17297346",
# """
# get_address_id(city_code='3150000')
# get_map(city_code='3150000')
