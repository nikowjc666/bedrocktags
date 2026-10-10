#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试订阅分配功能

使用方法：
    python test_subscription.py
"""

import sqlite3
from datetime import datetime, timedelta


def test_subscription_db():
    """测试订阅数据库功能"""
    print("=" * 60)
    print("测试订阅数据库功能")
    print("=" * 60)
    
    # 连接数据库
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    # 创建订阅表
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
    print("✓ 订阅表已创建")
    
    # 测试数据
    test_users = [
        {"email": "kiro01@example.com", "plan": "pro_yearly", "days": 365},
        {"email": "kiro02@example.com", "plan": "team_monthly", "days": 30},
        {"email": "kiro03@example.com", "plan": "enterprise", "days": 365},
    ]
    
    print("\n插入测试数据...")
    for user in test_users:
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
        print(f"  ✓ {user['email']} - {user['plan']} (有效期 {user['days']} 天)")
    
    conn.commit()
    
    # 查询并显示所有订阅
    print("\n查询所有订阅...")
    cursor.execute('''
        SELECT email, plan, start_date, end_date 
        FROM subscriptions 
        ORDER BY created_at DESC
    ''')
    
    rows = cursor.fetchall()
    print(f"\n共找到 {len(rows)} 条订阅记录：")
    print("-" * 100)
    print(f"{'邮箱':<30} {'订阅方案':<20} {'开始日期':<25} {'结束日期':<25}")
    print("-" * 100)
    
    for row in rows:
        email, plan, start_date, end_date = row
        start = datetime.fromisoformat(start_date).strftime('%Y-%m-%d %H:%M:%S')
        end = datetime.fromisoformat(end_date).strftime('%Y-%m-%d %H:%M:%S')
        print(f"{email:<30} {plan:<20} {start:<25} {end:<25}")
    
    print("-" * 100)
    
    # 统计各订阅方案数量
    print("\n订阅方案统计：")
    cursor.execute('''
        SELECT plan, COUNT(*) as count
        FROM subscriptions
        GROUP BY plan
        ORDER BY count DESC
    ''')
    
    stats = cursor.fetchall()
    for plan, count in stats:
        print(f"  • {plan}: {count} 个用户")
    
    conn.close()
    print("\n✓ 测试完成！")
    print("=" * 60)


def clear_subscriptions():
    """清空订阅数据（用于重新测试）"""
    response = input("\n是否要清空所有订阅数据？(yes/no): ")
    if response.lower() != 'yes':
        print("已取消")
        return
    
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM subscriptions')
    deleted = cursor.rowcount
    conn.commit()
    conn.close()
    print(f"✓ 已删除 {deleted} 条订阅记录")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--clear":
        clear_subscriptions()
    else:
        test_subscription_db()
        print("\n提示：运行 'python test_subscription.py --clear' 可清空测试数据")
