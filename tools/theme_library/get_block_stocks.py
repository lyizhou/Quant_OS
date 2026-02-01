#!/usr/bin/env python3

"""
独立脚本：获取题材库数据
请求题材库接口，并将返回数据打印到控制台
"""

import socket
import ssl
import struct
import time

THEME_HOST = "hwsockapp.longhuvip.com"
THEME_PORT = 14000


# 从log.txt读取登录命令
def load_login_cmd():
    """从log.txt文件读取登录命令的十六进制字符串"""
    try:
        with open("log.txt", encoding="utf-8") as f:
            hex_str = f.read().strip()
        return bytes.fromhex(hex_str)
    except FileNotFoundError:
        raise FileNotFoundError("log.txt文件不存在，请确保log.txt文件在当前目录下")
    except Exception as e:
        raise Exception(f"读取log.txt文件失败: {str(e)}")


# 固定报文
LOGIN_CMD = load_login_cmd()
THEME_CMD = bytes.fromhex("40 00 0A 00 0B 0B C1 00 00 03 02 0B C1")


# 题材库数据字段定义（protobuf格式）


def parse_varint(data, start_index):
    """解析protobuf varint整数
    返回: (值, 消耗的字节数)
    """
    result = 0
    shift = 0
    pos = start_index

    while pos < len(data):
        byte = data[pos]
        result |= (byte & 0x7F) << shift
        pos += 1

        if (byte & 0x80) == 0:
            break
        shift += 7

        if shift >= 64:
            raise ValueError("Varint too long")

    return result, pos - start_index


def parse_theme_list(theme_body):
    """解析题材库列表（protobuf格式）

    从案例分析，每个题材的protobuf结构是嵌套消息：
    - 外层字段（如0x52开头）包含嵌套的题材消息
    - 嵌套消息中：
      - 字段1 (0x0A): ID（字符串）
      - 字段2 (0x12): 名称（UTF-8字符串）
      - 字段3 (0x22): 代码（字符串）
      - 字段5 (0x28): 可能是整数（varint）
      - 字段6 (0x30): 可能是整数（varint）
      - 字段7 (0x38): 可能是整数（varint）- 可能是涨停数
      - 字段8 (0x40): 可能是整数（varint）
      - 字段9 (0x48): 可能是整数（varint）
      - 字段10 (0x50): 可能是整数（varint）
      - 字段11 (0x58): 可能是整数（varint）
      - 其他字段可能包含时间戳等信息
    """
    theme_list = []
    index = 0

    # 跳过开头的global信息（如果有）
    # 查找第一个题材数据开始位置（通常是 0B C1 00 00 00 之后）
    start_marker = theme_body.find(b"\x0b\xc1\x00\x00\x00")
    if start_marker != -1:
        index = start_marker + 5

    # 解析每个题材
    # 从案例看，每个题材以0x0A开头（字段1，ID）是最可靠的标识
    while index < len(theme_body):
        theme_data = {}
        theme_start = index

        # 查找题材ID字段（0x0A），这是最可靠的标识
        next_id = theme_body.find(b"\x0a", index)
        if next_id == -1:
            break

        # 检查是否有足够的数据
        if next_id + 2 >= len(theme_body):
            break

        # 解析题材ID（字段1，格式：0A [长度] [ID字符串]）
        id_len = theme_body[next_id + 1]
        if next_id + 2 + id_len > len(theme_body):
            index = next_id + 1
            continue

        # 验证ID长度（正常ID应该是1-10个字符的数字字符串）
        if id_len > 20:  # ID过长，可能是解析错误
            index = next_id + 1
            continue

        theme_id_bytes = theme_body[next_id + 2 : next_id + 2 + id_len]
        theme_id_str = theme_id_bytes.decode("utf-8", errors="ignore")

        # 验证ID是否为纯数字字符串（正常ID应该是数字）
        if not theme_id_str or not theme_id_str.strip().isdigit():
            # ID不是纯数字，可能是解析错误，跳过
            index = next_id + 1
            continue

        # 清理ID（去除空白字符）
        theme_id_str = theme_id_str.strip()

        # 再次验证ID长度（清理后）
        if len(theme_id_str) > 10:  # 正常ID不会超过10位数字
            index = next_id + 1
            continue

        theme_data["id"] = theme_id_str
        index = next_id + 2 + id_len

        # 解析题材名称（字段2，格式：12 [长度] [名称UTF-8]）
        if index >= len(theme_body) - 1:
            if theme_data.get("id"):
                theme_list.append(theme_data)
            break

        if theme_body[index] == 0x12:
            name_len = theme_body[index + 1]
            if index + 2 + name_len > len(theme_body):
                if theme_data.get("id"):
                    theme_list.append(theme_data)
                break

            theme_name = theme_body[index + 2 : index + 2 + name_len].decode(
                "utf-8", errors="ignore"
            )
            theme_data["name"] = theme_name
            index = index + 2 + name_len
        else:
            # 没有名称字段，跳过这个题材
            index = next_id + 1
            continue

        # 解析题材代码（字段3，格式：22 [长度] [代码]）
        if index < len(theme_body) and theme_body[index] == 0x22:
            code_len = theme_body[index + 1]
            if index + 2 + code_len <= len(theme_body):
                theme_code = theme_body[index + 2 : index + 2 + code_len].decode(
                    "utf-8", errors="ignore"
                )
                theme_data["code"] = theme_code
                index = index + 2 + code_len

        # 继续解析其他字段，直到遇到下一个题材的开始（下一个0x0A）或数据结束
        # 查找下一个题材的开始位置
        next_theme_start = theme_body.find(b"\x0a", index)
        if next_theme_start == -1:
            next_theme_start = len(theme_body)

        # 保存当前题材的原始数据范围（用于调试）
        theme_data["raw_data"] = theme_body[index:next_theme_start]

        # 在当前题材范围内解析所有可能的整数字段
        theme_end = next_theme_start
        current_pos = index

        # 记录所有字段以便分析
        all_fields = []

        while current_pos < theme_end:
            if current_pos >= len(theme_body):
                break

            field_tag = theme_body[current_pos]
            field_num = field_tag >> 3
            wire_type = field_tag & 0x07

            current_pos += 1

            if wire_type == 0:  # Varint
                try:
                    value, consumed = parse_varint(theme_body, current_pos)
                    current_pos += consumed

                    # 记录所有字段
                    all_fields.append((field_num, value, "varint"))

                    # 根据字段编号存储值
                    # 根据抓包分析，涨停数可能在字段5、6、7、8等
                    # 我们尝试多个可能的字段
                    if field_num == 5:
                        theme_data["field5"] = value
                    elif field_num == 6:
                        theme_data["field6"] = value
                    elif field_num == 7:
                        theme_data["field7"] = value
                        # 字段7可能是涨停数，但需要验证
                        if value <= 100:  # 涨停数通常不会超过100
                            theme_data["limit_up_count"] = value
                    elif field_num == 8:
                        theme_data["field8"] = value
                        # 字段8也可能是涨停数
                        if value <= 100 and "limit_up_count" not in theme_data:
                            theme_data["limit_up_count"] = value
                    elif field_num == 9:
                        theme_data["field9"] = value
                    elif field_num == 10:
                        theme_data["field10"] = value
                    elif field_num == 11:
                        theme_data["field11"] = value
                except (ValueError, IndexError):
                    break
            elif wire_type == 2:  # Length-delimited
                if current_pos >= len(theme_body):
                    break
                length = theme_body[current_pos]
                current_pos += 1
                if current_pos + length > len(theme_body):
                    break
                # 记录length-delimited字段
                all_fields.append((field_num, f"<{length} bytes>", "length-delimited"))
                # 跳过length-delimited字段的内容
                current_pos += length
            else:
                # 其他wire type，跳过
                break

        # 保存所有字段信息（用于调试）
        theme_data["_all_fields"] = all_fields

        # 更新index到下一个题材的开始
        index = next_theme_start

        # 保存题材数据
        if theme_data.get("id") and theme_data.get("name"):
            theme_list.append(theme_data)

        # 防止无限循环
        if index <= theme_start:
            index += 1
        if index >= len(theme_body):
            break

    return theme_list


def parse_packet_40(data):
    """解析40类型数据包（题材库响应）
    按照4096字节分块，每个块单独解析
    """
    try:
        if len(data) < 3:
            raise ValueError("数据太短，无法解析包头")

        # 检查包头
        packet_type = data[0]
        packet_body_length = struct.unpack(">H", data[1:3])[0]

        if packet_type != 0x40:
            raise ValueError(f"错误的包类型: 0x{packet_type:02X}，期望0x40")

        # 检查数据长度
        if len(data) < 3 + packet_body_length:
            raise ValueError("数据长度不足")

        # 解析包体（跳过开头的global信息）
        message_body = data[3:]

        # 按照4096字节分块处理
        chunk_size = 4096
        all_themes = []
        total_chunks = (len(message_body) + chunk_size - 1) // chunk_size

        print(f"\n数据包体总长度: {len(message_body)} 字节")
        print(f"将分为 {total_chunks} 个块（每块 {chunk_size} 字节）进行解析\n")

        for chunk_idx in range(total_chunks):
            start_pos = chunk_idx * chunk_size
            end_pos = min(start_pos + chunk_size, len(message_body))
            chunk_data = message_body[start_pos:end_pos]

            print(f"{'=' * 80}")
            print(f"解析第 {chunk_idx + 1}/{total_chunks} 块")
            print(f"块位置: {start_pos} - {end_pos} (长度: {len(chunk_data)} 字节)")
            print(f"{'=' * 80}")

            # 解析当前块
            chunk_themes = parse_theme_list(chunk_data)
            if chunk_themes:
                print(f"本块解析出 {len(chunk_themes)} 个题材")
                all_themes.extend(chunk_themes)
            else:
                print("本块未解析出题材数据")
            print()

        print(f"\n总共解析出 {len(all_themes)} 个题材\n")
        return all_themes

    except Exception as e:
        print(f"解析40类型数据包出错: {str(e)}")
        import traceback

        traceback.print_exc()
        return None


def parse_packet_60(data):
    """解析60类型数据包（题材库响应）
    按照4096字节分块，每个块单独解析
    """
    try:
        if len(data) < 3:
            raise ValueError("数据太短，无法解析包头")

        # 检查包头
        packet_type = data[0]
        packet_body_length = struct.unpack(">H", data[1:3])[0]

        if packet_type != 0x60:
            raise ValueError(f"错误的包类型: 0x{packet_type:02X}，期望0x60")

        # 检查数据长度
        if len(data) < 3 + packet_body_length:
            raise ValueError("数据长度不足")

        # 解析包体（跳过开头的global信息）
        message_body = data[3:]

        # 按照4096字节分块处理
        chunk_size = 4096
        all_themes = []
        total_chunks = (len(message_body) + chunk_size - 1) // chunk_size

        print(f"\n数据包体总长度: {len(message_body)} 字节")
        print(f"将分为 {total_chunks} 个块（每块 {chunk_size} 字节）进行解析\n")

        for chunk_idx in range(total_chunks):
            start_pos = chunk_idx * chunk_size
            end_pos = min(start_pos + chunk_size, len(message_body))
            chunk_data = message_body[start_pos:end_pos]

            print(f"{'=' * 80}")
            print(f"解析第 {chunk_idx + 1}/{total_chunks} 块")
            print(f"块位置: {start_pos} - {end_pos} (长度: {len(chunk_data)} 字节)")
            print(f"{'=' * 80}")

            # 解析当前块
            chunk_themes = parse_theme_list(chunk_data)
            if chunk_themes:
                print(f"本块解析出 {len(chunk_themes)} 个题材")
                all_themes.extend(chunk_themes)
            else:
                print("本块未解析出题材数据")
            print()

        print(f"\n总共解析出 {len(all_themes)} 个题材\n")
        return all_themes

    except Exception as e:
        print(f"解析60类型数据包出错: {str(e)}")
        import traceback

        traceback.print_exc()
        return None


def _extract_theme_list_from_packet(packet):
    """从0x40/0x60数据包解析题材列表（无控制台打印，供API使用）"""
    if not packet or len(packet) < 3:
        return []

    packet_type = packet[0]
    if packet_type not in (0x40, 0x60):
        return []

    packet_body_length = struct.unpack(">H", packet[1:3])[0]
    if len(packet) < 3 + packet_body_length:
        return []

    message_body = packet[3:]
    chunk_size = 4096
    themes = []

    total_chunks = (len(message_body) + chunk_size - 1) // chunk_size
    for chunk_idx in range(total_chunks):
        start_pos = chunk_idx * chunk_size
        end_pos = min(start_pos + chunk_size, len(message_body))
        chunk_data = message_body[start_pos:end_pos]
        themes.extend(parse_theme_list(chunk_data) or [])

    # 过滤并精简字段
    simplified = []
    seen_ids = set()
    for theme in themes:
        theme_id = theme.get("id")
        theme_name = theme.get("name")

        # 基本验证
        if not theme_id or not theme_name:
            continue

        # 验证ID是否为纯数字字符串
        theme_id = str(theme_id).strip()
        if not theme_id.isdigit():
            continue

        # 验证ID长度（正常ID应该是1-10位数字）
        if len(theme_id) == 0 or len(theme_id) > 10:
            continue

        # 验证名称长度（正常名称应该不超过100个字符）
        if len(theme_name) == 0 or len(theme_name) > 100:
            continue

        # 检查名称是否包含异常的控制字符（排除常见的空白字符）
        has_invalid_char = False
        for c in theme_name:
            if ord(c) < 32 and c not in "\t\n\r":
                has_invalid_char = True
                break
        if has_invalid_char:
            continue

        # 去重
        if theme_id in seen_ids:
            continue
        seen_ids.add(theme_id)

        simplified.append(
            {
                "id": theme_id,
                "name": theme_name,
                "code": theme.get("code"),
                "limit_up_count": theme.get("limit_up_count", 0),
            }
        )
    return simplified


def fetch_theme_list(max_wait_packets=20, timeout=30):
    """获取题材列表数据，返回[{id,name,code,limit_up_count}, ...]"""
    ssl_sock = None
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)

        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

        ssl_sock = context.wrap_socket(sock, server_hostname=THEME_HOST)
        ssl_sock.connect((THEME_HOST, THEME_PORT))

        # 登录
        ssl_sock.sendall(LOGIN_CMD)
        logged_in = False
        for _ in range(max_wait_packets):
            packet = receive_packet(ssl_sock)
            if not packet:
                continue
            packet_type = packet[0]
            if packet_type in (0x30, 0x60):
                logged_in = True
                break
        if not logged_in:
            raise RuntimeError("登录题材库服务失败")

        # 心跳保持
        send_heartbeat(ssl_sock)

        # 发送题材库请求
        ssl_sock.sendall(THEME_CMD)

        # 等待题材数据包
        theme_list = []
        for _ in range(max_wait_packets):
            packet = receive_packet(ssl_sock)
            if not packet:
                continue
            packet_type = packet[0]
            if packet_type in (0x40, 0x60):
                theme_list = _extract_theme_list_from_packet(packet)
                if theme_list:
                    break
        return theme_list
    finally:
        if ssl_sock:
            try:
                ssl_sock.close()
            except Exception:
                pass


def send_heartbeat(sock):
    """发送心跳包
    心跳包格式：0x10 0x00 0x00 (包类型 + 包体长度0)
    """
    heartbeat_cmd = bytes.fromhex("10 00 00")
    sock.sendall(heartbeat_cmd)
    print("心跳包已发送")


def receive_packet(sock):
    """接收一个完整的数据包"""
    # 先读取3字节的包头
    header = b""
    while len(header) < 3:
        chunk = sock.recv(3 - len(header))
        if not chunk:
            return None
        header += chunk

    packet_type = header[0]
    packet_body_length = struct.unpack(">H", header[1:3])[0]
    total_length = 3 + packet_body_length

    # 读取包体
    body = b""
    while len(body) < packet_body_length:
        chunk = sock.recv(packet_body_length - len(body))
        if not chunk:
            return None
        body += chunk

    return header + body


def print_raw_packet(packet, label="接收到的数据包"):
    """打印原始数据包的十六进制内容"""
    if not packet:
        return

    packet_type = packet[0] if len(packet) > 0 else 0
    hex_str = " ".join(f"{b:02X}" for b in packet)

    print(f"\n{'=' * 80}")
    print(f"{label}")
    print(f"包类型: 0x{packet_type:02X} ({packet_type})")
    print(f"包长度: {len(packet)} 字节")
    print(f"十六进制: {hex_str}")
    print(f"{'=' * 80}\n")


def print_theme_data(theme_list):
    """打印题材库数据到控制台"""
    if not theme_list:
        print("没有题材库数据")
        return

    print(f"\n{'=' * 80}")
    print(f"题材库数据 (共 {len(theme_list)} 条)")
    print(f"{'=' * 80}\n")

    for idx, theme in enumerate(theme_list, 1):
        print(f"【题材 {idx}】")
        print(f"  ID: {theme.get('id', 'N/A')}")
        print(f"  名称: {theme.get('name', 'N/A')}")
        print(f"  代码: {theme.get('code', 'N/A')}")

        # 显示涨停数（如果存在）
        if "limit_up_count" in theme:
            print(f"  涨停数: {theme.get('limit_up_count', 'N/A')}")

        # 显示所有解析到的整数字段（用于调试分析）
        debug_fields = []
        for key in ["field5", "field6", "field7", "field8", "field9", "field10", "field11"]:
            if key in theme:
                debug_fields.append(f"{key}={theme[key]}")

        if debug_fields:
            print(f"  其他字段: {', '.join(debug_fields)}")

        # 显示所有字段的详细信息（用于分析哪个字段是涨停数）
        if "_all_fields" in theme:
            field_info = []
            for field_num, value, field_type in theme["_all_fields"]:
                if field_type == "varint":
                    field_info.append(f"字段{field_num}(varint)={value}")
                else:
                    field_info.append(f"字段{field_num}({field_type})={value}")
            if field_info:
                print(f"  所有字段: {', '.join(field_info)}")

        print()


def main():
    """主函数"""
    # 配置
    HOST = "hwsockapp.longhuvip.com"
    PORT = 14000

    print(f"正在连接到 {HOST}:{PORT}...")

    # 解析域名获取IP（用于显示域名和IP的对应关系）
    try:
        ip_address = socket.gethostbyname(HOST)
        print(f"域名解析: {HOST} -> {ip_address}")
    except socket.gaierror as e:
        print(f"DNS解析失败: {e}")
        ip_address = None

    try:
        # 创建socket连接
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(30)  # 设置超时30秒

        # 创建SSL上下文（不验证证书）
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

        # 包装为SSL socket
        ssl_sock = context.wrap_socket(sock, server_hostname=HOST)
        ssl_sock.connect((HOST, PORT))

        print("连接成功！")

        # 发送登录命令
        print("发送登录命令...")
        ssl_sock.sendall(LOGIN_CMD)
        print("登录命令已发送")

        # 等待登录响应
        print("等待登录响应...")
        logged_in = False
        max_wait = 10  # 最多等待10个包
        for _ in range(max_wait):
            packet = receive_packet(ssl_sock)
            if packet:
                packet_type = packet[0]
                print_raw_packet(packet, "登录响应")
                if packet_type == 0x30 or packet_type == 0x60:
                    print("登录成功！")
                    logged_in = True
                    break
                elif packet_type == 0x40:
                    print(">>> 收到0x40类型响应，继续等待登录响应...")
                    continue
                elif packet_type == 0x11:
                    print(">>> 收到心跳响应，继续等待登录响应...")
                    continue
                else:
                    print(f">>> 收到未知类型(0x{packet_type:02X})响应，继续等待登录响应...")
                    continue
        else:
            print("等待登录响应超时")
            ssl_sock.close()
            return

        if not logged_in:
            print("登录失败")
            ssl_sock.close()
            return

        # 等待一小段时间确保连接稳定
        time.sleep(0.5)

        # 发送心跳包
        print("\n发送心跳包...")
        send_heartbeat(ssl_sock)

        # 等待心跳响应（可选，最多等待3个包）
        print("等待心跳响应...")
        heartbeat_responded = False
        max_heartbeat_wait = 3
        for _ in range(max_heartbeat_wait):
            packet = receive_packet(ssl_sock)
            if packet:
                packet_type = packet[0]
                print_raw_packet(packet, "心跳响应")
                if packet_type == 0x11:
                    print("收到心跳响应")
                    heartbeat_responded = True
                    break
                elif packet_type == 0x40:
                    print(">>> 收到0x40类型响应，继续等待心跳响应...")
                    continue
                else:
                    print(f">>> 收到未知类型(0x{packet_type:02X})响应，继续等待心跳响应...")
                    continue
        else:
            print("未收到心跳响应（可能服务器不返回心跳响应，继续执行）")

        # 等待一小段时间
        time.sleep(0.3)

        # 发送题材库请求
        print("\n发送题材库请求...")

        # 发送固定的题材库请求报文
        theme_cmd = bytes.fromhex("40 00 0A 00 0B 0B C1 00 00 03 02 0B C1")
        ssl_sock.sendall(theme_cmd)
        print("题材库请求已发送 (固定报文: 40 00 0A 00 0B 0B C1 00 00 03 02 0B C1)")

        # 接收题材库数据
        print("\n等待题材库数据响应...")
        max_wait = 20  # 增加等待次数，以便接收更多响应
        received_count = 0
        for i in range(max_wait):
            packet = receive_packet(ssl_sock)
            if packet:
                received_count += 1
                packet_type = packet[0]

                # 打印所有接收到的原始数据包
                print_raw_packet(packet, f"响应 #{received_count}")

                if packet_type == 0x60:
                    print(">>> 这是题材库数据包(0x60)，开始解析...")
                    # 解析数据
                    theme_list = parse_packet_60(packet)
                    if theme_list is not None:
                        print_theme_data(theme_list)
                        break
                elif packet_type == 0x40:
                    print(">>> 这是题材库数据包(0x40)，开始解析...")
                    # 解析数据（0x40类型也是题材库数据）
                    theme_list = parse_packet_40(packet)
                    if theme_list is not None:
                        print_theme_data(theme_list)
                        break
                elif packet_type == 0x11:
                    print(">>> 这是心跳响应，继续等待...")
                    continue
                else:
                    print(f">>> 这是未知类型(0x{packet_type:02X})响应，继续等待...")
                    continue
            else:
                # 没有收到数据，可能是连接关闭或超时
                print(f"第 {i + 1} 次等待未收到数据")
                time.sleep(0.1)  # 短暂等待后继续
        else:
            if received_count == 0:
                print("等待题材库数据超时，未收到任何响应")
            else:
                print(f"已接收 {received_count} 个响应包，但未找到题材库数据包(0x40或0x60)")

        # 关闭连接
        ssl_sock.close()
        print("\n连接已关闭")

    except TimeoutError:
        print("连接超时")
    except Exception as e:
        print(f"发生错误: {str(e)}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
