#!/bin/bash

# Chemistry Bot - Database Cleanup Script
# Completely clears Redis database and removes all lecture files

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}🗑️  Chemistry Bot - Database Cleanup${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"

# Check if Redis is running
echo -e "\n${YELLOW}⏳ Проверка подключения к Redis...${NC}"
if ! redis-cli ping > /dev/null 2>&1; then
    echo -e "${RED}❌ Redis не запущен!${NC}"
    echo "Пожалуйста, запустите Redis командой:"
    echo "  redis-server --daemonize yes"
    exit 1
fi
echo -e "${GREEN}✅ Redis подключен${NC}"

# Show current stats
echo -e "\n${YELLOW}📊 Текущее состояние базы данных:${NC}"
STUDENTS=$(redis-cli KEYS "student:*" | wc -l)
LECTURES=$(redis-cli HLEN "lectures")
TOTAL_KEYS=$(redis-cli DBSIZE | grep -oE '[0-9]+')

echo -e "  📚 Студентов: ${BLUE}${STUDENTS}${NC}"
echo -e "  📖 Лекций: ${BLUE}${LECTURES}${NC}"
echo -e "  🔑 Всего ключей: ${BLUE}${TOTAL_KEYS}${NC}"

# Show lecture files
if [ -d "./lectures" ] && [ "$(ls -A ./lectures)" ]; then
    FILE_COUNT=$(ls -1 ./lectures | wc -l)
    echo -e "  💾 Файлов в ./lectures: ${BLUE}${FILE_COUNT}${NC}"
else
    echo -e "  💾 Файлов в ./lectures: ${BLUE}0${NC}"
fi

# Confirmation
echo -e "\n${RED}⚠️  ВНИМАНИЕ: Эта операция необратима!${NC}"
echo -e "Вы собираетесь удалить:"
echo -e "  • Всех студентов из базы данных"
echo -e "  • Все лекции из базы данных"
echo -e "  • Все файлы лекций из папки ./lectures"
echo ""

read -p "Введите 'DELETE ALL' для подтверждения: " confirmation

if [ "$confirmation" != "DELETE ALL" ]; then
    echo -e "${YELLOW}❌ Отмена операции${NC}"
    exit 0
fi

# Backup (optional)
echo -e "\n${YELLOW}💾 Создание резервной копии...${NC}"
redis-cli BGSAVE > /dev/null 2>&1 || true
if [ -f "dump.rdb" ]; then
    cp dump.rdb dump.rdb.backup.$(date +%Y%m%d_%H%M%S)
    echo -e "${GREEN}✅ Резервная копия создана: dump.rdb.backup.*${NC}"
else
    echo -e "${YELLOW}ℹ️  Резервная копия не создана${NC}"
fi

# Clear Redis
echo -e "\n${YELLOW}🧹 Очистка Redis базы данных...${NC}"
redis-cli FLUSHDB > /dev/null 2>&1
echo -e "${GREEN}✅ Redis база данных очищена${NC}"

# Remove lecture files
echo -e "\n${YELLOW}🗑️  Удаление файлов лекций...${NC}"
if [ -d "./lectures" ]; then
    rm -rf ./lectures/*
    echo -e "${GREEN}✅ Папка ./lectures очищена${NC}"
fi

# Verify cleanup
echo -e "\n${YELLOW}✓ Проверка очистки...${NC}"
STUDENTS_AFTER=$(redis-cli KEYS "student:*" | wc -l)
LECTURES_AFTER=$(redis-cli HLEN "lectures")
TOTAL_KEYS_AFTER=$(redis-cli DBSIZE | grep -oE '[0-9]+')

echo -e "\n${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ ОЧИСТКА ЗАВЕРШЕНА${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"

echo -e "\n${YELLOW}📊 Новое состояние базы данных:${NC}"
echo -e "  📚 Студентов: ${GREEN}${STUDENTS_AFTER}${NC}"
echo -e "  📖 Лекций: ${GREEN}${LECTURES_AFTER}${NC}"
echo -e "  🔑 Всего ключей: ${GREEN}${TOTAL_KEYS_AFTER}${NC}"

if [ -d "./lectures" ]; then
    if [ -z "$(ls -A ./lectures)" ]; then
        echo -e "  💾 Файлов в ./lectures: ${GREEN}0${NC}"
    else
        FILE_COUNT=$(ls -1 ./lectures | wc -l)
        echo -e "  💾 Файлов в ./lectures: ${RED}${FILE_COUNT}${NC} (ошибка!)"
    fi
fi

echo -e "\n${GREEN}🎉 База данных полностью пуста и готова к использованию!${NC}\n"
