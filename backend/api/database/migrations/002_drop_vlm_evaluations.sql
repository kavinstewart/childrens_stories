-- Migration 002: Drop vlm_evaluations table
-- Run with: psql -f 002_drop_vlm_evaluations.sql -d childrens_stories
--
-- This migration removes the vlm_evaluations table which was scaffolded
-- but never properly implemented. The VLM evaluation feature will be
-- rebuilt from scratch when requirements are finalized.

DROP TABLE IF EXISTS vlm_evaluations;
