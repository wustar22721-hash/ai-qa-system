-- ============================================================
-- Agent 数据库初始化脚本
-- 用法: mysql -u root -p < scripts/init_db.sql
-- ============================================================

CREATE DATABASE IF NOT EXISTS agent_db
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

USE agent_db;

-- ============================================================
-- 1. 员工表
-- ============================================================
DROP TABLE IF EXISTS tickets;
DROP TABLE IF EXISTS employees;

CREATE TABLE employees (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    name        VARCHAR(50)  NOT NULL COMMENT '员工姓名',
    department  VARCHAR(50)  NOT NULL COMMENT '部门',
    position    VARCHAR(50)  DEFAULT NULL COMMENT '职位',
    email       VARCHAR(100) DEFAULT NULL COMMENT '邮箱',
    phone       VARCHAR(20)  DEFAULT NULL COMMENT '电话',
    leader_id   INT          DEFAULT NULL COMMENT '直属上级ID',
    created_at  TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_name       (name),
    INDEX idx_department (department),
    INDEX idx_leader     (leader_id),
    CONSTRAINT fk_leader FOREIGN KEY (leader_id) REFERENCES employees(id)
) ENGINE=InnoDB COMMENT='员工信息表';

-- ============================================================
-- 2. 工单表
-- ============================================================
CREATE TABLE tickets (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    ticket_id     VARCHAR(20)  NOT NULL UNIQUE COMMENT '工单编号',
    title         VARCHAR(200) NOT NULL COMMENT '工单标题',
    description   TEXT         DEFAULT NULL COMMENT '详细描述',
    assignee_id   INT          DEFAULT NULL COMMENT '指派员工ID',
    priority      ENUM('low','medium','high','urgent') NOT NULL DEFAULT 'medium' COMMENT '紧急程度',
    status        ENUM('open','in_progress','closed')  NOT NULL DEFAULT 'open' COMMENT '状态',
    created_at    TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_ticket_id   (ticket_id),
    INDEX idx_assignee    (assignee_id),
    INDEX idx_status      (status),
    CONSTRAINT fk_assignee FOREIGN KEY (assignee_id) REFERENCES employees(id)
) ENGINE=InnoDB COMMENT='工单表';

-- ============================================================
-- 3. 插入员工数据（含组织层级）
-- ============================================================

-- 管理层 / 部门负责人 (leader_id = NULL)
INSERT INTO employees (id, name, department, position, email, phone, leader_id) VALUES
(1,  '赵建国', '技术部', '技术总监',   'zhaojianguo@company.com',  '13800001001', NULL),
(4,  '李雪',   '产品部', '产品总监',   'lixue@company.com',       '13800001004', NULL),
(6,  '孙伟',   '运营部', '运营总监',   'sunwei@company.com',      '13800001006', NULL),
(8,  '周涛',   '销售部', '销售总监',   'zhoutao@company.com',     '13800001008', NULL),
(10, '郑华',   '人事部', '人事经理',   'zhenghua@company.com',    '13800001010', NULL),
(12, '刘芳',   '财务部', '财务主管',   'liufang@company.com',     '13800001012', NULL);

-- 技术部 (leader_id → 赵建国)
INSERT INTO employees (id, name, department, position, email, phone, leader_id) VALUES
(2,  '张三',   '技术部', '高级后端工程师', 'zhangsan@company.com',   '13800001002', 1),
(3,  '陈小明', '技术部', '前端工程师',     'chenxiaoming@company.com', '13800001003', 1);

-- 产品部 (leader_id → 李雪)
INSERT INTO employees (id, name, department, position, email, phone, leader_id) VALUES
(5,  '王芳',   '产品部', '产品经理',     'wangfang@company.com',    '13800001005', 4);

-- 运营部 (leader_id → 孙伟)
INSERT INTO employees (id, name, department, position, email, phone, leader_id) VALUES
(7,  '吴丽',   '运营部', '运营专员',     'wuli@company.com',        '13800001007', 6);

-- 销售部 (leader_id → 周涛)
INSERT INTO employees (id, name, department, position, email, phone, leader_id) VALUES
(9,  '钱鹏',   '销售部', '销售经理',     'qianpeng@company.com',    '13800001009', 8);

-- 人事部 (leader_id → 郑华)
INSERT INTO employees (id, name, department, position, email, phone, leader_id) VALUES
(11, '冯磊',   '人事部', '招聘专员',     'fenglei@company.com',     '13800001011', 10);

-- 财务部 (leader_id → 刘芳)
INSERT INTO employees (id, name, department, position, email, phone, leader_id) VALUES
(13, '黄梅',   '财务部', '会计',         'huangmei@company.com',    '13800001013', 12);

-- ============================================================
-- 4. 插入工单数据
-- ============================================================
INSERT INTO tickets (ticket_id, title, description, assignee_id, priority, status) VALUES
('TICKET-001', '三楼打印机故障',         '三楼东区打印机无法打印，提示卡纸，多次重启无效',            2,  'high',   'in_progress'),
('TICKET-002', '会议室网络中断',         'A201会议室WiFi信号极弱，影响视频会议',                      3,  'urgent', 'open'),
('TICKET-003', '新员工入职权限开通',     '新员工张三需要开通企业邮箱、OA系统、门禁权限',               11, 'medium', 'closed'),
('TICKET-004', '报销系统无法提交',       '部分员工反馈报销系统提交时报500错误，已持续两天',            13, 'high',   'open'),
('TICKET-005', '客户积分规则配置',       '配合运营活动需要调整客户积分规则，涉及后台配置和前端展示',    5,  'low',    'open');

-- ============================================================
-- 5. 查询验证
-- ============================================================
-- 查看所有员工
SELECT id, name, department, position FROM employees ORDER BY id;

-- 查看组织架构（含上级姓名）
SELECT
    e.id,
    e.name,
    e.department,
    e.position,
    l.name AS leader_name
FROM employees e
LEFT JOIN employees l ON e.leader_id = l.id
ORDER BY e.department, e.id;

-- 查看工单及指派对象
SELECT
    t.ticket_id,
    t.title,
    t.priority,
    t.status,
    e.name AS assignee_name,
    e.department
FROM tickets t
LEFT JOIN employees e ON t.assignee_id = e.id
ORDER BY t.created_at;
