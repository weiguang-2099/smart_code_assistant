"""
LangChain Tools for Code Analysis

定义用于代码分析和审查的工具，供 LangChain Agent 调用
"""
import re
import ast
from typing import Optional
from langchain_core.tools import tool


@tool
def analyze_code_structure(code: str, language: str = "python") -> str:
    """
    分析代码结构，提取函数、类、依赖等基本信息

    Args:
        code: 要分析的代码
        language: 编程语言 (默认: python)

    Returns:
        代码结构分析结果
    """
    lines = code.split('\n')
    total_lines = len(lines)
    code_lines = len([l for l in lines if l.strip() and not l.strip().startswith('#')])
    comment_lines = len([l for l in lines if l.strip().startswith('#')])
    blank_lines = total_lines - code_lines - comment_lines

    result = f"""📊 代码结构分析 [{language}]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📈 基本统计:
  • 总行数: {total_lines}
  • 代码行: {code_lines}
  • 注释行: {comment_lines}
  • 空行: {blank_lines}
  • 代码密度: {code_lines/total_lines*100:.1f}%
"""

    if language.lower() == "python":
        try:
            tree = ast.parse(code)
            functions = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
            classes = [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
            imports = [node for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom))]

            result += f"""
🔧 函数统计:
  • 函数数量: {len(functions)}
  • 平均行数: {sum(len(ast.get_source_segment(code, f) or '') for f in functions) // len(functions) if functions else 0}

📦 类统计:
  • 类数量: {len(classes)}

📥 导入统计:
  • 导入模块: {len(imports)}"""
        except:
            result += "\n⚠️  AST 解析失败，使用基础分析"

        # 使用正则表达式作为备用
        functions = len(re.findall(r'def \w+\(', code))
        classes = len(re.findall(r'class \w+', code))
        imports = len(re.findall(r'^import |^from .* import', code, re.MULTILINE))

        result += f"""
🔧 函数/方法: {functions}
📦 类定义: {classes}
📥 导入语句: {imports}"""

    elif language.lower() in ["javascript", "typescript", "js", "ts"]:
        functions = len(re.findall(r'function\s+\w+|const\s+\w+\s*=\s*\(|=>', code))
        classes = len(re.findall(r'class\s+\w+', code))
        imports = len(re.findall(r'^import |^require\(', code, re.MULTILINE))

        result += f"""
🔧 函数/方法: {functions}
📦 类定义: {classes}
📥 导入语句: {imports}"""

    return result


@tool
def detect_code_smells(code: str, language: str = "python") -> str:
    """
    检测代码坏味道（Code Smells），包括长函数、重复代码、命名问题等

    Args:
        code: 要检测的代码
        language: 编程语言 (默认: python)

    Returns:
        检测到的问题列表
    """
    issues = []
    lines = code.split('\n')

    # 检测过长的行
    for i, line in enumerate(lines, 1):
        if len(line) > 100:
            issues.append(f"⚠️  行 {i}: 代码过长 ({len(line)} 字符)，建议拆分")

    # 检测过深的缩进
    for i, line in enumerate(lines, 1):
        if line.strip():
            indent = len(line) - len(line.lstrip())
            if indent > 24:  # 超过6级缩进
                issues.append(f"⚠️  行 {i}: 缩进过深 ({indent//4} 级)，建议重构")

    if language.lower() == "python":
        # 检测长函数
        function_pattern = r'(def\s+\w+\s*\([^)]*\)\s*:)'
        current_function = None
        function_lines = 0

        for line in lines:
            func_match = re.match(function_pattern, line.strip())
            if func_match:
                if current_function and function_lines > 50:
                    issues.append(f"⚠️  函数 '{current_function}' 过长 ({function_lines} 行)，建议拆分")
                current_function = func_match.group(1).split('(')[0].replace('def ', '')
                function_lines = 0
            elif current_function and (line.strip() and not line.strip().startswith('#')):
                function_lines += 1

        # 检测最后函数
        if current_function and function_lines > 50:
            issues.append(f"⚠️  函数 '{current_function}' 过长 ({function_lines} 行)，建议拆分")

        # 检测过多参数
        for i, line in enumerate(lines, 1):
            params_match = re.search(r'def\s+\w+\(([^)]*)\)', line)
            if params_match:
                params = params_match.group(1).split(',')
                if len(params) > 5:
                    issues.append(f"⚠️  行 {i}: 函数参数过多 ({len(params)} 个)，建议使用配置对象")

        # 检测魔法数字
        for i, line in enumerate(lines, 1):
            numbers = re.findall(r'\b\d{2,}\b', line)
            if numbers and not any(x in line for x in ['#', '"', "'"]):
                issues.append(f"⚠️  行 {i}: 可能存在魔法数字 {numbers}，建议使用常量")

    # 检测重复代码（简单版本）
    code_blocks = {}
    for i in range(len(lines) - 2):
        block = '\n'.join(lines[i:i+3])
        if block.strip() and len(block.strip()) > 30:
            if block in code_blocks:
                issues.append(f"⚠️  行 {i+1}: 可能存在重复代码（首次出现在行 {code_blocks[block]+1}）")
            else:
                code_blocks[block] = i

    if not issues:
        return "✅ 未发现明显的代码坏味道"

    return "🔍 代码坏味道检测结果:\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n" + "\n".join(issues[:10])


@tool
def calculate_code_complexity(code: str, language: str = "python") -> str:
    """
    计算代码复杂度（圈复杂度 Cyclomatic Complexity）

    Args:
        code: 要分析的代码
        language: 编程语言 (默认: python)

    Returns:
        复杂度评分和建议
    """
    complexity = 1  # 基础复杂度

    if language.lower() == "python":
        # 计算圈复杂度
        keywords = [
            (r'\bif\b', 1),
            (r'\belif\b', 1),
            (r'\bfor\b', 1),
            (r'\bwhile\b', 1),
            (r'\bexcept\b', 1),
            (r'\bwith\b', 1),
            (r'\band\b', 1),
            (r'\bor\b', 1),
        ]

        for pattern, weight in keywords:
            complexity += len(re.findall(pattern, code)) * weight

        # lambda 和 列表推导
        complexity += len(re.findall(r'\blambda\b', code)) * 0.5
        complexity += len(re.findall(r'\[.*for.*in.*\]', code)) * 0.5

    elif language.lower() in ["javascript", "typescript", "js", "ts"]:
        keywords = [
            (r'\bif\b', 1),
            (r'\belse\s+if\b', 1),
            (r'\bfor\b', 1),
            (r'\bwhile\b', 1),
            (r'\bcatch\b', 1),
            (r'\?[^:]*:', 1),  # 三元运算符
            (r'\&&\b', 1),
            (r'\|\|\b', 1),
        ]

        for pattern, weight in keywords:
            complexity += len(re.findall(pattern, code)) * weight

    lines = len([l for l in code.split('\n') if l.strip()])
    complexity_per_line = complexity / lines if lines > 0 else 0

    # 评估复杂度
    if complexity <= 10:
        level = "🟢 简单"
        suggestion = "代码结构清晰，易于维护"
    elif complexity <= 20:
        level = "🟡 中等"
        suggestion = "代码结构尚可，建议保持关注"
    elif complexity <= 50:
        level = "🟠 复杂"
        suggestion = "代码较复杂，建议重构以降低维护成本"
    else:
        level = "🔴 非常复杂"
        suggestion = "代码过于复杂，强烈建议重构"

    return f"""📊 代码复杂度分析 [{language}]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 圈复杂度: {complexity:.1f}
📏 每行复杂度: {complexity_per_line:.3f}
📊 复杂度等级: {level}

💡 建议: {suggestion}

📈 复杂度参考:
  • 1-10: 简单，易于理解和测试
  • 11-20: 中等，需要一定的测试覆盖
  • 21-50: 复杂，需要重构和完整测试
  • 50+: 非常复杂，必须重构"""


@tool
def check_security_issues(code: str, language: str = "python") -> str:
    """
    检测代码中的安全漏洞和问题

    Args:
        code: 要检测的代码
        language: 编程语言 (默认: python)

    Returns:
        安全问题列表
    """
    issues = []

    if language.lower() == "python":
        # SQL 注入检测
        if re.search(r'execute\(["\'].*\+.*["\']', code):
            issues.append("🔴 高危: 可能存在 SQL 注入风险（字符串拼接）")

        # 硬编码密钥
        if re.search(r'(api_key|secret|password|token)\s*=\s*["\'][^"\']+["\']', code, re.IGNORECASE):
            issues.append("🟠 警告: 疑似硬编码密钥或密码")

        # eval 使用
        if re.search(r'\beval\s*\(', code):
            issues.append("🔴 高危: 使用 eval() 可能导致代码注入")

        # shell=True
        if re.search(r'subprocess\.(call|run|Popen).*shell\s*=\s*True', code):
            issues.append("🔴 高危: subprocess 使用 shell=True 可能导致命令注入")

        # 不安全的随机数
        if re.search(r'random\.random\s*\(', code):
            issues.append("🟡 注意: 使用 random 模块用于安全场景，建议使用 secrets 模块")

        # pickle 反序列化
        if re.search(r'pickle\.loads?\s*\(', code):
            issues.append("🔴 高危: pickle 反序列化可能执行任意代码")

        # 弱哈希算法
        if re.search(r'(md5|sha1)\s*\(', code):
            issues.append("🟡 警告: 使用弱哈希算法 (MD5/SHA1)，建议使用 SHA256+")

    elif language.lower() in ["javascript", "typescript", "js", "ts"]:
        # eval
        if re.search(r'\beval\s*\(', code):
            issues.append("🔴 高危: 使用 eval() 可能导致代码注入")

        # innerHTML
        if re.search(r'\.innerHTML\s*=', code):
            issues.append("🟠 警告: 直接设置 innerHTML 可能导致 XSS")

        # dangerouslySetInnerHTML
        if re.search(r'dangerouslySetInnerHTML', code):
            issues.append("🟠 警告: 使用 dangerouslySetInnerHTML 可能导致 XSS")

        # 硬编码密钥
        if re.search(r'(apiKey|secret|password|token)\s*=\s*["\'][^"\']+["\']', code):
            issues.append("🟠 警告: 疑似硬编码密钥或密码")

    # 通用检测
    # TODO 注释
    if re.search(r'TODO|FIXME|XXX|HACK', code, re.IGNORECASE):
        issues.append("🟡 提示: 代码中包含 TODO/FIXME 注释")

    # 调试语句
    debug_patterns = [r'\bconsole\.log\b', r'\bprint\s*\(', r'\bdebugger\b']
    for pattern in debug_patterns:
        if re.search(pattern, code):
            issues.append("🟡 提示: 代码中可能包含调试语句")
            break

    if not issues:
        return "✅ 未发现明显的安全问题"

    return "🔒 安全问题检测结果:\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n" + "\n".join(issues)


@tool
def search_code_pattern(code: str, pattern: str) -> str:
    """
    在代码中搜索特定模式

    Args:
        code: 要搜索的代码
        pattern: 正则表达式模式

    Returns:
        匹配结果
    """
    try:
        matches = re.finditer(pattern, code, re.MULTILINE)
        results = []

        for match in matches:
            start_pos = match.start()
            lines_before = code[:start_pos].count('\n')
            line_num = lines_before + 1
            results.append(f"  • 行 {line_num}: {match.group(0)[:60]}...")

        if not results:
            return f"未找到匹配模式: {pattern}"

        return f"🔍 搜索结果 [{pattern}]:\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n" + "\n".join(results[:10])
    except re.error as e:
        return f"正则表达式错误: {str(e)}"


# 导出所有工具
langchain_tools = [
    analyze_code_structure,
    detect_code_smells,
    calculate_code_complexity,
    check_security_issues,
    search_code_pattern,
]

# 工具描述映射（用于 Agent）
tool_descriptions = {
    "analyze_code_structure": "分析代码结构，提取函数、类、依赖等基本信息",
    "detect_code_smells": "检测代码坏味道，包括长函数、重复代码、命名问题等",
    "calculate_code_complexity": "计算代码复杂度（圈复杂度）并提供评分",
    "check_security_issues": "检测代码中的安全漏洞和问题",
    "search_code_pattern": "在代码中搜索特定模式",
}
