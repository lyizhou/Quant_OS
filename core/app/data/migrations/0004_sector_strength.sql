-- 板块强度计算结果缓存表
-- 用于缓存板块、子分类的强度计算结果，避免重复调用API

CREATE TABLE IF NOT EXISTS sector_strength_results (
    id INTEGER PRIMARY KEY,
    sector_id INTEGER NOT NULL,                    -- 板块ID
    sector_name VARCHAR(100) NOT NULL,            -- 板块名称
    category VARCHAR(50),                         -- 板块分类（大板块/子板块/二级板块）
    category_id INTEGER,                          -- 子分类ID（如果是子分类的话）
    category_name VARCHAR(100),                   -- 子分类名称

    -- 计算日期
    calc_date DATE NOT NULL,                      -- 计算日期
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- 整体统计数据
    total_count INTEGER DEFAULT 0,                -- 总股票数
    up_count INTEGER DEFAULT 0,                   -- 上涨股票数
    down_count INTEGER DEFAULT 0,                 -- 下跌股票数
    up_ratio REAL DEFAULT 0,                      -- 上涨比例 (0-1)

    -- 平均指标
    avg_change_pct REAL DEFAULT 0,                -- 平均涨跌幅 (%)
    avg_volume_ratio REAL DEFAULT 0,             -- 平均量比
    avg_turnover_rate REAL DEFAULT 0,            -- 平均换手率 (%)

    -- 资金流向
    total_net_money_flow REAL DEFAULT 0,         -- 总主力净流入（万元）
    avg_money_flow_ratio REAL DEFAULT 0,          -- 平均资金流向占比 (%)

    -- 强度得分
    strength_score REAL DEFAULT 0,                -- 综合强度得分

    -- Top股票（JSON格式存储）
    top_stocks TEXT,                              -- Top10股票JSON

    -- 元数据
    data_source VARCHAR(50) DEFAULT 'tushare',    -- 数据来源
    is_active BOOLEAN DEFAULT true                -- 是否有效
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_sector_strength_sector_id ON sector_strength_results(sector_id);
CREATE INDEX IF NOT EXISTS idx_sector_strength_category_id ON sector_strength_results(category_id);
CREATE INDEX IF NOT EXISTS idx_sector_strength_calc_date ON sector_strength_results(calc_date);
CREATE INDEX IF NOT EXISTS idx_sector_strength_composite ON sector_strength_results(sector_id, calc_date);

-- 创建视图：最新板块强度
CREATE OR REPLACE VIEW v_latest_sector_strength AS
SELECT
    s.*,
    ROW_NUMBER() OVER (PARTITION BY s.sector_id ORDER BY s.calc_date DESC) as rn
FROM sector_strength_results s
WHERE s.is_active = true;

-- 板块强度历史表（用于趋势分析）
CREATE TABLE IF NOT EXISTS sector_strength_history (
    id INTEGER PRIMARY KEY,
    sector_id INTEGER NOT NULL,
    calc_date DATE NOT NULL,
    strength_score REAL NOT NULL,
    avg_change_pct REAL NOT NULL,
    up_ratio REAL NOT NULL,
    total_net_money_flow REAL NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_sector_strength_history_sector_date ON sector_strength_history(sector_id, calc_date);
