-- ============================================================================
-- PHASE 5 P4: Sector Settings Database Migration
-- ============================================================================
-- This script creates the necessary database tables and RLS policies
-- for the multi-sector dashboard functionality.
--
-- IMPORTANT: Execute these commands in Supabase SQL Editor
-- ============================================================================

-- ============================================================================
-- 1. ADD ACTIVE_SECTOR COLUMN TO USERS TABLE
-- ============================================================================
-- This stores the user's currently active sector preference

ALTER TABLE users 
ADD COLUMN IF NOT EXISTS active_sector VARCHAR(50) DEFAULT 'fob';

-- Create index for faster queries
CREATE INDEX IF NOT EXISTS idx_users_active_sector 
ON users(id, active_sector);

-- ============================================================================
-- 2. CREATE SECTOR_SETTINGS TABLE
-- ============================================================================
-- This table stores sector-specific configuration and settings
-- Uses JSONB for flexible schema (can add new settings without migrations)

CREATE TABLE IF NOT EXISTS sector_settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    sector VARCHAR(50) NOT NULL CHECK (sector IN ('fob', 'retail', 'manufacturing')),
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- Ensure one settings record per user per sector
    UNIQUE(user_id, sector)
);

-- ============================================================================
-- 3. CREATE INDEXES FOR PERFORMANCE
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_sector_settings_user_id 
ON sector_settings(user_id);

CREATE INDEX IF NOT EXISTS idx_sector_settings_user_sector 
ON sector_settings(user_id, sector);

-- ============================================================================
-- 4. ENABLE ROW LEVEL SECURITY
-- ============================================================================
-- Prevent users from accessing other users' settings

ALTER TABLE sector_settings ENABLE ROW LEVEL SECURITY;

-- ============================================================================
-- 5. ROW LEVEL SECURITY POLICIES
-- ============================================================================

-- Policy 1: Users can SELECT their own settings
CREATE POLICY "Users can view own sector settings"
ON sector_settings FOR SELECT
USING (auth.uid() = user_id);

-- Policy 2: Users can UPDATE their own settings
CREATE POLICY "Users can update own sector settings"
ON sector_settings FOR UPDATE
USING (auth.uid() = user_id)
WITH CHECK (auth.uid() = user_id);

-- Policy 3: Users can INSERT their own settings
CREATE POLICY "Users can insert own sector settings"
ON sector_settings FOR INSERT
WITH CHECK (auth.uid() = user_id);

-- Policy 4: Users can DELETE their own settings
CREATE POLICY "Users can delete own sector settings"
ON sector_settings FOR DELETE
USING (auth.uid() = user_id);

-- ============================================================================
-- 6. CREATE TRIGGER FOR UPDATED_AT TIMESTAMP
-- ============================================================================
-- Automatically update the updated_at column when records are modified

CREATE OR REPLACE FUNCTION update_sector_settings_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_sector_settings_updated_at
BEFORE UPDATE ON sector_settings
FOR EACH ROW
EXECUTE FUNCTION update_sector_settings_timestamp();

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================
-- Run these to verify the migration was successful:

-- Check users table has active_sector column
-- SELECT column_name, data_type, column_default 
-- FROM information_schema.columns 
-- WHERE table_name = 'users' AND column_name = 'active_sector';

-- Check sector_settings table exists
-- SELECT * FROM information_schema.tables 
-- WHERE table_name = 'sector_settings';

-- Check RLS is enabled
-- SELECT tablename, rowsecurity FROM pg_tables 
-- WHERE tablename = 'sector_settings';

-- ============================================================================
-- ROLLBACK SCRIPT (if needed)
-- ============================================================================
-- To undo this migration, run:

-- DROP TRIGGER IF EXISTS trigger_sector_settings_updated_at ON sector_settings;
-- DROP FUNCTION IF EXISTS update_sector_settings_timestamp();
-- DROP TABLE IF EXISTS sector_settings;
-- ALTER TABLE users DROP COLUMN IF EXISTS active_sector;
-- DROP INDEX IF EXISTS idx_users_active_sector;

-- ============================================================================
-- SAMPLE DATA (for testing, optional)
-- ============================================================================

-- Insert sample sector settings for testing
-- INSERT INTO sector_settings (user_id, sector, settings) 
-- VALUES (
--   'your-user-id-here',
--   'retail',
--   '{"store_size": "small", "category_focus": "food", "location": "Paris"}'::jsonb
-- );

-- ============================================================================
