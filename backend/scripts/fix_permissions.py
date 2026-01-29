"""
Скрипт для автоматического исправления прав доступа к базе данных.

Запусти: python -m scripts.fix_permissions
"""

import asyncio
import sys
from pathlib import Path

# Добавляем путь к app
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.database import engine
from app.config import settings
from sqlalchemy import text


async def fix_permissions():
    """Выдает права доступа текущему пользователю."""
    print("=" * 60)
    print("🔧 Исправление прав доступа к базе данных")
    print("=" * 60)
    
    # Извлекаем имя пользователя из DATABASE_URL
    db_url = settings.database_url
    if "://" in db_url:
        # Формат: postgresql://user:password@host:port/dbname
        parts = db_url.split("://")[1]
        if "@" in parts:
            user_part = parts.split("@")[0]
            username = user_part.split(":")[0]
        else:
            username = "postgres"
    else:
        username = "postgres"
    
    print(f"\n📝 Пользователь из DATABASE_URL: {username}")
    print(f"📝 База данных: {db_url.split('/')[-1] if '/' in db_url else 'edinorok'}")
    
    try:
        async with engine.begin() as conn:
            # Сначала проверяем, кто владелец таблиц
            print("\n🔍 Проверяю владельцев таблиц...")
            result = await conn.execute(
                text("""
                SELECT 
                    tablename,
                    tableowner
                FROM pg_tables
                WHERE schemaname = 'public'
                ORDER BY tablename;
                """)
            )
            
            tables = result.fetchall()
            if tables:
                print("\n📊 Владельцы таблиц:")
                owners = set()
                for table in tables:
                    print(f"   • {table[0]}: {table[1]}")
                    owners.add(table[1])
                
                # Если таблицы принадлежат другому пользователю, нужно изменить владельца
                if len(owners) > 0 and username not in owners:
                    print(f"\n⚠️  Таблицы принадлежат другому пользователю: {', '.join(owners)}")
                    print(f"💡 Нужно либо:")
                    print(f"   1. Изменить владельца таблиц на {username}")
                    print(f"   2. Или подключиться как суперпользователь и выдать права")
                    print(f"\n📋 Выполни вручную через psql:")
                    print(f"   psql -U postgres -d edinorok")
                    print(f"\n   -- Вариант 1: Изменить владельца (если есть права)")
                    for owner in owners:
                        print(f"   ALTER TABLE {tables[0][0]} OWNER TO {username};")
                    print(f"\n   -- Вариант 2: Выдать права от имени владельца")
                    for owner in owners:
                        print(f"   -- Подключись как: psql -U {owner} -d edinorok")
                        print(f"   GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO {username};")
                        print(f"   GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO {username};")
                    return
            
            # Выдаем права на все таблицы
            print("\n🔐 Выдаю права на таблицы...")
            try:
                # Права на существующие таблицы
                await conn.execute(text(f"GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO {username}"))
                await conn.execute(text(f"GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO {username}"))
                
                # Права на будущие таблицы
                await conn.execute(text(f"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO {username}"))
                await conn.execute(text(f"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO {username}"))
                
                print("✅ Права на таблицы выданы")
            except Exception as e:
                print(f"⚠️  Не удалось выдать права автоматически: {e}")
                print(f"\n💡 Попробуй выполнить команды вручную:")
                print(f"   psql -U postgres -d edinorok")
                print(f"\n   -- Если таблицы принадлежат другому пользователю, подключись как владелец:")
                if tables:
                    owner = tables[0][1]
                    print(f"   psql -U {owner} -d edinorok")
                print(f"\n   GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO {username};")
                print(f"   GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO {username};")
                print(f"   ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO {username};")
                print(f"   ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO {username};")
                raise
            
            # Проверяем права
            print("\n🔍 Проверяю права...")
            result = await conn.execute(
                text("""
                SELECT 
                    tablename,
                    has_table_privilege(current_user, tablename, 'SELECT') as can_select,
                    has_table_privilege(current_user, tablename, 'INSERT') as can_insert,
                    has_table_privilege(current_user, tablename, 'UPDATE') as can_update,
                    has_table_privilege(current_user, tablename, 'DELETE') as can_delete
                FROM pg_tables
                WHERE schemaname = 'public'
                ORDER BY tablename;
                """)
            )
            
            tables = result.fetchall()
            if tables:
                print("\n📊 Текущие права на таблицы:")
                for table in tables:
                    perms = []
                    if table[1]: perms.append("SELECT")
                    if table[2]: perms.append("INSERT")
                    if table[3]: perms.append("UPDATE")
                    if table[4]: perms.append("DELETE")
                    status = "✅" if len(perms) == 4 else "⚠️"
                    print(f"   {status} {table[0]}: {', '.join(perms) if perms else 'НЕТ ПРАВ'}")
            else:
                print("   ℹ️  Таблицы еще не созданы")
            
            print("\n" + "=" * 60)
            print("✅ Готово! Попробуй запустить скрипт обработки снова:")
            print("   python -m scripts.process_artists")
            print("=" * 60)
            
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        print("\n💡 Попробуй выполнить вручную через psql:")
        print(f"   psql -U postgres -d edinorok")
        print(f"   GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO {username};")
        print(f"   GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO {username};")
        print(f"   ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO {username};")
        print(f"   ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO {username};")


if __name__ == "__main__":
    asyncio.run(fix_permissions())
