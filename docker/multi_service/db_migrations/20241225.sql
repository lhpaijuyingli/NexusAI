ALTER TABLE `app_runs`
	CHANGE COLUMN `ai_tool_type` `ai_tool_type` INT NOT NULL DEFAULT '0' COMMENT 'AI tool type 0: Regular APP (not an AI tool) 1: Agent generator 2: Skill generator 3: Round Table meeting summary generator 4: Round Table app target data generator' AFTER `type`;