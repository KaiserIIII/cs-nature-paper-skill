# 提示词示例

## 完整科研工程任务

```text
使用 $research-engineering-suite 帮我处理这个课题：先把研究问题收窄，再列出需要查证的文献和数据，接着设计实验代码，最后给出验证和论文写作计划。
```

## 文献与证据

```text
使用 $research-engineering-suite 帮我做一个小型文献调研。要求区分证据、推断和建议；每个关键 claim 都要说明需要什么来源支撑。
```

## 实验 coding

```text
使用 $research-engineering-suite 实现这个实验脚本。先读 repo 结构和现有 helper，定义最小可测试行为，再写实现和复现命令。
```

## Debug

```text
使用 $research-engineering-suite 调试这个 traceback。不要先猜原因，先读取日志、命令、输入路径和相关代码，然后给出最小修复和验证命令。
```

## 图像或数据结果异常

```text
使用 $research-engineering-suite 检查这个结果图为什么不对。请把 source data、坐标变换、contrast、projection、render/export 分开验证。
```

## 论文写作

```text
使用 $research-engineering-suite 把这些结果写成论文 Results 和 Methods。每个结论都要标注来自哪个实验、文件、图或引用。
```

## 审稿意见和修回

```text
使用 $research-engineering-suite 分析这些 reviewer comments。输出 major/minor 分类、必须补的实验、可通过文字澄清的问题、以及逐点 rebuttal 草稿。
```

## 完成前检查

```text
使用 $research-engineering-suite 做最终验证：检查代码、文档、引用、输出文件和复现命令是否足以支撑我准备提交的结论。
```
