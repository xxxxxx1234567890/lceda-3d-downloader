#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
立创EDA 3D模型下载器 CLI
用于从立创EDA/立创商城下载电子元器件的3D模型文件
"""

import argparse
import json
import os
import re
import sys
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path
from typing import Optional, List, Dict, Any

# API 端点
SEARCH_URL = "https://pro.lceda.cn/api/szlcsc/eda/product/list"
COMPONENT_URL = "https://pro.lceda.cn/api/components/{uuid}"
STEP_URL = "https://modules.lceda.cn/qAxj6KHrDKw4blvCG8QJPs7Y/{model_uuid}"
OBJ_URL = "https://modules.lceda.cn/3dmodel/{model_uuid}"

# 默认下载目录
DEFAULT_OUTPUT_DIR = Path.home() / "Downloads" / "lceda_models"

# 请求头
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
}


def http_get(url: str, timeout: int = 30) -> bytes:
    """发送HTTP GET请求"""
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            if response.info().get('Content-Encoding') == 'gzip':
                import gzip
                return gzip.decompress(response.read())
            return response.read()
    except urllib.error.URLError as e:
        raise ConnectionError(f"网络请求失败: {e}")


def http_get_json(url: str, timeout: int = 30) -> dict:
    """发送HTTP GET请求并解析JSON"""
    data = http_get(url, timeout)
    return json.loads(data.decode('utf-8'))


def sanitize_filename(name: str) -> str:
    """清理文件名，移除非法字符"""
    illegal_chars = '<>:"/\\|?*'
    for char in illegal_chars:
        name = name.replace(char, '_')
    name = ''.join(c for c in name if ord(c) >= 32)
    return name[:200]


def search_components(keyword: str, limit: int = 20) -> List[Dict[str, Any]]:
    """搜索元器件"""
    url = f"{SEARCH_URL}?wd={urllib.parse.quote(keyword)}"
    data = http_get_json(url)
    
    if not data.get('success') or data.get('code') != 0:
        raise ValueError(f"搜索失败: {data.get('message', '未知错误')}")
    
    results = data.get('result', [])
    components_with_3d = []
    
    for item in results:
        attrs = item.get('attributes', {})
        model_uuid = attrs.get('3D Model') or attrs.get('_3D_Model')
        if model_uuid:
            components_with_3d.append({
                'uuid': item.get('uuid'),
                'title': item.get('title', ''),
                'display_title': item.get('display_title', ''),
                'manufacturer': attrs.get('Manufacturer', ''),
                'manufacturer_part': attrs.get('Manufacturer_Part', ''),
                'footprint': item.get('footprint', {}).get('display_title', '') if item.get('footprint') else '',
                'model_uuid': model_uuid,
                'model_transform': attrs.get('3D Model Transform') or attrs.get('_3D_Model_Transform', ''),
                'lcsc_part': attrs.get('LCSC Part Name', ''),
            })
    
    return components_with_3d[:limit]


def get_component_detail(uuid: str) -> Dict[str, Any]:
    """获取元器件详情（含真正的3D模型UUID）"""
    url = COMPONENT_URL.format(uuid=uuid) + f"?uuid={uuid}"
    data = http_get_json(url)
    
    result = data.get('result', {})
    return {
        'uuid': result.get('uuid', uuid),
        'model_uuid': result.get('_3d_model_uuid', '') or result.get('3d_model_uuid', ''),
        'title': result.get('title', ''),
        'display_title': result.get('display_title', ''),
    }


def download_step(uuid: str, model_uuid: str, output_dir: Path, filename_prefix: str = '') -> Optional[Path]:
    """下载STEP模型"""
    if not model_uuid:
        detail = get_component_detail(uuid)
        model_uuid = detail.get('model_uuid', '')
    
    if not model_uuid:
        print(f"器件 {uuid} 没有3D模型", file=sys.stderr)
        return None
    
    url = STEP_URL.format(model_uuid=model_uuid)
    
    if not filename_prefix:
        filename_prefix = sanitize_filename(model_uuid)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    filepath = output_dir / f"{filename_prefix}.step"
    
    try:
        import requests
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': '*/*',
            'Referer': 'https://pro.lceda.cn/',
        }
        resp = requests.get(url, headers=headers, timeout=120)
        if resp.status_code == 200:
            with open(filepath, 'wb') as f:
                f.write(resp.content)
            return filepath
        print(f"下载失败: HTTP {resp.status_code}", file=sys.stderr)
        return None
    except ImportError:
        req = urllib.request.Request(url, headers={'User-Agent': HEADERS['User-Agent']})
        with urllib.request.urlopen(req, timeout=120) as response:
            content = response.read()
            if response.info().get('Content-Encoding') == 'gzip':
                import gzip
                content = gzip.decompress(content)
            with open(filepath, 'wb') as f:
                f.write(content)
            return filepath
    except Exception as e:
        print(f"下载失败: {e}", file=sys.stderr)
        return None


def download_obj(uuid: str, model_uuid: str, output_dir: Path, filename_prefix: str = '') -> Optional[Path]:
    """下载OBJ模型（自动分离MTL）"""
    if not model_uuid:
        detail = get_component_detail(uuid)
        model_uuid = detail.get('model_uuid', '')
    
    if not model_uuid:
        print(f"器件 {uuid} 没有3D模型", file=sys.stderr)
        return None
    
    url = OBJ_URL.format(model_uuid=model_uuid)
    
    if not filename_prefix:
        filename_prefix = sanitize_filename(model_uuid)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    obj_filepath = output_dir / f"{filename_prefix}.obj"
    mtl_filepath = output_dir / f"{filename_prefix}.mtl"
    
    try:
        import requests
        headers = {'User-Agent': HEADERS['User-Agent'], 'Referer': 'https://pro.lceda.cn/'}
        resp = requests.get(url, headers=headers, timeout=60)
        if resp.status_code != 200:
            print(f"下载失败: HTTP {resp.status_code}", file=sys.stderr)
            return None
        content = resp.text
    except ImportError:
        data = http_get(url)
        content = data.decode('utf-8')
    except Exception as e:
        print(f"OBJ下载失败: {e}", file=sys.stderr)
        return None
    
    # 分离OBJ和MTL
    try:
        obj_lines = []
        mtl_lines = []
        lines = content.split('\n')
        i = 0
        while i < len(lines):
            line = lines[i]
            if line.strip().startswith('newmtl'):
                mtl_lines.append(line)
                for j in range(1, 4):
                    if i + j < len(lines):
                        mtl_lines.append(lines[i + j])
                i += 4
                while i < len(lines) and (not lines[i].strip() or lines[i].strip().startswith('illum')):
                    if lines[i].strip().startswith('illum'):
                        mtl_lines.append(lines[i])
                    i += 1
                continue
            else:
                obj_lines.append(line)
                i += 1
        
        obj_content = f"mtllib {filename_prefix}.mtl\n" + '\n'.join(obj_lines)
        
        with open(obj_filepath, 'w') as f:
            f.write(obj_content)
        with open(mtl_filepath, 'w') as f:
            f.write('\n'.join(mtl_lines))
        
        return obj_filepath
    except Exception as e:
        print(f"OBJ/MTL分离失败: {e}", file=sys.stderr)
        return None


def generate_preview(step_filepath: Path, output_dir: Path = None) -> Optional[Path]:
    """
    从STEP文件生成预览图片（三视图：顶视图、正视图、侧视图）
    需要安装 matplotlib
    """
    try:
        import matplotlib.pyplot as plt
        import matplotlib.patches as patches
        from matplotlib.patches import FancyBboxPatch
        import numpy as np
        
        if output_dir is None:
            output_dir = step_filepath.parent
        
        # 解析STEP文件获取尺寸信息
        with open(step_filepath, 'r', errors='ignore') as f:
            content = f.read()
        
        # 提取坐标点估算边界
        bounds = {'x_min': 0, 'x_max': 10, 'y_min': 0, 'y_max': 10, 'z_min': 0, 'z_max': 3}
        points = re.findall(r'CARTESIAN_POINT\s*\(\s*[\'"]*[^\'"]*[\'"]*\s*,\s*\(\s*([-\d.]+)\s*,\s*([-\d.]+)\s*,\s*([-\d.]+)\s*\)', content)
        if points:
            x_vals = [float(p[0]) for p in points]
            y_vals = [float(p[1]) for p in points]
            z_vals = [float(p[2]) for p in points]
            if x_vals:
                bounds['x_min'], bounds['x_max'] = min(x_vals), max(x_vals)
            if y_vals:
                bounds['y_min'], bounds['y_max'] = min(y_vals), max(y_vals)
            if z_vals:
                bounds['z_min'], bounds['z_max'] = min(z_vals), max(z_vals)
        
        # 创建三视图
        fig, axes = plt.subplots(1, 3, figsize=(15, 5))
        fig.suptitle(f'{step_filepath.stem}', fontsize=14, fontweight='bold')
        
        width = bounds['x_max'] - bounds['x_min']
        length = bounds['y_max'] - bounds['y_min']
        height = bounds['z_max'] - bounds['z_min']
        
        # 顶视图 (X-Y)
        ax1 = axes[0]
        ax1.set_title('Top View (X-Y)')
        rect1 = FancyBboxPatch((bounds['x_min'], bounds['y_min']), width, length,
                               boxstyle="round,pad=0.05", facecolor='steelblue', 
                               edgecolor='navy', linewidth=2, alpha=0.7)
        ax1.add_patch(rect1)
        ax1.set_xlim(bounds['x_min'] - 1, bounds['x_max'] + 1)
        ax1.set_ylim(bounds['y_min'] - 1, bounds['y_max'] + 1)
        ax1.set_aspect('equal')
        ax1.grid(True, linestyle='--', alpha=0.5)
        ax1.set_xlabel(f'X: {width:.2f}mm')
        ax1.set_ylabel(f'Y: {length:.2f}mm')
        
        # 正视图 (X-Z)
        ax2 = axes[1]
        ax2.set_title('Front View (X-Z)')
        rect2 = FancyBboxPatch((bounds['x_min'], bounds['z_min']), width, height,
                               boxstyle="round,pad=0.02", facecolor='coral',
                               edgecolor='darkred', linewidth=2, alpha=0.7)
        ax2.add_patch(rect2)
        ax2.set_xlim(bounds['x_min'] - 1, bounds['x_max'] + 1)
        ax2.set_ylim(bounds['z_min'] - 1, max(bounds['z_max'] + 1, 2))
        ax2.set_aspect('equal')
        ax2.grid(True, linestyle='--', alpha=0.5)
        ax2.set_xlabel(f'X: {width:.2f}mm')
        ax2.set_ylabel(f'Z: {height:.2f}mm')
        
        # 侧视图 (Y-Z)
        ax3 = axes[2]
        ax3.set_title('Side View (Y-Z)')
        rect3 = FancyBboxPatch((bounds['y_min'], bounds['z_min']), length, height,
                               boxstyle="round,pad=0.02", facecolor='lightgreen',
                               edgecolor='darkgreen', linewidth=2, alpha=0.7)
        ax3.add_patch(rect3)
        ax3.set_xlim(bounds['y_min'] - 1, bounds['y_max'] + 1)
        ax3.set_ylim(bounds['z_min'] - 1, max(bounds['z_max'] + 1, 2))
        ax3.set_aspect('equal')
        ax3.grid(True, linestyle='--', alpha=0.5)
        ax3.set_xlabel(f'Y: {length:.2f}mm')
        ax3.set_ylabel(f'Z: {height:.2f}mm')
        
        plt.tight_layout()
        preview_path = output_dir / f"{step_filepath.stem}_preview.png"
        plt.savefig(preview_path, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close()
        
        return preview_path
    except ImportError:
        print("警告: matplotlib未安装，跳过预览图生成", file=sys.stderr)
        return None
    except Exception as e:
        print(f"预览图生成失败: {e}", file=sys.stderr)
        return None


def cmd_search(args):
    """搜索命令"""
    results = search_components(args.keyword, args.limit)
    if not results:
        print("未找到有3D模型的器件")
        return
    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        print(f"找到 {len(results)} 个有3D模型的器件:\n")
        for i, item in enumerate(results, 1):
            print(f"{i}. {item['display_title']}")
            print(f"   型号: {item['manufacturer_part']}")
            print(f"   封装: {item['footprint']}")
            print(f"   制造商: {item['manufacturer']}")
            print(f"   UUID: {item['uuid']}")
            print()


def cmd_download(args):
    """下载命令（支持批量）"""
    output_dir = Path(args.output) if args.output else DEFAULT_OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    
    results = []
    
    for idx, uuid_or_keyword in enumerate(args.uuid, 1):
        if len(args.uuid) > 1:
            print(f"\n[{idx}/{len(args.uuid)}] 正在处理器件: {uuid_or_keyword}")
        else:
            print(f"正在处理器件: {uuid_or_keyword}")
        
        # 搜索获取器件信息
        components = search_components(uuid_or_keyword, limit=10)
        
        if not components:
            try:
                detail = get_component_detail(uuid_or_keyword)
                if detail.get('model_uuid'):
                    components = [{
                        'uuid': uuid_or_keyword,
                        'display_title': detail.get('display_title', uuid_or_keyword[:16]),
                        'footprint': '',
                        'model_uuid': detail['model_uuid'],
                    }]
            except:
                pass
        
        if not components:
            print(f"未找到器件: {uuid_or_keyword}")
            continue
        
        comp = components[0]
        
        # 获取真正的模型UUID
        component_3d_uuid = comp['model_uuid']
        print(f"  获取模型详情: {component_3d_uuid}")
        
        detail = get_component_detail(component_3d_uuid)
        real_model_uuid = detail.get('model_uuid', '')
        
        if not real_model_uuid:
            print(f"  无法获取3D模型UUID")
            continue
        
        print(f"  真实模型UUID: {real_model_uuid}")
        
        filename_prefix = sanitize_filename(
            f"{comp['display_title']}_{comp['footprint']}" if comp['footprint'] else comp['display_title']
        )
        
        # 下载模型
        if args.format == 'step':
            filepath = download_step(component_3d_uuid, real_model_uuid, output_dir, filename_prefix)
        else:
            filepath = download_obj(component_3d_uuid, real_model_uuid, output_dir, filename_prefix)
        
        if filepath:
            result = {
                'uuid': comp['uuid'],
                'display_title': comp['display_title'],
                'format': args.format,
                'filepath': str(filepath),
            }
            
            # 生成预览图
            if args.preview:
                preview_path = generate_preview(filepath, output_dir)
                if preview_path:
                    result['preview'] = str(preview_path)
                    print(f"  预览图: {preview_path}")
            
            results.append(result)
            print(f"  ✓ 下载成功: {filepath}")
        else:
            print(f"  ✗ 下载失败: {uuid_or_keyword}")
    
    # 汇总
    print(f"\n{'='*50}")
    print(f"下载完成: 成功 {len(results)}/{len(args.uuid)}")
    
    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    
    return results


def cmd_info(args):
    """获取器件详情"""
    detail = get_component_detail(args.uuid)
    if args.json:
        print(json.dumps(detail, ensure_ascii=False, indent=2))
    else:
        print(f"器件UUID: {detail.get('uuid')}")
        print(f"3D模型UUID: {detail.get('model_uuid')}")
        print(f"标题: {detail.get('display_title', 'N/A')}")


def main():
    parser = argparse.ArgumentParser(
        description='立创EDA 3D模型下载器',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 搜索器件
  python3 client.py search --keyword "USB-C" --limit 5
  
  # 下载单个器件
  python3 client.py download --uuid "STM32F103" --format step --preview
  
  # 批量下载多个器件
  python3 client.py download --uuid "USB-C" "TYPE-C" "STM32" --format step --preview
  
  # JSON输出
  python3 client.py search --keyword "USB-C" --json
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='命令')
    
    # search
    search_parser = subparsers.add_parser('search', help='搜索元器件')
    search_parser.add_argument('--keyword', '-k', required=True, help='搜索关键字')
    search_parser.add_argument('--limit', '-l', type=int, default=20, help='返回结果数量')
    search_parser.add_argument('--json', action='store_true', help='JSON格式输出')
    
    # download
    download_parser = subparsers.add_parser('download', help='下载模型（支持批量）')
    download_parser.add_argument('--uuid', '-u', required=True, nargs='+', help='器件UUID或关键字（支持多个）')
    download_parser.add_argument('--format', '-f', choices=['step', 'obj'], default='step', help='模型格式')
    download_parser.add_argument('--output', '-o', help='输出目录')
    download_parser.add_argument('--preview', '-p', action='store_true', help='生成预览图')
    download_parser.add_argument('--json', action='store_true', help='JSON格式输出')
    
    # info
    info_parser = subparsers.add_parser('info', help='获取器件详情')
    info_parser.add_argument('--uuid', '-u', required=True, help='器件UUID')
    info_parser.add_argument('--json', action='store_true', help='JSON格式输出')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    if args.command == 'search':
        cmd_search(args)
    elif args.command == 'download':
        cmd_download(args)
    elif args.command == 'info':
        cmd_info(args)


if __name__ == '__main__':
    main()
