-- 发票系统生产环境数据库初始化脚本 v1.1.0
-- 适用于Docker Compose首次部署
-- 创建日期: 2024-01-01

-- 设置数据库字符集和事务
SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci;
SET FOREIGN_KEY_CHECKS = 0;
SET sql_mode = 'STRICT_TRANS_TABLES,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION';

-- 设置数据库字符集
ALTER DATABASE invoice_system CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- =============================================================================
-- 1. 创建用户表 (基础表)
-- =============================================================================
CREATE TABLE IF NOT EXISTS `users` (
    `id` INT(11) NOT NULL AUTO_INCREMENT,
    `username` VARCHAR(50) NOT NULL,
    `email` VARCHAR(100) DEFAULT NULL,
    `hashed_password` VARCHAR(255) NOT NULL,
    `is_active` TINYINT(1) DEFAULT 1,
    `is_superuser` TINYINT(1) DEFAULT 0,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    PRIMARY KEY (`id`),
    UNIQUE KEY `ix_users_username` (`username`),
    KEY `ix_users_email` (`email`),
    KEY `ix_users_id` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================================================
-- 2. 创建发票表 (核心业务表)
-- =============================================================================
CREATE TABLE IF NOT EXISTS `invoices` (
    `id` CHAR(36) NOT NULL,
    `user_id` INT(11) NOT NULL,
    
    -- 文件信息
    `original_filename` VARCHAR(255) NOT NULL,
    `file_path` VARCHAR(500) NOT NULL,
    `file_size` INT(11) DEFAULT NULL,
    `file_md5_hash` CHAR(32) DEFAULT NULL COMMENT 'MD5文件哈希值，用于快速去重',
    `file_sha256_hash` CHAR(64) DEFAULT NULL COMMENT 'SHA256文件哈希值，用于精确验证',
    
    -- 来源信息
    `source` VARCHAR(20) DEFAULT 'manual',
    
    -- 发票基本信息
    `invoice_code` VARCHAR(50) DEFAULT NULL,
    `invoice_num` VARCHAR(50) DEFAULT NULL,
    `invoice_date` DATETIME DEFAULT NULL,
    `invoice_type` VARCHAR(50) DEFAULT NULL,
    
    -- 购买方信息
    `purchaser_name` VARCHAR(200) DEFAULT NULL,
    `purchaser_register_num` VARCHAR(50) DEFAULT NULL,
    `purchaser_address` TEXT,
    `purchaser_bank` TEXT,
    
    -- 销售方信息
    `seller_name` VARCHAR(200) DEFAULT NULL,
    `seller_register_num` VARCHAR(50) DEFAULT NULL,
    `seller_address` TEXT,
    `seller_bank` TEXT,
    
    -- 金额信息
    `total_amount` DECIMAL(15,2) DEFAULT NULL,
    `total_tax` DECIMAL(15,2) DEFAULT NULL,
    `amount_in_words` VARCHAR(100) DEFAULT NULL,
    `amount_in_figures` DECIMAL(15,2) DEFAULT NULL,
    
    -- 其他信息
    `service_type` VARCHAR(50) DEFAULT NULL,
    `commodity_details` JSON DEFAULT NULL,
    `ocr_raw_data` JSON DEFAULT NULL,
    
    -- 状态管理
    `status` VARCHAR(20) DEFAULT 'processing',
    `ocr_status` VARCHAR(20) DEFAULT 'pending',
    `ocr_error_message` TEXT,
    
    -- 时间戳
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    `processed_at` DATETIME DEFAULT NULL,
    
    PRIMARY KEY (`id`),
    KEY `ix_invoices_user_id` (`user_id`),
    KEY `ix_invoices_invoice_code` (`invoice_code`),
    KEY `ix_invoices_invoice_num` (`invoice_num`),
    KEY `ix_invoices_invoice_date` (`invoice_date`),
    KEY `ix_invoices_purchaser_name` (`purchaser_name`),
    KEY `ix_invoices_seller_name` (`seller_name`),
    KEY `ix_invoices_total_amount` (`total_amount`),
    KEY `ix_invoices_service_type` (`service_type`),
    KEY `ix_invoices_status` (`status`),
    KEY `ix_invoices_created_at` (`created_at`),
    
    -- 复合索引 (性能优化)
    KEY `idx_invoice_code_num` (`invoice_code`, `invoice_num`),
    KEY `idx_invoice_user_status` (`user_id`, `status`),
    KEY `idx_invoice_user_date` (`user_id`, `invoice_date`),
    KEY `idx_invoices_user_code_num` (`user_id`, `invoice_code`, `invoice_num`),
    KEY `idx_invoices_user_ocr_status` (`user_id`, `ocr_status`),
    KEY `idx_invoices_user_file_size` (`user_id`, `file_size`),
    KEY `idx_invoice_seller_name` (`seller_name`(50)),
    
    -- 哈希去重索引/约束 (高性能文件去重)
    KEY `idx_invoices_md5_hash` (`file_md5_hash`),
    KEY `idx_invoices_sha256_hash` (`file_sha256_hash`),
    KEY `idx_invoices_source` (`source`),
    UNIQUE KEY `uq_invoice_user_filehash_size` (`user_id`, `file_md5_hash`, `file_size`),
    UNIQUE KEY `uq_invoice_user_sha256` (`user_id`, `file_sha256_hash`),
    
    -- 发票去重唯一约束 (关键业务约束)
    UNIQUE KEY `uq_invoice_user_invoicenum` (`user_id`, `invoice_num`),
    
    -- 外键约束
    CONSTRAINT `fk_invoices_user_id` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================================================
-- 3. 创建附件表
-- =============================================================================
CREATE TABLE IF NOT EXISTS `attachments` (
    `id` INT(11) NOT NULL AUTO_INCREMENT,
    `invoice_id` CHAR(36) NOT NULL,
    
    -- 文件信息
    `filename` VARCHAR(255) NOT NULL,
    `file_path` VARCHAR(500) NOT NULL,
    `file_size` INT(11) DEFAULT NULL,
    `mime_type` VARCHAR(100) DEFAULT NULL,
    
    -- 时间戳
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (`id`),
    KEY `ix_attachments_id` (`id`),
    KEY `ix_attachments_created_at` (`created_at`),
    KEY `idx_attachments_invoice` (`invoice_id`),
    
    -- 外键约束
    CONSTRAINT `fk_attachments_invoice_id` FOREIGN KEY (`invoice_id`) REFERENCES `invoices` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================================================
-- 4. 创建邮箱配置表
-- =============================================================================
CREATE TABLE IF NOT EXISTS `email_configs` (
    `id` INT(11) NOT NULL AUTO_INCREMENT,
    `user_id` INT(11) NOT NULL,
    
    -- 邮箱配置信息
    `email_address` VARCHAR(100) NOT NULL,
    `imap_server` VARCHAR(100) NOT NULL,
    `imap_port` INT(11) DEFAULT 993,
    `username` VARCHAR(100) NOT NULL,
    `password_encrypted` TEXT NOT NULL,
    
    -- 配置状态
    `is_active` TINYINT(1) DEFAULT 1,
    `last_scan_time` DATETIME DEFAULT NULL,
    `scan_days` INT(11) DEFAULT 7,
    `last_seen_uid` BIGINT DEFAULT NULL,
    `uid_validity` BIGINT DEFAULT NULL,
    
    -- 时间戳
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    PRIMARY KEY (`id`),
    KEY `ix_email_configs_id` (`id`),
    KEY `ix_email_configs_email_address` (`email_address`),
    KEY `idx_email_config_user_active` (`user_id`, `is_active`),
    
    -- 外键约束
    CONSTRAINT `fk_email_configs_user_id` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================================================
-- 5. 创建邮件表 (邮件处理功能)
-- =============================================================================
CREATE TABLE IF NOT EXISTS `emails` (
    `id` CHAR(36) NOT NULL,
    `user_id` INT(11) NOT NULL,
    
    -- 邮件基本信息
    `message_id` VARCHAR(255) NOT NULL,
    `subject` VARCHAR(500) DEFAULT NULL,
    `sender` VARCHAR(255) DEFAULT NULL,
    `recipient` VARCHAR(255) DEFAULT NULL,
    `date_sent` DATETIME DEFAULT NULL,
    `date_received` DATETIME DEFAULT NULL,
    
    -- 邮件内容
    `body_text` TEXT,
    `body_html` TEXT,
    
    -- 附件信息
    `has_attachments` TINYINT(1) DEFAULT 0,
    `attachment_count` INT(11) DEFAULT 0,
    `attachment_info` JSON DEFAULT NULL,
    
    -- 发票检测状态
    `invoice_scan_status` VARCHAR(20) DEFAULT 'pending',
    `invoice_count` INT(11) DEFAULT 0,
    `scan_result` JSON DEFAULT NULL,
    
    -- 处理状态
    `processing_status` VARCHAR(20) DEFAULT 'unprocessed',
    `error_message` TEXT,
    
    -- 时间戳
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    `scanned_at` DATETIME DEFAULT NULL,
    
    PRIMARY KEY (`id`),
    KEY `idx_emails_user_id` (`user_id`),
    KEY `idx_emails_message_id` (`message_id`),
    KEY `idx_emails_sender` (`sender`),
    KEY `idx_emails_date_sent` (`date_sent`),
    KEY `idx_emails_date_received` (`date_received`),
    KEY `idx_emails_invoice_scan_status` (`invoice_scan_status`),
    KEY `idx_emails_processing_status` (`processing_status`),
    KEY `idx_emails_created_at` (`created_at`),
    KEY `idx_emails_user_scan_status` (`user_id`, `invoice_scan_status`),
    KEY `idx_emails_user_processing_status` (`user_id`, `processing_status`),
    KEY `idx_emails_user_date` (`user_id`, `date_sent`),
    
    -- 唯一约束：同一用户下的邮件message_id唯一
    UNIQUE KEY `unique_user_message` (`user_id`, `message_id`),
    
    -- 外键约束
    CONSTRAINT `fk_emails_user_id` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================================================
-- 6.5. 创建 OCR 缓存表
-- =============================================================================
CREATE TABLE IF NOT EXISTS `ocr_cache` (
    `id` INT(11) NOT NULL AUTO_INCREMENT,
    `sha256` VARCHAR(64) NOT NULL,
    `status` VARCHAR(20) DEFAULT 'success',
    `ocr_json` JSON DEFAULT NULL,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uq_ocr_cache_sha256` (`sha256`),
    KEY `idx_ocr_cache_sha256` (`sha256`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================================================
-- 6. 创建系统日志表 (监控和审计)
-- =============================================================================
CREATE TABLE IF NOT EXISTS `system_logs` (
    `id` INT(11) NOT NULL AUTO_INCREMENT,
    `user_id` INT(11) DEFAULT NULL,
    
    -- 日志信息
    `log_type` VARCHAR(50) NOT NULL,
    `log_level` VARCHAR(20) DEFAULT 'INFO',
    `message` TEXT NOT NULL,
    `details` JSON DEFAULT NULL,
    
    -- 关联信息
    `resource_type` VARCHAR(50) DEFAULT NULL,
    `resource_id` VARCHAR(50) DEFAULT NULL,
    `ip_address` VARCHAR(45) DEFAULT NULL,
    `user_agent` TEXT,
    
    -- 时间戳
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (`id`),
    KEY `ix_system_logs_id` (`id`),
    KEY `ix_system_logs_user_id` (`user_id`),
    KEY `ix_system_logs_log_type` (`log_type`),
    KEY `ix_system_logs_log_level` (`log_level`),
    KEY `ix_system_logs_created_at` (`created_at`),
    KEY `ix_system_logs_resource` (`resource_type`, `resource_id`),
    
    -- 复合索引用于常见查询
    KEY `ix_system_logs_user_type_time` (`user_id`, `log_type`, `created_at`),
    KEY `ix_system_logs_level_time` (`log_level`, `created_at`),
    KEY `idx_logs_user_type_created` (`user_id`, `log_type`, `created_at`),
    KEY `idx_logs_resource` (`resource_type`, `resource_id`),
    
    -- 外键约束
    CONSTRAINT `fk_system_logs_user_id` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================================================
-- 7. 设置InnoDB引擎参数和优化
-- =============================================================================
SET GLOBAL innodb_file_per_table = ON;

-- 恢复外键检查
SET FOREIGN_KEY_CHECKS = 1;

-- =============================================================================
-- 8. 记录初始化完成
-- =============================================================================
INSERT INTO `system_logs` (`log_type`, `log_level`, `message`, `details`, `resource_type`) 
VALUES (
    'system', 
    'INFO', 
    '发票系统数据库初始化完成 v1.1.0',
    JSON_OBJECT(
        'version', '1.1.0',
        'init_date', NOW(),
        'deployment_type', 'docker-compose',
        'tables_created', JSON_ARRAY('users', 'invoices', 'attachments', 'email_configs', 'emails', 'ocr_cache', 'system_logs'),
        'features', JSON_ARRAY('发票管理', '邮件处理', '去重检测', '系统日志', 'OCR处理', 'OCR缓存', 'IMAP UID 增量扫描')
    ),
    'initialization'
);