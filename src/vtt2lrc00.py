import sys
from datetime import datetime, timedelta
import chardet

def parse_time(time_str):
    # VTT中的时间格式可能是 "HH:MM:SS.mmm" 或 "MM:SS.mmm"
    time_str = time_str.strip()
    try:
        if len(time_str.split(':')) == 3:
            dt = datetime.strptime(time_str, "%H:%M:%S.%f")
        else:
            dt = datetime.strptime(time_str, "%M:%S.%f")
    except ValueError as e:
        raise ValueError(f"无法解析时间字符串: '{time_str}'") from e
    return dt

def format_time(time):
    return time.strftime("%M:%S.%f")[:8]

DEFAULT_THRESHOLD = timedelta(seconds=2)

def vtt2lrc(vtt, header=True, threshold=DEFAULT_THRESHOLD):
    lrc = ""
    
    if header:
        lrc += "[re:vtt2lrc]\n"

    last_end = parse_time("23:59:59.99")  # 一个很大的时间值

    # 将VTT内容按两个换行符分割成多个块
    chunks = vtt.split("\n\n")[1:]  # 跳过第一个块（通常是WEBVTT头部）

    for idx, chunk in enumerate(chunks, start=1):
        if not chunk.strip():
            continue
        
        lines = chunk.split("\n")
        if '-->' in lines[0]:
            time_line = lines[0]
            text = "\n".join(lines[1:]).strip()
        elif len(lines) >= 2 and '-->' in lines[1]:
            # 第一行是标识符，第二行是时间码
            time_line = lines[1]
            text = "\n".join(lines[2:]).strip()
        else:
            print(f"警告: 无法解析第 {idx} 个字幕块。")
            continue
        
        try:
            begin_str, end_str = map(str.strip, time_line.split("-->"))
            begin, end = map(parse_time, [begin_str, end_str])
        except ValueError as e:
            print(f"错误: 无法解析时间码 '{time_line}' 在第 {idx} 个字幕块。")
            continue
        
        if begin - last_end > threshold:
            lrc += f"[{format_time(last_end)}]\n"
            
        lrc += f"[{format_time(begin)}] {text}\n"
        
        last_end = end
        
    lrc += f"[{format_time(last_end)}]\n"
    
    return lrc

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python vtt2lrc.py input.vtt output.lrc")
        sys.exit(1)
        
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    try:
        # 自动检测文件编码
        with open(input_file, 'rb') as f:
            raw_data = f.read()
            result = chardet.detect(raw_data)
            encoding = result['encoding']
            if encoding is None:
                raise ValueError("无法检测文件编码。")
            
            vtt = raw_data.decode(encoding)
    except UnicodeDecodeError:
        print(f"无法使用编码 {encoding} 读取文件 {input_file}，请检查文件编码。")
        sys.exit(1)
    except FileNotFoundError:
        print(f"文件 {input_file} 未找到。")
        sys.exit(1)
    except Exception as e:
        print(f"读取文件时出错: {e}")
        sys.exit(1)
    
    try:
        lrc = vtt2lrc(vtt)
        # 将LRC内容写入文件，使用UTF-8编码
        with open(output_file, 'w', encoding='utf-8') as f_out:
            f_out.write(lrc)
        print(f"转换成功，LRC文件已保存为 {output_file}")
    except Exception as e:
        print(f"转换过程中出错: {e}")
        sys.exit(1)
