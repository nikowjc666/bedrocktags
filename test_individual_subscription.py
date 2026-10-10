#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
个性化订阅功能测试脚本

测试场景：
1. 统一分配模式（所有用户相同订阅）
2. 个性化分配模式（每个用户不同订阅）
3. 混合模式（部分用户有订阅，部分无订阅）

使用方法：
    python test_individual_subscription.py
"""

import json
import sqlite3
from datetime import datetime, timedelta


def setup_test_db():
    """创建测试数据库"""
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            plan TEXT NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✓ 测试数据库已就绪")


def test_scenario_1():
    """测试场景 1：统一分配模式"""
    print("\n" + "="*60)
    print("测试场景 1：统一分配模式")
    print("="*60)
    
    # 模拟统一分配：5 个用户，全部专业版年付
    users = [
        {"email": f"unified{i:02d}@test.com", "plan": "pro_yearly", "days": 365}
        for i in range(1, 6)
    ]
    
    print(f"创建 {len(users)} 个用户，订阅方案：pro_yearly")
    
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    for user in users:
        now = datetime.now()
        end_date = now + timedelta(days=user["days"])
        
        cursor.execute('''
            INSERT INTO subscriptions (email, plan, start_date, end_date, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(email) DO UPDATE SET
                plan = excluded.plan,
                start_date = excluded.start_date,
                end_date = excluded.end_date,
                updated_at = excluded.updated_at
        ''', (
            user["email"],
            user["plan"],
            now.isoformat(),
            end_date.isoformat(),
            now.isoformat(),
            now.isoformat()
        ))
    
    conn.commit()
    conn.close()
    
    print("✓ 统一分配完成")
    print("\n结果：")
    for user in users:
        print(f"  - {user['email']}: {user['plan']}")


def test_scenario_2():
    """测试场景 2：个性化分配模式"""
    print("\n" + "="*60)
    print("测试场景 2：个性化分配模式 ⭐")
    print("="*60)
    
    # 模拟个性化分配：5 个用户，5 种不同订阅
    users = [
        {"email": "admin01@test.com", "plan": "enterprise", "days": 365},
        {"email": "dev01@test.com", "plan": "pro_yearly", "days": 365},
        {"email": "dev02@test.com", "plan": "pro_monthly", "days": 30},
        {"email": "tester01@test.com", "plan": "free", "days": 30},
        {"email": "guest01@test.com", "plan": "free", "days": 7},
    ]
    
    print(f"创建 {len(users)} 个用户，每个用户不同订阅：")
    
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    for user in users:
        now = datetime.now()
        end_date = now + timedelta(days=user["days"])
        
        cursor.execute('''
            INSERT INTO subscriptions (email, plan, start_date, end_date, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(email) DO UPDATE SET
                plan = excluded.plan,
                start_date = excluded.start_date,
                end_date = excluded.end_date,
                updated_at = excluded.updated_at
        ''', (
            user["email"],
            user["plan"],
            now.isoformat(),
            end_date.isoformat(),
            now.isoformat(),
            now.isoformat()
        ))
    
    conn.commit()
    conn.close()
    
    print("✓ 个性化分配完成")
    print("\n结果：")
    for user in users:
        print(f"  - {user['email']}: {user['plan']} ({user['days']}天)")


def test_scenario_3():
    """测试场景 3：混合模式（部分有订阅，部分无订阅）"""
    print("\n" + "="*60)
    print("测试场景 3：混合模式")
    print("="*60)
    
    # 模拟混合模式：5 个用户，3 个有订阅，2 个无订阅（跳过）
    users = [
        {"email": "mixed01@test.com", "plan": "team_yearly", "days": 365},
        {"email": "mixed02@test.com", "plan": "team_yearly", "days": 365},
        {"email": "mixed03@test.com", "plan": "pro_yearly", "days": 365},
        # mixed04 和 mixed05 不分配订阅（模拟跳过）
    ]
    
    print(f"创建 5 个用户，其中 {len(users)} 个有订阅，2 个跳过：")
    
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    for user in users:
        now = datetime.now()
        end_date = now + timedelta(days=user["days"])
        
        cursor.execute('''
            INSERT INTO subscriptions (email, plan, start_date, end_date, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(email) DO UPDATE SET
                plan = excluded.plan,
                start_date = excluded.start_date,
                end_date = excluded.end_date,
                updated_at = excluded.updated_at
        ''', (
            user["email"],
            user["plan"],
            now.isoformat(),
            end_date.isoformat(),
            now.isoformat(),
            now.isoformat()
        ))
    
    conn.commit()
    conn.close()
    
    print("✓ 混合分配完成")
    print("\n结果：")
    for user in users:
        print(f"  - {user['email']}: {user['plan']}")
    print(f"  - mixed04@test.com: (未分配)")
    print(f"  - mixed05@test.com: (未分配)")


def show_all_subscriptions():
    """显示所有订阅信息"""
    print("\n" + "="*60)
    print("所有订阅记录")
    print("="*60)
    
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT email, plan, start_date, end_date 
        FROM subscriptions 
        ORDER BY plan, email
    ''')
    
    rows = cursor.fetchall()
    
    if not rows:
        print("暂无订阅记录")
        conn.close()
        return
    
    print(f"\n共 {len(rows)} 条订阅记录：")
    print("-" * 100)
    print(f"{'邮箱':<30} {'订阅方案':<20} {'开始日期':<20} {'结束日期':<20}")
    print("-" * 100)
    
    for row in rows:
        email, plan, start_date, end_date = row
        start = datetime.fromisoformat(start_date).strftime('%Y-%m-%d')
        end = datetime.fromisoformat(end_date).strftime('%Y-%m-%d')
        print(f"{email:<30} {plan:<20} {start:<20} {end:<20}")
    
    print("-" * 100)
    
    # 统计各订阅方案数量
    cursor.execute('''
        SELECT plan, COUNT(*) as count
        FROM subscriptions
        GROUP BY plan
        ORDER BY count DESC
    ''')
    
    stats = cursor.fetchall()
    print("\n订阅方案统计：")
    for plan, count in stats:
        print(f"  • {plan}: {count} 个用户")
    
    conn.close()


def generate_test_config():
    """生成测试用的个性化订阅配置（JSON 格式）"""
    print("\n" + "="*60)
    print("生成测试配置文件")
    print("="*60)
    
    # 示例：10 个用户的个性化订阅配置
    config = {
        "kiro01": {"plan": "enterprise", "days": 365},
        "kiro02": {"plan": "pro_yearly", "days": 365},
        "kiro03": {"plan": "pro_yearly", "days": 365},
        "kiro04": {"plan": "pro_yearly", "days": 365},
        "kiro05": {"plan": "pro_monthly", "days": 30},
        "kiro06": {"plan": "team_yearly", "days": 365},
        "kiro07": {"plan": "team_monthly", "days": 30},
        "kiro08": {"plan": "free", "days": 30},
        "kiro09": {"plan": "free", "days": 7},
        # kiro10 不分配订阅（不在配置中）
    }
    
    filename = "test_individual_config.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    
    print(f"✓ 配置文件已生成：{filename}")
    print("\n配置内容：")
    
    plans = {}
    for username, sub in config.items():
        plan = sub["plan"]
        plans[plan] = plans.get(plan, 0) + 1
        print(f"  - {username}: {plan} ({sub['days']}天)")
    
    print(f"\n未配置订阅的用户：kiro10")
    
    print("\n统计：")
    for plan, count in sorted(plans.items()):
        print(f"  • {plan}: {count} 个")
    print(f"  • 未配置: 1 个")
    
    print(f"\n💡 在前端可以导入此配置进行测试")


def clear_test_data():
    """清空测试数据"""
    response = input("\n是否清空所有测试数据？(yes/no): ")
    if response.lower() != 'yes':
        print("已取消")
        return
    
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    # 只删除测试邮箱的数据
    cursor.execute("DELETE FROM subscriptions WHERE email LIKE '%@test.com'")
    deleted = cursor.rowcount
    
    conn.commit()
    conn.close()
    
    print(f"✓ 已删除 {deleted} 条测试记录")


def main():
    print("="*60)
    print("个性化订阅功能测试")
    print("="*60)
    
    # 设置测试数据库
    setup_test_db()
    
    # 运行测试场景
    test_scenario_1()
    test_scenario_2()
    test_scenario_3()
    
    # 显示所有订阅
    show_all_subscriptions()
    
    # 生成测试配置
    generate_test_config()
    
    # 提示清理
    print("\n" + "="*60)
    print("测试完成！")
    print("="*60)
    print("\n提示：")
    print("1. 运行 'python test_individual_subscription.py --clear' 可清空测试数据")
    print("2. 使用生成的 test_individual_config.json 在前端测试个性化配置")
    print("3. 通过 /api/sso/subscriptions 接口查看订阅记录")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--clear":
        setup_test_db()
        clear_test_data()
    else:
        main()
