import sys
import os
import glob
import shutil
import chardet
import re
from datetime import datetime, timedelta
import io


# -*- coding: utf-8 -*-

def vtt2txt(vtt_content):
    """将VTT内容转换为纯文本"""
    txt = io.StringIO()

    lines = vtt_content.split("\n")
    current_block = []
    blocks = []

    for line in lines:
        if line.strip() == "":
            if current_block:
                blocks.append(current_block)
                current_block = []
        else:
            current_block.append(line)

    if current_block:
        blocks.append(current_block)

    # 跳过第一块 "WEBVTT"
    blocks = blocks[1:] if len(blocks) > 1 else []

    for block in blocks:
        # 跳过序号行和时间行，只保留文本行
        text_lines = []
        for line in block:
            # 跳过序号行（纯数字）和时间行（包含-->）
            if not (line.strip().isdigit() or "-->" in line):
                text_lines.append(line.strip())

        # 如果块中有文本内容，则添加到输出
        if text_lines:
            # 将多行文本合并为一行（用空格分隔）
            txt.write(' '.join(text_lines) + "\n")

    return txt.getvalue()


def lrc2txt(lrc_content):
    """将LRC内容转换为纯文本"""
    txt = io.StringIO()

    lines = lrc_content.split("\n")
    for line in lines:
        # 使用正则表达式移除所有方括号及其内容
        clean_line = re.sub(r'\[.*?\]', '', line).strip()

        # 如果处理后还有内容，则写入输出
        if clean_line:
            txt.write(clean_line + "\n")

    return txt.getvalue()


def convert_to_txt(input_file, output_file):
    try:
        with open(input_file, 'rb') as f:
            raw_data = f.read()

            # 尝试使用 UTF-8 解码
            try:
                content = raw_data.decode('utf-8')
            except UnicodeDecodeError:
                # 使用 chardet 检测编码
                result = chardet.detect(raw_data)
                encoding = result['encoding']
                if encoding is None:
                    raise ValueError("无法检测文件编码。")
                content = raw_data.decode(encoding)

        # 根据文件扩展名选择转换函数
        if input_file.lower().endswith(".vtt"):
            txt = vtt2txt(content)
        elif input_file.lower().endswith(".lrc"):
            txt = lrc2txt(content)
        else:
            raise ValueError(f"不支持的文件格式: {input_file}")

        with open(output_file, 'w', encoding='utf-8') as f_out:
            f_out.write(txt)
        return True
    except Exception as e:
        print(f"转换失败: {e}")
        return False


def extract_number_from_filename(filename):
    """从文件名中提取数字"""
    # 尝试匹配文件名开头的数字
    match = re.search(r'#?(\d+)', filename)
    if match:
        return int(match.group(1))

    # 尝试匹配文件名中的其他数字
    numbers = re.findall(r'\d+', filename)
    if numbers:
        return int(numbers[0])

    # 如果没有找到数字，返回一个很大的数字确保排在最后
    return float('inf')


def merge_txt_files(txt_files, output_file):
    """合并多个TXT文件到一个文件中"""
    try:
        # 按文件名中的数字排序
        sorted_files = sorted(
            txt_files,
            key=lambda f: extract_number_from_filename(os.path.basename(f))
        )

        with open(output_file, 'w', encoding='utf-8') as outfile:
            for txt_file in sorted_files:
                # 写入文件内容（不添加任何标题）
                with open(txt_file, 'r', encoding='utf-8') as infile:
                    content = infile.read().strip()  # 移除首尾空白
                    if content:  # 确保内容不为空
                        outfile.write(content)
                        outfile.write("\n\n")  # 文件之间添加两个换行符分隔
        return True
    except Exception as e:
        print(f"合并文件失败: {e}")
        return False


def get_last_folder_name(path):
    """获取路径中最后一个文件夹的名称"""
    # 规范化路径并移除末尾斜杠
    normalized = os.path.normpath(path)

    # 获取最后一个文件夹名
    folder_name = os.path.basename(normalized)

    # 如果路径是根目录，直接返回路径字符串
    if folder_name == "":
        return normalized.replace("\\", "_").replace("/", "_").replace(":", "")

    # 移除可能的RJ号前缀
    if re.match(r'^RJ\d+\s*', folder_name):
        return re.sub(r'^RJ\d+\s*', '', folder_name).strip()

    return folder_name


if __name__ == "__main__":
    # 在""内填入地址
    folder_path = r""

    if not os.path.isdir(folder_path):
        print(f"路径 '{folder_path}' 无效或不是文件夹。")
        sys.exit(1)

    # 递归查找所有.vtt和.lrc文件，并确保每个基名只处理一次
    processed_basenames = set()
    converted_files = []
    generated_txt_files = []  # 存储所有生成的TXT文件路径

    # 先处理所有VTT文件
    for root, _, files in os.walk(folder_path):
        for file in files:
            if file.lower().endswith(".vtt"):
                file_path = os.path.join(root, file)
                basename = os.path.splitext(file)[0]  # 不带扩展名的文件名

                # 如果这个基名还没有处理过
                if basename not in processed_basenames:
                    processed_basenames.add(basename)
                    converted_files.append(file_path)

    # 再处理LRC文件，但跳过已有同名VTT文件的
    for root, _, files in os.walk(folder_path):
        for file in files:
            if file.lower().endswith(".lrc"):
                file_path = os.path.join(root, file)
                basename = os.path.splitext(file)[0]  # 不带扩展名的文件名

                # 如果这个基名还没有处理过
                if basename not in processed_basenames:
                    processed_basenames.add(basename)
                    converted_files.append(file_path)

    if not converted_files:
        print("该文件夹及子文件夹中没有找到支持的 .vtt 或 .lrc 文件。")
        sys.exit(0)

    # 转换文件并记录生成的TXT文件
    for input_file in converted_files:
        # 生成输出文件名：替换扩展名为.txt
        output_file = os.path.splitext(input_file)[0] + ".txt"

        if convert_to_txt(input_file, output_file):
            print(f"成功转换: {input_file} -> {output_file}")
            generated_txt_files.append(output_file)
        else:
            print(f"转换失败: {input_file}")

    # 合并所有生成的TXT文件
    if generated_txt_files:
        # 获取最后一个文件夹名作为文件名
        folder_name = get_last_folder_name(folder_path)

        # 创建合并文件名
        combined_file = os.path.join(folder_path, f"{folder_name}.txt")

        if merge_txt_files(generated_txt_files, combined_file):
            print(f"成功合并 {len(generated_txt_files)} 个TXT文件到: {combined_file}")
        else:
            print("合并TXT文件失败")
    else:
        print("没有生成TXT文件，无法合并")

    print("所有操作完成")