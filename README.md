# 立创EDA 3D模型下载器

这是一个 [OpenClaw](https://openclaw.ai) AgentSkill，用于下载立创EDA元器件的3D模型。

## 功能

- ✅ 搜索元器件（自动筛选有3D模型的器件）
- ✅ 下载 STEP 格式模型（用于 CAD 软件）
- ✅ 下载 OBJ 格式模型（用于预览）
- ✅ 生成预览图（三视图：顶视、正视、侧视）
- ✅ 批量下载（一次下载多个器件）
- ✅ JSON 输出（便于程序解析）

## 安装

```bash
# 克隆仓库
git clone https://github.com/xxxxxx1234567890/lceda-3d-downloader.git

# 复制到 OpenClaw 技能目录
cp -r lceda-3d-downloader ~/.openclaw/workspace/skills/

# 安装依赖
pip3 install -r lceda-3d-downloader/requirements.txt
```

## 使用

在 OpenClaw 中说：
- "下载 USB-C 的3D模型"
- "帮我找 STM32 的STEP模型"
- "搜索 TYPE-C 的3D封装"

## 文件说明

| 文件 | 说明 |
|:-----|:-----|
| `SKILL.md` | 技能描述文件 |
| `client.py` | 主程序 |
| `requirements.txt` | Python 依赖 |

## 许可证

MIT License
