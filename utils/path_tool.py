"""
为整个工程提供统一的绝对路径
"""

import os

def get_project_root() -> str:
    r"""
    获取工程所在的根目录
    :return: 字符串根目录
    示例（以下三个路径）：
        E:\rag_agent_project\6.Agent项目案例\utils\path_tool.py
        E:\rag_agent_project\6.Agent项目案例\utils
        E:\rag_agent_project\6.Agent项目案例
    一个错误点：三引号里的内容仍然是字符串，会解析反斜杠转义。
        其中 \utils 开头的 \u 被 Python 当成 Unicode 转义，它后面需要 4 位十六进制数字，但 tils 不符合要求，因此报错。
        错误指向第 8 行，是因为整个字符串从这里开始。
        最简单的修复：在这个说明字符串开头加 r，让反斜杠按原样处理
    """
    # 当前文件的绝对路径
    current_file = os.path.abspath(__file__)
    # 获取工程的根目录，先获取 文件 所在的 文件夹 绝对路径
    current_dir = os.path.dirname(current_file)
    # 获取工程根目录
    project_root = os.path.dirname(current_dir)

    return project_root


def get_abs_path(relative_path: str) -> str:
    """
    传递相对路径，得到绝对路径
    :param relative_path: 相对路径
    :return: 绝对路径
    """
    project_root = get_project_root()
    return os.path.join(project_root, relative_path)

if __name__ == '__main__':
    print(get_abs_path("sda/d23"))
