from aip import AipOcr
import os

#密钥文件路径
filename = 'file/key'
APP_ID = ""
API_KEY = ""
SECRET_KEY = ""
client = None

#读取密钥文件
if os.path.exists(filename):
    with open(filename, "r", encoding="utf-8") as f:
        dictkey = eval(f.readlines()[0])
        APP_ID = dictkey['APP_ID']
        API_KEY = dictkey['API_KEY']
        SECRET_KEY = dictkey['SECRET_KEY']
    #初始化百度OCR，设置10秒超时防卡死
    client = AipOcr(APP_ID, API_KEY, SECRET_KEY)
    client.setConnectionTimeoutInMillis(10000)
    client.setSocketTimeoutInMillis(10000)
else:
    print(filename)
    print('请先在file目录下创建key，写入格式：\n{\'APP_ID\':\'你的ID\', \'API_KEY\':\'你的KEY\', \'SECRET_KEY\':\'你的SECRET\'}')

def get_file_content(filePath):
    with open(filePath, 'rb') as fp:
        return fp.read()


def getcn():
    img_path = r"file/temp.png"
    if client is None:
        return "密钥文件不存在，请检查file/key"

    try:
        image = get_file_content(img_path)
        print("图片读取成功，开始请求识别接口...")
    except Exception as e:
        msg = f"图片读取失败：{e}"
        print(msg)
        return msg

    try:
        results = client.licensePlate(image)
        #print("接口原始返回：", results)
        if "words_result" in results and "number" in results["words_result"]:
            plate = results["words_result"]["number"]
            print(f"识别到车牌：{plate}")
            return plate
        else:
            msg = "未识别到车牌，图片无清晰车牌"
            print(msg)
            return msg
    except Exception as err:
        msg = f"请求出错/超时：{err}"
        print(msg)
        return msg
if __name__ == "__main__":
    getcn()