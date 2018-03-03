--
-- How to create this file (from project "my_focus_news"):
--   1. remove shownews/migrations/
--   2. python manage.py makemigrations shownews  ==> regenerate migration files
--   3. python manage.py sqlmigrate shownews 0001 > database_sql_commands.sql
--
BEGIN;
--
-- Create model NewsCategory
--
CREATE TABLE "shownews_newscategory" ("id" serial NOT NULL PRIMARY KEY, "name" varchar(100) NOT NULL UNIQUE);
--
-- Create model NewsData
--
CREATE TABLE "shownews_newsdata" ("id" serial NOT NULL PRIMARY KEY, "title" text NOT NULL, "url" varchar(200) NOT NULL UNIQUE, "content" text NOT NULL, "time" timestamp with time zone NOT NULL, "read_time" timestamp with time zone NULL, "creation_time" timestamp with time zone NOT NULL, "last_modified_time" timestamp with time zone NOT NULL);
--
-- Create model NewsKeyword
--
CREATE TABLE "shownews_newskeyword" ("id" serial NOT NULL PRIMARY KEY, "name" varchar(100) NOT NULL, "to_include" boolean NOT NULL);
--
-- Create model ScoreMap
--
CREATE TABLE "shownews_scoremap" ("id" serial NOT NULL PRIMARY KEY, "weight" numeric(5, 2) NOT NULL, "news_id" integer NOT NULL);
--
-- Create model ScrapingRule
--
CREATE TABLE "shownews_scrapingrule" ("id" serial NOT NULL PRIMARY KEY, "name" varchar(100) NOT NULL UNIQUE, "active" boolean NOT NULL);
CREATE TABLE "shownews_scrapingrule_keywords" ("id" serial NOT NULL PRIMARY KEY, "scrapingrule_id" integer NOT NULL, "newskeyword_id" integer NOT NULL);
CREATE TABLE "shownews_scrapingrule_tags" ("id" serial NOT NULL PRIMARY KEY, "scrapingrule_id" integer NOT NULL, "newscategory_id" integer NOT NULL);
--
-- Add field rule to scoremap
--
ALTER TABLE "shownews_scoremap" ADD COLUMN "rule_id" integer NOT NULL;
--
-- Alter unique_together for newskeyword (1 constraint(s))
--
ALTER TABLE "shownews_newskeyword" ADD CONSTRAINT "shownews_newskeyword_name_to_include_7dc6f697_uniq" UNIQUE ("name", "to_include");
--
-- Add field rules to newsdata
--
CREATE TABLE "shownews_newsdata_rules" ("id" serial NOT NULL PRIMARY KEY, "newsdata_id" integer NOT NULL, "scrapingrule_id" integer NOT NULL);
--
-- Alter unique_together for scoremap (1 constraint(s))
--
ALTER TABLE "shownews_scoremap" ADD CONSTRAINT "shownews_scoremap_news_id_rule_id_122ece75_uniq" UNIQUE ("news_id", "rule_id");
CREATE INDEX "shownews_newscategory_name_4418902d_like" ON "shownews_newscategory" ("name" varchar_pattern_ops);
CREATE INDEX "shownews_newsdata_url_9fe10cfd_like" ON "shownews_newsdata" ("url" varchar_pattern_ops);
ALTER TABLE "shownews_scoremap" ADD CONSTRAINT "shownews_scoremap_news_id_50f21067_fk_shownews_newsdata_id" FOREIGN KEY ("news_id") REFERENCES "shownews_newsdata" ("id") DEFERRABLE INITIALLY DEFERRED;
CREATE INDEX "shownews_scoremap_news_id_50f21067" ON "shownews_scoremap" ("news_id");
CREATE INDEX "shownews_scrapingrule_name_dd41a5b7_like" ON "shownews_scrapingrule" ("name" varchar_pattern_ops);
ALTER TABLE "shownews_scrapingrule_keywords" ADD CONSTRAINT "shownews_scrapingrul_scrapingrule_id_90d39a01_fk_shownews_" FOREIGN KEY ("scrapingrule_id") REFERENCES "shownews_scrapingrule" ("id") DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE "shownews_scrapingrule_keywords" ADD CONSTRAINT "shownews_scrapingrul_newskeyword_id_0a6b61b8_fk_shownews_" FOREIGN KEY ("newskeyword_id") REFERENCES "shownews_newskeyword" ("id") DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE "shownews_scrapingrule_keywords" ADD CONSTRAINT "shownews_scrapingrule_ke_scrapingrule_id_newskeyw_f48ef5e7_uniq" UNIQUE ("scrapingrule_id", "newskeyword_id");
CREATE INDEX "shownews_scrapingrule_keywords_scrapingrule_id_90d39a01" ON "shownews_scrapingrule_keywords" ("scrapingrule_id");
CREATE INDEX "shownews_scrapingrule_keywords_newskeyword_id_0a6b61b8" ON "shownews_scrapingrule_keywords" ("newskeyword_id");
ALTER TABLE "shownews_scrapingrule_tags" ADD CONSTRAINT "shownews_scrapingrul_scrapingrule_id_f87cbb71_fk_shownews_" FOREIGN KEY ("scrapingrule_id") REFERENCES "shownews_scrapingrule" ("id") DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE "shownews_scrapingrule_tags" ADD CONSTRAINT "shownews_scrapingrul_newscategory_id_ec549e3b_fk_shownews_" FOREIGN KEY ("newscategory_id") REFERENCES "shownews_newscategory" ("id") DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE "shownews_scrapingrule_tags" ADD CONSTRAINT "shownews_scrapingrule_ta_scrapingrule_id_newscate_b648609c_uniq" UNIQUE ("scrapingrule_id", "newscategory_id");
CREATE INDEX "shownews_scrapingrule_tags_scrapingrule_id_f87cbb71" ON "shownews_scrapingrule_tags" ("scrapingrule_id");
CREATE INDEX "shownews_scrapingrule_tags_newscategory_id_ec549e3b" ON "shownews_scrapingrule_tags" ("newscategory_id");
CREATE INDEX "shownews_scoremap_rule_id_97958d2c" ON "shownews_scoremap" ("rule_id");
ALTER TABLE "shownews_scoremap" ADD CONSTRAINT "shownews_scoremap_rule_id_97958d2c_fk_shownews_scrapingrule_id" FOREIGN KEY ("rule_id") REFERENCES "shownews_scrapingrule" ("id") DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE "shownews_newsdata_rules" ADD CONSTRAINT "shownews_newsdata_ru_newsdata_id_f8de1f8a_fk_shownews_" FOREIGN KEY ("newsdata_id") REFERENCES "shownews_newsdata" ("id") DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE "shownews_newsdata_rules" ADD CONSTRAINT "shownews_newsdata_ru_scrapingrule_id_8111f06a_fk_shownews_" FOREIGN KEY ("scrapingrule_id") REFERENCES "shownews_scrapingrule" ("id") DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE "shownews_newsdata_rules" ADD CONSTRAINT "shownews_newsdata_rules_newsdata_id_scrapingrule_030a37a0_uniq" UNIQUE ("newsdata_id", "scrapingrule_id");
CREATE INDEX "shownews_newsdata_rules_newsdata_id_f8de1f8a" ON "shownews_newsdata_rules" ("newsdata_id");
CREATE INDEX "shownews_newsdata_rules_scrapingrule_id_8111f06a" ON "shownews_newsdata_rules" ("scrapingrule_id");
COMMIT;