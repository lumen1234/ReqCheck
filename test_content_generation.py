import os
import sys
import json

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.routes.parse import construct_requirement_tree

def test_content_field():
    print("=" * 60)
    print("测试需求树生成中content字段")
    print("=" * 60)

    # 模拟解析后的内容，包含标题和对应的内容
    test_content = [
        {
            'type': 'heading',
            'level': 1,
            'text': '1 范围',
            'title_number': '1'
        },
        {
            'type': 'content',
            'text': '本文件定义了MEMS陀螺软件系统的需求规格说明。'
        },
        {
            'type': 'content',
            'text': '适用于MEMS陀螺业务软件系统核心功能开发项目。'
        },
        {
            'type': 'heading',
            'level': 2,
            'text': '2 引用文档',
            'title_number': '2'
        },
        {
            'type': 'content',
            'text': 'GB/T 8567-2006 计算机软件文档编制规范'
        },
        {
            'type': 'content',
            'text': 'GB/T 11457-2006 软件工程术语'
        },
        {
            'type': 'heading',
            'level': 2,
            'text': '3 需求',
            'title_number': '3'
        },
        {
            'type': 'heading',
            'level': 3,
            'text': '3.1 要求的状态和方式',
            'title_number': '3.1'
        },
        {
            'type': 'content',
            'text': 'MEMS陀螺作为角速度传感器，需实现载体角速度测量功能。'
        },
        {
            'type': 'content',
            'text': 'TDG06E每次与上级系统通讯均需握手，陀螺状态信息实时上传。'
        }
    ]

    # 构造需求树
    print("\n[测试1] 构造需求树...")
    try:
        tree = construct_requirement_tree(test_content, '测试文档.docx')
        print("  ✓ 需求树构造成功")
    except Exception as e:
        print(f"  ✗ 构造失败: {e}")
        return False

    # 检查content字段
    print("\n[测试2] 检查content字段...")
    def check_content(node, path=""):
        node_path = f"{path}/{node['name']}" if path else node['name']
        
        # 检查content字段是否存在
        if 'content' in node:
            content = node['content']
            content_status = "✓ 有内容" if content and len(content) > 0 else "✗ 空内容"
            print(f"  {node_path}: {content_status}")
            if content and len(content) > 0:
                print(f"    内容: {content}")
        else:
            print(f"  {node_path}: ✗ 缺少content字段")
        
        # 递归检查子节点
        for child in node.get('children', []):
            check_content(child, node_path)

    check_content(tree)

    # 生成全文JSON文件
    print("\n[测试3] 生成全文JSON文件...")
    try:
        output_file = 'full_content_tree.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(tree, f, ensure_ascii=False, indent=2)
        print(f"  ✓ JSON文件生成成功: {output_file}")
        print(f"  文件大小: {os.path.getsize(output_file)} 字节")
    except Exception as e:
        print(f"  ✗ 生成失败: {e}")
        return False

    # 验证JSON文件内容
    print("\n[测试4] 验证JSON文件内容...")
    try:
        with open(output_file, 'r', encoding='utf-8') as f:
            loaded_tree = json.load(f)
        print("  ✓ JSON文件加载成功")
        
        # 检查加载后的树结构
        def verify_tree(node):
            assert 'content' in node, f"节点 {node['name']} 缺少content字段"
            assert isinstance(node['content'], str), f"节点 {node['name']} 的content不是字符串"
            for child in node.get('children', []):
                verify_tree(child)
        
        verify_tree(loaded_tree)
        print("  ✓ JSON文件结构验证通过")
        
    except Exception as e:
        print(f"  ✗ 验证失败: {e}")
        return False

    print("\n" + "=" * 60)
    print("所有测试通过! content字段已正确填充")
    print("=" * 60)
    return True

if __name__ == '__main__':
    try:
        test_content_field()
    except KeyboardInterrupt:
        print("\n测试已取消")
