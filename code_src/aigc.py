import os
import _thread
import time
from openai import OpenAI
from loguru import logger


subtitle_dir = "./subtitle_txt"
prompt_file_path = "./prompt.txt"
model_dsc_list = []

client = OpenAI(
    api_key="sk-kFp99pPCsyMjz3T0Y2DR3XhWDrnByRQHFqamdZAHsoHh0hmp",
    base_url="https://api.moonshot.cn/v1",
)
model_data = []
prompt_str = ""


def loading(lock):
    chars = ['⣾', '⣷', '⣯', '⣟', '⡿', '⢿', '⣻', '⣽']
    i = 0
    print('')
    while lock[0]:
        i = (i + 1) % len(chars)
        print('\033[A%s %s' %
              (chars[i], lock[1] or '' if len(lock) >= 2 else ''))
        time.sleep(0.1)
    print('')


def get_ai_model():
    global model_data, model_dsc_list
    model_list = client.models.list()
    model_data = model_list.data

    logger.success("获取到可用模型列表")
    for i, model in enumerate(model_data):
        model_dsc_list.append([i, int(str(model.id).split('-')[-1].replace("k", ""))])
        logger.info("model[{:d}]: {}".format(i, model.id))
    model_dsc_list = sorted(model_dsc_list, key=lambda x: x[1])


def load_prompt(file_name):
    file_base_name = str(os.path.basename(file_name))
    course, title = file_base_name.split("_&_")
    global prompt_str
    with open(prompt_file_path, "r", encoding="utf-8") as f:
        raw_prompt_str =     f.read()
    with open(file_name, "r", encoding="utf-8") as f:
        prompt_str = raw_prompt_str.replace("_COURSE_", course).replace("_TITLE_", title).replace("_SUBTITLE_",
                                                                                                  f.read())
        return prompt_str


def single_round_session(file_name):
    global model_data

    logger.info("解析文件: {}".format(file_name))
    if not os.path.exists(file_name):
        logger.error("文件不存在")
        return False

    selected_model_idx = -1
    file_size = os.path.getsize(file_name)
    for e_model in model_dsc_list:
        if (file_size + 1000) <= e_model[1] * 1000:
            selected_model_idx = e_model[0]
            break
    if selected_model_idx == -1:
        logger.error("文本大小: {:d}B 文本超出128K限制，无法请求".format(file_size))
    else:
        logger.info("文本大小: {:d}B 选择模型:{}".format(file_size, model_data[selected_model_idx].id))

    loaded_prompt_str = load_prompt(file_name)

    logger.info("等待生成...")
    lock = [True, '生成中...']
    try:
        _thread.start_new_thread(loading, (lock,))
    except Exception as e:
        print(e)

    completion = client.chat.completions.create(
        model=model_data[selected_model_idx].id,
        messages=[
            {"role": "system", "content": "你是一名老师，善于通过文本内容，总结其中的主要逻辑和大纲"},
            {"role": "user", "content": loaded_prompt_str}
        ],
        temperature=0.3,
    )

    lock = [False, '']
    logger.success("-"*50)
    print(completion.choices[0].message.content)
    logger.success("-"*50)


def main():
    get_ai_model()
    single_round_session(
        subtitle_dir + "/【视频课件资料见置顶评论】深度学习入门必学丨神经网络基础丨卷积神经网络丨循环神经网络_&_第一节：多层感知机02.txt")


if __name__ == '__main__':
    main()
