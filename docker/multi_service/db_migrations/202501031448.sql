ALTER TABLE `ai_tool_llm_records` ADD `loop_count` INT NOT NULL DEFAULT '0' COMMENT 'The number of times the loop needs to continue running' AFTER `ai_tool_type`, ADD INDEX (`loop_count`);