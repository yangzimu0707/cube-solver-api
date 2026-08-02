"""
测试 passagemath-rubiks 库是否支持 4x4/5x5
"""

try:
    from sage.all import RubikCube
    
    # 测试 2x2
    print("测试 2x2...")
    cube2 = RubikCube(2)
    cube2.scramble()
    print(f"2x2 打乱后状态: {cube2}")
    solution2 = cube2.solve()
    print(f"2x2 解法: {solution2}")
    print(f"2x2 解法步数: {len(solution2)}")
    
    # 测试 3x3
    print("\n测试 3x3...")
    cube3 = RubikCube(3)
    cube3.scramble()
    print(f"3x3 打乱后状态: {cube3}")
    solution3 = cube3.solve()
    print(f"3x3 解法: {solution3}")
    print(f"3x3 解法步数: {len(solution3)}")
    
    # 测试 4x4
    print("\n测试 4x4...")
    cube4 = RubikCube(4)
    cube4.scramble()
    print(f"4x4 打乱后状态: {cube4}")
    solution4 = cube4.solve()
    print(f"4x4 解法: {solution4}")
    print(f"4x4 解法步数: {len(solution4)}")
    
    # 测试 5x5
    print("\n测试 5x5...")
    cube5 = RubikCube(5)
    cube5.scramble()
    print(f"5x5 打乱后状态: {cube5}")
    solution5 = cube5.solve()
    print(f"5x5 解法: {solution5}")
    print(f"5x5 解法步数: {len(solution5)}")
    
    print("\n✅ passagemath-rubiks 支持 2x2, 3x3, 4x4, 5x5")
    
except ImportError as e:
    print(f"❌ 导入失败: {e}")
    print("passagemath-rubiks 可能未安装或不可用")
except Exception as e:
    print(f"❌ 测试失败: {e}")
