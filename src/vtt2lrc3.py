import sys
import os
import glob
import shutil
import chardet
from datetime import datetime, timedelta
import io

def parse_time(time_str):
    time_str = time_str.strip()
    parts = time_str.split(':')
    if len(parts) == 3:
        hour, minute, rest = parts
    else:
        hour = 0
        minute, rest = parts
    
    second_part = rest.split('.')
    second = second_part[0]
    micro = second_part[1] if len(second_part) > 1 else '0'
    
    total_seconds = int(hour) * 3600 + int(minute) * 60 + int(second)
    micro = int(micro.ljust(6, '0'))  # 确保有 6 位微秒
    
    # 总微秒数
    return total_seconds * 1000000 + micro

def format_time(time_micro):
    # 将微秒转换为时分秒格式
    total_seconds = time_micro // 1000000
    micro = time_micro % 1000000
    
    minutes, seconds = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    
    # 格式化为 MM:SS.ssssss
    return f"{minutes:02d}:{seconds:02d}.{micro:06d}"[:8]

DEFAULT_THRESHOLD_MICRO = timedelta(seconds=2).microseconds

def vtt2lrc(vtt, header=True, threshold_micro=DEFAULT_THRESHOLD_MICRO):
    if header:
        lrc = io.StringIO()
        lrc.write("[re:vtt2lrc]\n")
    else:
        lrc = io.StringIO()
    
    last_end = parse_time("23:59:59.999")
    
    lines = vtt.split("\n")
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
    
    last_end_micro = parse_time("23:59:59.999")
    
    for idx, block in enumerate(blocks, start=1):
        time_line = None
        text_lines = []
        for line in block:
            if "-->" in line:
                time_line = line
            else:
                text_lines.append(line.strip())
        
        if not time_line:
            continue
        
        # 解析时间
        begin_str, end_str = map(str.strip, time_line.split("-->"))
        begin_micro = parse_time(begin_str)
        end_micro = parse_time(end_str)
        
        # 格式化时间
        begin_formatted = format_time(begin_micro)
        
        # 检查阈值
        if begin_micro - last_end_micro > threshold_micro:
            lrc.write(f"[{format_time(last_end_micro)}]\n")
        
        # 写入 LRC 行
        lrc.write(f"[{begin_formatted}] {' '.join(text_lines)}\n")
        
        last_end_micro = end_micro
    
    # 写入最后的时间
    lrc.write(f"[{format_time(last_end_micro)}]\n")
    
    return lrc.getvalue()

def convert_vtt_to_lrc(input_file, output_file):
    try:
        with open(input_file, 'rb') as f:
            raw_data = f.read()
            
            # 尝试使用 UTF-8 解码
            try:
                vtt = raw_data.decode('utf-8')
            except UnicodeDecodeError:
                # 使用 chardet 检测编码
                result = chardet.detect(raw_data)
                encoding = result['encoding']
                if encoding is None:
                    raise ValueError("无法检测文件编码。")
                vtt = raw_data.decode(encoding)
        
        lrc = vtt2lrc(vtt)
        with open(output_file, 'w', encoding='utf-8') as f_out:
            f_out.write(lrc)
        return True
    except Exception as e:
        print(f"转换失败: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python vtt2lrc.py <folder_path>")
        sys.exit(1)
    
    folder_path = sys.argv[1]

    if not os.path.isdir(folder_path):
        print(f"路径 '{folder_path}' 无效或不是文件夹。")
        sys.exit(1)

    res_folder = os.path.join(os.path.dirname(folder_path), "res")
    os.makedirs(res_folder, exist_ok=True)

    vtt_files = glob.glob(os.path.join(folder_path, "*.vtt"))
    
    if not vtt_files:
        print("该文件夹中没有找到 .vtt 文件。")
        sys.exit(1)
    
    for vtt_file in vtt_files:
        output_file = os.path.join(res_folder, os.path.splitext(os.path.basename(vtt_file))[0] + ".lrc")
        if convert_vtt_to_lrc(vtt_file, output_file):
            print(f"成功转换: {vtt_file} -> {output_file}")
        else:
            print(f"转换失败: {vtt_file}")
    
    # 清空源文件夹中的所有文件
    for file in os.listdir(folder_path):
        file_path = os.path.join(folder_path, file)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print(f"无法删除文件 {file_path}: {e}")

    print("所有文件转换完成，并已清空目标文件夹")