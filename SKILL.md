---
name: lceda-3d-downloader
description: 立创EDA元器件3D模型下载技能。支持搜索元器件、筛选有3D模型的器件、下载STEP/OBJ格式模型文件、生成预览图、批量下载。当用户提到下载立创3D模型、LCEDA模型、元器件3D封装时触发。
icon: 🔧
---

# 立创EDA 3D模型下载器

## 功能

- ✅ 搜索元器件（自动筛选有3D模型的器件）
- ✅ 下载 STEP 格式模型（用于 CAD 软件）
- ✅ 下载 OBJ 格式模型（用于预览）
- ✅ 生成预览图（三视图：顶视、正视、侧视）
- ✅ 批量下载（一次下载多个器件）
- ✅ JSON 输出（便于程序解析）

## 触发信号

用户提到下列需求时触发本技能：
- "下载 xxx 的3D模型"
- "帮我找 xxx 的STEP模型"
- "立创 xxx 器件的3D封装"
- "搜索 xxx 的3D模型"
- "批量下载 xxx yyy 的3D模型"

## 执行原则

1. 搜索元器件时，只展示有3D模型的器件
2. 如果搜索结果唯一且有3D模型，直接下载
3. 如果搜索结果不唯一，列出供用户选择（编号列表）
4. 下载完成后，通过 `<qqfile>` 发送给用户
5. 生成预览图片，通过 `<qqimg>` 发送给用户
6. 批量下载时，显示进度（如 [1/3]、[2/3]）

## 命令示例

### 搜索元器件

```bash
# 基础搜索
python3 client.py search --keyword "USB-C"

# 限制结果数量
python3 client.py search --keyword "STM32" --limit 10

# JSON 输出
python3 client.py search --keyword "TYPE-C" --json
```

### 下载单个器件

```bash
# 下载 STEP 格式
python3 client.py download --uuid "STM32F103" --format step

# 下载并生成预览图
python3 client.py download --uuid "USB-C" --format step --preview

# 指定输出目录
python3 client.py download --uuid "TYPE-C" --format step -o /tmp/models
```

### 批量下载

```bash
# 批量下载多个器件（空格分隔）
python3 client.py download --uuid "USB-C" "STM32F103" "TYPE-C" --format step --preview

# 批量下载 JSON 输出
python3 client.py download --uuid "USB-C" "STM32" --format step --json
```

### 获取器件详情

```bash
python3 client.py info --uuid "3a41b9ec9b654a0fad4d118405ec6290"
```

## 参数说明

### `search` 搜索

| 参数 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `--keyword` / `-k` | 是 | 无 | 搜索关键字 |
| `--limit` / `-l` | 否 | 20 | 返回结果数量 |
| `--json` | 否 | 关闭 | JSON 格式输出 |

### `download` 下载

| 参数 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `--uuid` / `-u` | 是 | 无 | 器件UUID或关键字（支持多个，空格分隔） |
| `--format` / `-f` | 否 | step | 模型格式：step / obj |
| `--output` / `-o` | 否 | ~/Downloads/lceda_models/ | 输出目录 |
| `--preview` / `-p` | 否 | 关闭 | 生成预览图 |
| `--json` | 否 | 关闭 | JSON 格式输出 |

### `info` 详情

| 参数 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `--uuid` / `-u` | 是 | 无 | 器件UUID |
| `--json` | 否 | 关闭 | JSON 格式输出 |

## 工作流程

### 流程 A：唯一结果自动下载

```
用户："下载 STM32F103VBT6 的3D模型"
     ↓
搜索 "STM32F103VBT6" → 结果唯一且有3D模型
     ↓
下载 STEP 文件 → 生成预览图
     ↓
发送文件和预览图给用户
```

### 流程 B：多结果选择

```
用户："下载 USB-C 的3D模型"
     ↓
搜索 "USB-C" → 结果不唯一
     ↓
列出有3D模型的器件：
  1. TYPE-C 16PIN 2MD(073)
  2. TYPE-C-31-M-12
  3. TYPE-C16PIN
     ↓
用户选择编号（如："下载第1个"）
     ↓
下载对应器件 → 生成预览图
     ↓
发送文件和预览图给用户
```

### 流程 C：批量下载

```
用户："批量下载 USB-C STM32F103 TYPE-C 的3D模型"
     ↓
搜索并下载每个器件（显示进度）
  [1/3] USB-C ✓
  [2/3] STM32F103 ✓
  [3/3] TYPE-C ✓
     ↓
发送所有文件给用户
```

## 输出示例

### 搜索结果（文本）

```
找到 3 个有3D模型的器件:

1. TYPE-C 16PIN 2MD(073)
   型号: 
   封装: USB-C-SMD_TYPE-C-6PIN-2MD-073
   制造商: SHOU HAN(首韩)
   UUID: 45fb1c7fbc5b42ebbb9f47d092c4f3dc

2. TYPE-C-31-M-12
   型号: 
   封装: USB-C_SMD-TYPE-C-31-M-12_1
   制造商: 韩国韩荣
   UUID: 74d31c19993b4b9581f3175a7da4b280
```

### 下载结果（JSON）

```json
[
  {
    "uuid": "2cf867601c904dc19db2917730c9fbec",
    "display_title": "STM32F103VBT6",
    "format": "step",
    "filepath": "/home/user/Downloads/lceda_models/STM32F103VBT6_LQFP-100.step",
    "preview": "/home/user/Downloads/lceda_models/STM32F103VBT6_LQFP-100_preview.png"
  }
]
```

## API 端点

```python
# 搜索元器件
SEARCH_URL = "https://pro.lceda.cn/api/szlcsc/eda/product/list?wd={keyword}"

# 获取器件详情（含真正的3D模型UUID）
COMPONENT_URL = "https://pro.lceda.cn/api/components/{uuid}?uuid={uuid}"

# 下载STEP模型
STEP_URL = "https://modules.lceda.cn/qAxj6KHrDKw4blvCG8QJPs7Y/{model_uuid}"

# 下载OBJ模型
OBJ_URL = "https://modules.lceda.cn/3dmodel/{model_uuid}"
```

## 注意事项

1. 仅支持立创商城有3D模型的元器件
2. 搜索结果中的 `attributes['3D Model']` 是器件UUID，需要再调用 `/api/components/` 获取真正的模型UUID
3. 预览图生成需要安装 matplotlib
4. 大模型文件下载可能需要较长时间

## 依赖

```
requests>=2.28.0
matplotlib>=3.5.0  # 预览图生成（可选）
```
