import re
from typing import Optional, Tuple

# 1.1 标识 / 3.2.X 能力 / 3.7保密性（编号与标题可无空格）
HEADING_NUM_RE = re.compile(
    r'^(\d+(?:\.(?:\d+|[Xx]))*)\s*(.*)$'
)
# 「1范围」「1.1标识」无空格
HEADING_NUM_COMPACT_RE = re.compile(
    r'^(\d+(?:\.(?:\d+|[Xx]))+)([\u4e00-\u9fa5a-zA-Z（(].*)$'
)
HEADING_CHAPTER_COMPACT_RE = re.compile(
    r'^(\d)([\u4e00-\u9fa5a-zA-Z（(][^）\)]*)$'
)
CHAPTER_RE = re.compile(r'^第\s*(\d+)\s*章\s*(.*)$')
MD_HEADING_RE = re.compile(r'^(#{1,6})\s+(.+)$')
LIST_ITEM_RE = re.compile(r'^[a-zA-Z][\.\)、）]\s*|^（\d+）')
# Word 目录行：制表符 + 末尾页码，或「.\t标题\t页码」
TOC_LINE_RE = re.compile(
    r'^(?:[\d\.]+)?\s*\.?\t.+\t\d{1,4}\s*$|^.+\t\d{1,4}\s*$'
)

_INLINE_BODY_MARKERS = (
    '本条', '本章', '本节', '（若有）', '如需', '应指明', '应描述',
    '应列出', '应概述', '应标识', '应定义', '应包括', '应规定',
)


# 编号后的标签如果具备这些特征，大概率是需求正文，而不是真正标题。
_REQUIREMENT_LABEL_STARTERS = (
 '系统', '用户', '管理员', '平台', '页面', '接口', '服务', '模块', '软件',
 '描述', '包括', '包含', '定义', '规定', '指明', '标识', '概述', '列出',
 '提供', '支持', '满足', '实现', '采用', '使用', '根据', '按照', '通过',
 '需要', '要求', '说明', '给出', '指出', '表示', '用于', '属于', '负责',
 '进行', '建立', '确保', '保证', '执行', '显示', '展示', '校验', '保存',
 '导出', '导入', '上传', '下载', '提示', '本条', '本章', '本节', '本文',
 '该', '应', '可', '如', '需', '本', '其',
)
_REQUIREMENT_KEYWORDS_RE = re.compile(
 r'(应当|应该|应|需要|支持|允许|可以|必须|不得|禁止|提供|实现|展示|显示'
 r'|校验|保存|导出|导入|上传|下载|提示|记录|生成|发送|接收|处理|返回'
 r'|配置|管理|创建|新增|编辑|删除|查询|查看|不超过|不小于|不大于|大于'
 r'|小于|达到|具备|保障|兼容|遵循|符合|满足|响应|触发|调用|通知|存储'
 r'|计算|统计|分析|检测|监控|恢复|验证|授权|认证|加载|刷新|切换|跳转)'
)
_REQUIREMENT_SUBJECT_RE = re.compile(r'^(系统|用户|管理员|平台|页面|接口|服务|模块|软件|客户端|服务器|数据库)')
_CONDITION_SENTENCE_RE = re.compile(r'^(当|如果|若|在).*(时|则|需要|应|应该|必须|可以)')


def is_toc_line(line: str) -> bool:
    """判断是否为 Word 自动目录行。"""
    line = line.strip()
    if not line:
        return False
    if TOC_LINE_RE.match(line):
        return True
    if '\t' in line and re.search(r'\t\d{1,4}\s*$', line):
        return True
    if re.match(r'^\.\t', line):
        return True
    return False


def normalize_heading_label(label: str) -> str:
    """清理目录残留格式。"""
    label = label.strip()
    label = re.sub(r'^\.\s*', '', label)
    label = re.sub(r'\t\d{1,4}\s*$', '', label)
    label = label.replace('\t', ' ').strip()
    return label


def level_from_number(number: str) -> int:
    parts = [p for p in number.split('.') if p and p.lower() != 'x']
    return len(parts) if parts else 1


def label_looks_like_requirement_content(label: str) -> bool:
	"""判断编号后的标签文本是否更像需求正文，而不是短标题。"""
	label = (label or '').strip()
	if not label:
		return False
	# 4-6 字短词（如「应急响应」「系统概述」）即使碰巧含关键词也大概率是真标题
	if len(label) <= 6:
		return False
	if len(label) > 20:
		return True
	if label.endswith(('。', '；', ';', '，', ',', '！', '!', '？', '?')):
		# 短文本以标点结尾未必是需求正文，要求至少10字才有足够信号
		if len(label) >= 10:
			return True
	if _CONDITION_SENTENCE_RE.match(label):
		return True
	if _REQUIREMENT_SUBJECT_RE.match(label) and _REQUIREMENT_KEYWORDS_RE.search(label):
		return True
	if _REQUIREMENT_KEYWORDS_RE.search(label) and len(label) >= 8:
		return True
	if any(label.startswith(starter) for starter in _REQUIREMENT_LABEL_STARTERS):
		# 仅以关键词开头是弱信号，需附加条件才判为需求内容
		if _REQUIREMENT_KEYWORDS_RE.search(label) or len(label) >= 10:
			return True
	return False

def parse_heading_line(line: str) -> Optional[Tuple[str, str, int]]:
    """从匹配数字编号模式的行中提取 (number, label, level)。

    IMPORTANT: 此函数仅负责结构提取，不做标题判定。
    调用方必须结合 Word 格式信号或内容启发式来判定该行是否真的是标题。

    返回 (number, label, level) 或 None。
    """
    line = line.strip()
    if not line or LIST_ITEM_RE.match(line) or is_toc_line(line):
        return None
    # 排除列表项：1）xxx、a）xxx
    if re.match(r'^\d+[）\)]', line):
        return None

    chapter = CHAPTER_RE.match(line)
    if chapter:
        number = chapter.group(1)
        label = chapter.group(2).strip() or f'第{number}章'
        return number, label, 1

    match = HEADING_NUM_RE.match(line)
    if match:
        number = match.group(1)
        label = match.group(2).strip()
    else:
        normalized = line.replace(' ', '').replace('\u3000', '')
        compact = HEADING_NUM_COMPACT_RE.match(normalized)
        if not compact:
            compact = HEADING_CHAPTER_COMPACT_RE.match(normalized)
        if not compact:
            return None
        number = compact.group(1)
        label = compact.group(2).strip()

    if not label:
        return None
    label = normalize_heading_label(label)
    from app.parsers.section_registry import is_not_section_title
    if is_not_section_title(label) or is_toc_line(f'{number} {label}'):
        return None
    if label.isdigit() and len(number.split('.')) == 1:
        return None
    return number, label, level_from_number(number)


def parse_md_atx_heading(line: str) -> Optional[Tuple[Optional[str], str, int]]:
    """解析 Markdown ATX 标题，优先从文本中提取数字编号。"""
    line = line.strip()
    match = MD_HEADING_RE.match(line)
    if not match:
        return None

    md_level = len(match.group(1))
    title_text = match.group(2).strip()

    numbered = parse_heading_line(title_text)
    if numbered:
        number, label, num_level = numbered
        return number, label, num_level

    return None, title_text, md_level


def number_to_node_id(number: str) -> str:
    parts = re.split(r'[.\-]+', number.replace('X', 'x').lower())
    safe = [p for p in parts if p]
    return 'node_' + '_'.join(safe) if safe else 'node_unknown'


def split_heading_label(label: str) -> Tuple[str, Optional[str]]:
    """
    将「标题 + 同行正文」拆开，例如：
    「系统概述 本条应概述…」-> ('系统概述', '本条应概述…')
    """
    label = label.strip()
    if not label:
        return label, None

    for marker in _INLINE_BODY_MARKERS:
        idx = label.find(marker)
        if idx > 0:
            title_part = label[:idx].strip()
            body_part = label[idx:].strip()
            if title_part and len(title_part) <= 50:
                return title_part, body_part
        if idx == 0:
            return '', label

    # 不再按标点符号切分长标题——标点（尤其是逗号）在长标题中很常见，
    # 按标点切分会导致标题被截断、后半部分误判为正文。
    return label, None
