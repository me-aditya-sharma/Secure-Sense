# backend/reset.ps1 - drop, recreate, migrate, reseed the SecureSense DB.
# Run from the backend/ folder: .\reset.ps1

$ErrorActionPreference = "Stop"

$DB_CONTAINER = "securesense-db"
$DB_USER = "securesense"
$DB_NAME = "securesense"

Write-Host "Dropping and recreating database '$DB_NAME'..."
docker exec -i $DB_CONTAINER psql -U $DB_USER -d postgres -c "DROP DATABASE IF EXISTS $DB_NAME;"
docker exec -i $DB_CONTAINER psql -U $DB_USER -d postgres -c "CREATE DATABASE $DB_NAME;"

Write-Host "Applying schema..."
Get-Content schema.sql -Raw | docker exec -i $DB_CONTAINER psql -U $DB_USER -d $DB_NAME

Write-Host "Seeding demo data..."
python seed.py

Write-Host "Done."
