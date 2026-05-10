#!/usr/bin/env python3
import sys
sys.path.append('.')
from user_data import user_manager

users = user_manager.list_users()
print('用戶列表:')
for u in users:
    print(f'{u.username}: {u.role}')