
if [ "$1" == "local" ]; then
    echo "Switching to LOCAL (SQLite) environment..."
    cp .env.local .env
    echo "✓ Using SQLite database"
elif [ "$1" == "supabase" ]; then
    echo "Switching to SUPABASE (PostgreSQL) environment..."
    cp .env.supabase .env
    echo "✓ Using Supabase PostgreSQL"
else
    echo "Usage: ./switch_env.sh [local|supabase]"
    exit 1
fi
